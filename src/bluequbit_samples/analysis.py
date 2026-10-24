"""Per-problem metrics with exact-reference coverage and no fabricated scores."""

import json
import math
from pathlib import Path
import tempfile
import os

from .provenance import atomic_json, file_sha256


def records_frame(records):
    import pandas as pd
    rows = []
    for record in records:
        row = record.to_dict() if hasattr(record, "to_dict") else dict(record)
        method, parameters = row["method"], row["parameters"]
        if method == "mps":
            setting = "chi=unlimited" if parameters.get("chi") is None else f"chi={parameters['chi']}"
        elif method == "pps":
            setting = f"eta={parameters.get('eta', 0):g}"
        else:
            setting = "double"
        row.update(setting=setting, reference_status=row["diagnostics"].get("reference_status"),
                   max_bond_actual=row["diagnostics"].get("max_bond_actual"),
                   state_norm_squared=row["diagnostics"].get("state_norm_squared"),
                   peak_num_paulis=row["diagnostics"].get("peak_num_paulis"),
                   remaining_slices=row["diagnostics"].get("remaining_slices"))
        rows.append(row)
    columns = ["circuit_id", "sample", "qubit", "num_qubits", "qasm_sha256", "dataset_kind",
               "method", "parameters", "setting", "status", "estimate", "backend", "wall_seconds",
               "compute_seconds", "peak_rss", "reference_status", "max_bond_actual", "state_norm_squared",
               "peak_num_paulis", "remaining_slices", "diagnostics", "package_versions", "cache_hit"]
    return pd.DataFrame(rows) if rows else pd.DataFrame(columns=columns)


def comparison_table(records):
    frame = records_frame(records)
    if frame.empty:
        frame["reference"] = []
        frame["absolute_error"] = []
        return frame
    keys = ["circuit_id", "qasm_sha256", "dataset_kind"]
    exact = frame[(frame.method == "exact") & (frame.status == "SUCCEEDED") & frame.estimate.notna()]
    if exact.duplicated(keys).any():
        raise ValueError("Duplicate exact references: collect one result per ID and input hash")
    refs = exact[keys + ["estimate"]].rename(columns={"estimate": "reference"})
    frame = frame.merge(refs, how="left", on=keys, validate="many_to_one")
    frame["absolute_error"] = (frame.estimate - frame.reference).abs()
    return frame


def correlation_score(predictions, references, *, points=100, near_constant_atol=1e-14):
    """Local replica. The tolerance is numerical policy, not an official threshold."""
    import numpy as np
    x, y = np.asarray(predictions, dtype=float), np.asarray(references, dtype=float)
    if x.shape != y.shape or x.ndim != 1 or x.size == 0:
        raise ValueError("Nonempty aligned one-dimensional vectors are required")
    if not np.isfinite(x).all() or not np.isfinite(y).all():
        return None, None, "NONFINITE"
    x0, y0 = x - x.mean(), y - y.mean()
    nx, ny = np.linalg.norm(x0), np.linalg.norm(y0)
    if nx <= near_constant_atol:
        return None, 0.0, "CONSTANT_PREDICTION"
    if ny <= near_constant_atol:
        return None, None, "CONSTANT_REFERENCE"
    rho = float(np.clip(np.dot(x0, y0) / (nx * ny), -1, 1))
    return rho, float(points * max(0, rho) ** 2), "OK"


def summary_table(samples, records):
    import numpy as np
    import pandas as pd
    comparison = comparison_table(records)
    rows = []
    if comparison.empty:
        return pd.DataFrame(columns=["sample", "method", "setting", "expected_ids", "completed_ids",
                                     "paired_ids", "mae", "rmse", "max_abs_error", "pearson", "score",
                                     "score_status", "wall_seconds", "peak_rss"])
    for (label, method, setting), group in comparison.groupby(["sample", "method", "setting"], sort=False):
        input_group = [s for s in samples if s.sample == label]
        expected = {s.circuit_id for s in input_group}
        expected_count = len(expected)
        input_complete = True
        if input_group and all(s.dataset_kind == "official" for s in input_group):
            dimensions = {s.num_qubits for s in input_group}
            expected_count = input_group[0].num_qubits
            input_complete = len(dimensions) == 1 and {s.qubit for s in input_group} == set(range(expected_count))
        if group.circuit_id.duplicated().any():
            raise ValueError(f"Duplicate records within {label}/{method}/{setting}")
        successful = group[(group.status == "SUCCEEDED") & group.estimate.notna()]
        paired = successful[successful.reference.notna()]
        error = paired.estimate.to_numpy(dtype=float) - paired.reference.to_numpy(dtype=float)
        complete = input_complete and set(paired.circuit_id) == expected and bool(expected)
        rho, score, state = (None, None, "PARTIAL_REFERENCE_OR_PREDICTION" if input_complete else "INCOMPLETE_INPUT_MANIFEST")
        if complete:
            rho, score, state = correlation_score(paired.estimate, paired.reference)
        rows.append(dict(sample=label, dataset_kind=group.dataset_kind.iloc[0], method=method, setting=setting,
                         expected_ids=expected_count, completed_ids=len(successful), paired_ids=len(paired),
                         mae=float(np.mean(abs(error))) if error.size else None,
                         rmse=float(np.sqrt(np.mean(error**2))) if error.size else None,
                         max_abs_error=float(np.max(abs(error))) if error.size else None,
                         pearson=rho, score=score, score_status=state,
                         wall_seconds=float(group.wall_seconds.sum()),
                         peak_rss=group.peak_rss.max() if group.peak_rss.notna().any() else None))
    return pd.DataFrame(rows)


def _atomic_csv(path, frame):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(dir=path.parent, suffix=".csv.tmp")
    os.close(descriptor)
    try:
        frame.to_csv(temporary, index=False, float_format="%.17g", encoding="utf-8", lineterminator="\n")
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def _retire_submission(root, label):
    """Preserve prior bytes while removing an ineligible current submission."""
    previous = root / "submissions" / f"{label}.csv"
    if previous.exists():
        archive = root / "superseded_submissions"
        archive.mkdir(parents=True, exist_ok=True)
        os.replace(previous, archive / f"{label}-{file_sha256(previous)}.csv")


def export_results(samples, records, output_dir):
    import pandas as pd
    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)
    frame = comparison_table(records)
    summary = summary_table(samples, records)
    # Raw JSON retains nested diagnostics; CSVs are reader-facing flat views.
    atomic_json(root / "records.json", [r.to_dict() for r in records])
    manifest = pd.DataFrame([s.manifest_row() for s in samples])
    _atomic_csv(root / "input_manifest.csv", manifest)
    flat = frame.drop(columns=["parameters", "diagnostics", "package_versions"], errors="ignore")
    _atomic_csv(root / "estimates.csv", flat)
    _atomic_csv(root / "summary.csv", summary)
    exact = flat[(flat.method == "exact") & (flat.status == "SUCCEEDED")]
    _atomic_csv(root / "exact_references.csv", exact)
    exports = {}
    for label in ("S1", "S2", "S3"):
        group = [s for s in samples if s.sample == label and s.dataset_kind == "official"]
        expected = {s.circuit_id for s in group}
        if not group:
            _retire_submission(root, label)
            exports[label] = {"status": "NO_OFFICIAL_INPUTS"}
            continue
        dimensions = {s.num_qubits for s in group}
        if len(dimensions) != 1 or {s.qubit for s in group} != set(range(group[0].num_qubits)):
            _retire_submission(root, label)
            exports[label] = {"status": "INCOMPLETE_INPUT_MANIFEST"}
            continue
        values = exact[(exact["sample"] == label) & (exact.dataset_kind == "official")]
        # Match hashes too; a result from another input revision must not be exported.
        expected_identity = {(s.circuit_id, s.qasm_sha256) for s in group}
        actual_identity = set(zip(values.circuit_id, values.qasm_sha256))
        if len(values) != len(expected) or actual_identity != expected_identity:
            _retire_submission(root, label)
            exports[label] = {"status": "INCOMPLETE_EXACT_REFERENCES"}
            continue
        output = values[["circuit_id", "estimate"]].rename(columns={"estimate": "value"}).sort_values("circuit_id")
        if output.circuit_id.duplicated().any() or not all(math.isfinite(v) for v in output.value):
            raise ValueError(f"Invalid submission values for {label}")
        path = root / "submissions" / f"{label}.csv"
        _atomic_csv(path, output)
        reread = pd.read_csv(path, float_precision="round_trip")
        if list(reread.columns) != ["circuit_id", "value"] or set(reread.circuit_id) != expected:
            raise ValueError("Submission read-back validation failed")
        if list(reread.value) != list(output.value) or not all(math.isfinite(v) for v in reread.value):
            raise ValueError("Submission numeric read-back validation failed")
        exports[label] = {"status": "EXPORTED_NOT_SUBMITTED", "path": str(path), "rows": len(output),
                          "sha256": file_sha256(path)}
    atomic_json(root / "submission_exports.json", exports)
    hashes = {str(path.relative_to(root)): file_sha256(path) for path in sorted(root.rglob("*"))
              if path.is_file() and path.name != "SHA256SUMS.json"}
    atomic_json(root / "SHA256SUMS.json", hashes)
    return {"directory": str(root), "submissions": exports, "hashes": hashes}


def verify_exports(output_dir):
    root = Path(output_dir)
    expected = json.loads((root / "SHA256SUMS.json").read_text(encoding="utf-8"))
    for name, digest in expected.items():
        candidate = (root / name).resolve()
        if not candidate.is_relative_to(root.resolve()):
            raise ValueError("Invalid checksum path")
        if file_sha256(candidate) != digest:
            raise ValueError(f"Read-back hash mismatch: {name}")
    return {"status": "VERIFIED", "files": len(expected)}

