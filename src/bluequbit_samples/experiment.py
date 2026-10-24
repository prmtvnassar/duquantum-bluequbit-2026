"""One sequential experiment path shared by notebooks and batch jobs."""

from pathlib import Path

from .analysis import export_results
from .models import RunConfig
from .provenance import atomic_json, environment_receipt
from .runtime import execute

DEFAULT_CHIS = (16, 32, 64, 128, 256)
DEFAULT_ETAS = (1e-2, 1e-3, 1e-4, 1e-5)


def run_suite(samples, output_dir, config=None, methods=("exact", "mps", "pps"),
              chis=DEFAULT_CHIS, etas=DEFAULT_ETAS, progress=True):
    config = config or RunConfig()
    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)
    if len({s.circuit_id for s in samples}) != len(samples):
        raise ValueError("A suite may contain only one input for each circuit ID")
    if set(methods) - {"exact", "mps", "pps"}:
        raise ValueError("Unknown method in suite")
    atomic_json(root / "environment.json", environment_receipt(config))
    atomic_json(root / "input_manifest.json", [s.manifest_row() for s in samples])
    records = []
    actions = []
    # Exact references are completed and saved before approximate sweeps.
    for method in ("exact", "mps", "pps"):
        if method not in methods:
            continue
        parameters = [{}] if method == "exact" else [{"chi": c} for c in chis] if method == "mps" else [{"eta": e} for e in etas]
        for parameter in parameters:
            for sample in samples:
                actions.append((sample, method, parameter))
    atomic_json(root / "suite_status.json", {"status": "RUNNING", "planned_tasks": len(actions), "completed_tasks": 0})
    try:
        for index, (sample, method, parameter) in enumerate(actions, 1):
            record = execute(sample, method, parameter, config, root)
            records.append(record)
            atomic_json(root / "current_records.json", [r.to_dict() for r in records])
            atomic_json(root / "suite_status.json", {"status": "RUNNING", "planned_tasks": len(actions),
                        "completed_tasks": index, "successful_tasks": sum(r.succeeded for r in records)})
            if progress:
                print(f"[{index}/{len(actions)}] {sample.circuit_id} {method} {parameter}: {record.status}"
                      + (" (cache)" if record.cache_hit else ""), flush=True)
    except BaseException:
        atomic_json(root / "suite_status.json", {"status": "INTERRUPTED", "planned_tasks": len(actions),
                    "completed_tasks": len(records), "successful_tasks": sum(r.succeeded for r in records)})
        raise
    exported = export_results(samples, records, root / "exports")
    success = len(records) == len(actions) and all(r.succeeded for r in records)
    atomic_json(root / "suite_status.json", {"status": "COMPLETE" if success else "PARTIAL",
                "planned_tasks": len(actions), "completed_tasks": len(records),
                "successful_tasks": sum(r.succeeded for r in records), "exports": exported["directory"]})
    return records
