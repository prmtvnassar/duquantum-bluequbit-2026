"""Plain-CSV run records for scripts and agents.

Use the helpers below as the sole writer. Each update rewrites one small CSV
atomically; concurrent writers to the same file must be serialized by the caller.
"""

from __future__ import annotations

import csv
from contextlib import contextmanager
from datetime import datetime, timezone
from functools import wraps
import hashlib
import io
import json
import math
import os
from pathlib import Path
import tempfile
import time
from typing import Any, Mapping

from .submission import HEADER as SELECTED_HEADER, SubmissionError, read_template


TARGET_HEADER = ("circuit", "qubit")
JOB_HEADER = (
    "run_key", "dataset", "circuit", "method", "device", "kit_version", "attempt",
    "options_json", "qubits_json", "status", "job_id", "started_at_utc",
    "finished_at_utc", "wall_seconds", "credits_consumed", "error",
)
ESTIMATE_HEADER = ("run_key", "dataset", "circuit", "qubit", "estimate", "recorded_at_utc")
DATASETS = {"sample", "hidden"}
METHODS = {"mps", "pps", "exact"}
STATUSES = {"planned", "queued", "running", "succeeded", "failed", "canceled"}


class RunCsvError(ValueError):
    """A run record is malformed or conflicts with existing records."""


@contextmanager
def _runs_lock(runs_dir: Path):
    """Serialize read-modify-write operations across local agent processes."""
    runs_dir.mkdir(parents=True, exist_ok=True)
    lock_path = runs_dir / ".records.lock"
    with lock_path.open("a+b") as handle:
        handle.seek(0, os.SEEK_END)
        if handle.tell() == 0:
            handle.write(b"0")
            handle.flush()
        deadline = time.monotonic() + 10
        while True:
            try:
                handle.seek(0)
                if os.name == "nt":
                    import msvcrt

                    msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl

                    fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except OSError as exc:
                if time.monotonic() >= deadline:
                    raise RunCsvError(f"Timed out waiting for run CSV lock: {lock_path}") from exc
                time.sleep(0.1)
        try:
            yield
        finally:
            handle.seek(0)
            if os.name == "nt":
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def _serialized(function):
    @wraps(function)
    def wrapper(runs_dir: Path, *args, **kwargs):
        with _runs_lock(Path(runs_dir)):
            return function(runs_dir, *args, **kwargs)

    return wrapper


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _required_text(value: Any, label: str) -> str:
    text = str(value).strip() if value is not None else ""
    if not text:
        raise RunCsvError(f"{label} is required")
    return text


def _csv_payload(header: tuple[str, ...], rows: list[Mapping[str, str]]) -> bytes:
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=header, lineterminator="\n", extrasaction="raise")
    writer.writeheader()
    for row in rows:
        writer.writerow(row)
    return buffer.getvalue().encode("utf-8")


def _write_table(path: Path, header: tuple[str, ...], rows: list[Mapping[str, str]], *, create_only: bool = False) -> bool:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = _csv_payload(header, rows)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile("wb", dir=path.parent, prefix=".runs-", suffix=".tmp", delete=False) as output:
            temporary = Path(output.name)
            output.write(payload)
            output.flush()
            os.fsync(output.fileno())
        if create_only:
            try:
                os.link(temporary, path)
            except FileExistsError:
                if path.read_bytes() == payload:
                    return False
                raise RunCsvError(f"Refusing to replace existing run CSV: {path}")
        else:
            os.replace(temporary, path)
        return True
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def _read_table(path: Path, header: tuple[str, ...]) -> list[dict[str, str]]:
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as source:
            reader = csv.DictReader(source)
            if tuple(reader.fieldnames or ()) != header:
                raise RunCsvError(f"{path}: expected header {','.join(header)}")
            rows = list(reader)
    except (OSError, UnicodeError, csv.Error) as exc:
        raise RunCsvError(f"Cannot read {path}: {exc}") from exc
    for line_number, row in enumerate(rows, 2):
        if None in row or any(value is None for value in row.values()):
            raise RunCsvError(f"{path}:{line_number}: wrong number of columns")
    return rows


def prepare_run_csv(template_path: Path, dataset: str, runs_dir: Path) -> dict[str, Path]:
    """Create template-ordered target and selection files, preserving existing data."""
    if dataset not in DATASETS:
        raise RunCsvError(f"dataset must be one of {sorted(DATASETS)}")
    try:
        targets = read_template(template_path)
    except SubmissionError as exc:
        raise RunCsvError(str(exc)) from exc
    runs_dir = Path(runs_dir)
    paths = {
        "targets": runs_dir / f"targets_{dataset}.csv",
        "selected": runs_dir / f"selected_{dataset}.csv",
        "jobs": runs_dir / "jobs.csv",
        "estimates": runs_dir / "estimates.csv",
    }
    _write_table(paths["targets"], TARGET_HEADER, [dict(zip(TARGET_HEADER, key)) for key in targets], create_only=True)
    _write_table(
        paths["selected"], SELECTED_HEADER,
        [{"circuit": circuit, "qubit": qubit, "estimate": ""} for circuit, qubit in targets],
        create_only=True,
    )
    _write_table(paths["jobs"], JOB_HEADER, [], create_only=True)
    _write_table(paths["estimates"], ESTIMATE_HEADER, [], create_only=True)
    return paths


def action_key(
    *, dataset: str, circuit: str, method: str, device: str,
    kit_version: str, options: Mapping[str, Any], qubits: list[str], attempt: int = 1,
) -> str:
    """Stable key for one configuration and its affected observable set."""
    payload = {
        "dataset": dataset, "circuit": circuit, "method": method, "device": device,
        "kit_version": kit_version, "attempt": attempt,
        "options": options, "qubits": sorted(qubits),
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _normalize_job(record: Mapping[str, Any]) -> dict[str, str]:
    dataset = _required_text(record.get("dataset"), "dataset").lower()
    method = _required_text(record.get("method"), "method").lower()
    status = _required_text(record.get("status"), "status").lower()
    if dataset not in DATASETS or method not in METHODS or status not in STATUSES:
        raise RunCsvError("Invalid dataset, method, or status")
    circuit = _required_text(record.get("circuit"), "circuit")
    device = _required_text(record.get("device"), "device")
    kit_version = _required_text(record.get("kit_version"), "kit_version")
    try:
        attempt = int(record.get("attempt", 1))
    except (TypeError, ValueError) as exc:
        raise RunCsvError("attempt must be a positive integer") from exc
    if attempt < 1 or str(attempt) != str(record.get("attempt", 1)):
        raise RunCsvError("attempt must be a positive integer")
    options = record.get("options", {})
    qubits = record.get("qubits", [])
    if not isinstance(options, dict) or not isinstance(qubits, list) or not qubits:
        raise RunCsvError("options must be an object and qubits a nonempty list")
    qubits = [_required_text(value, "qubit") for value in qubits]
    if len(qubits) != len(set(qubits)):
        raise RunCsvError("Job qubits must be unique")
    try:
        options_json = json.dumps(options, sort_keys=True, separators=(",", ":"), allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise RunCsvError(f"options are not JSON-safe: {exc}") from exc
    run_key = action_key(
        dataset=dataset, circuit=circuit, method=method, device=device,
        kit_version=kit_version, options=options, qubits=qubits, attempt=attempt,
    )
    if record.get("run_key") not in (None, "", run_key):
        raise RunCsvError("Supplied run_key does not match the action configuration")
    row = {
        "run_key": run_key, "dataset": dataset, "circuit": circuit,
        "method": method, "device": device, "kit_version": kit_version,
        "attempt": str(attempt),
        "options_json": options_json,
        "qubits_json": json.dumps(sorted(qubits), separators=(",", ":"), ensure_ascii=False),
        "status": status,
        "job_id": str(record.get("job_id") or ""),
        "started_at_utc": str(record.get("started_at_utc") or ""),
        "finished_at_utc": str(record.get("finished_at_utc") or ""),
        "wall_seconds": str(record.get("wall_seconds") if record.get("wall_seconds") is not None else ""),
        "credits_consumed": str(record.get("credits_consumed") if record.get("credits_consumed") is not None else ""),
        "error": str(record.get("error") or ""),
    }
    for field in ("wall_seconds", "credits_consumed"):
        if row[field]:
            try:
                value = float(row[field])
            except ValueError as exc:
                raise RunCsvError(f"{field} must be numeric") from exc
            if not math.isfinite(value) or value < 0:
                raise RunCsvError(f"{field} must be a finite nonnegative number")
    return row


@_serialized
def upsert_job(runs_dir: Path, record: Mapping[str, Any]) -> str:
    """Create or update one job while preserving its action identity."""
    runs_dir = Path(runs_dir)
    path = runs_dir / "jobs.csv"
    rows = _read_table(path, JOB_HEADER)
    row = _normalize_job(record)
    targets = _read_table(runs_dir / f"targets_{row['dataset']}.csv", TARGET_HEADER)
    allowed = {(target["circuit"], target["qubit"]) for target in targets}
    unexpected = [qubit for qubit in json.loads(row["qubits_json"]) if (row["circuit"], qubit) not in allowed]
    if unexpected:
        raise RunCsvError(f"Job contains targets absent from the official template: {unexpected[:5]}")
    matching = [i for i, existing in enumerate(rows) if existing["run_key"] == row["run_key"]]
    if len(matching) > 1:
        raise RunCsvError(f"Duplicate run_key in {path}: {row['run_key']}")
    if matching:
        index = matching[0]
        old = rows[index]
        identity = ("dataset", "circuit", "method", "device", "kit_version", "attempt", "options_json", "qubits_json")
        if any(old[field] != row[field] for field in identity):
            raise RunCsvError("Cannot change a recorded action's identity")
        if old["status"] == "succeeded" and row["status"] != "succeeded":
            raise RunCsvError("Cannot regress a succeeded job to an unfinished status")
        if old["job_id"] and row["job_id"] and old["job_id"] != row["job_id"]:
            raise RunCsvError("A new platform job ID requires a new run attempt record")
        for field in ("job_id", "started_at_utc", "finished_at_utc", "wall_seconds", "credits_consumed", "error"):
            if not row[field]:
                row[field] = old[field]
        if row["status"] == "succeeded":
            row["error"] = ""
        rows[index] = row
    else:
        rows.append(row)
    _write_table(path, JOB_HEADER, rows)
    return row["run_key"]


@_serialized
def record_estimate(runs_dir: Path, record: Mapping[str, Any]) -> None:
    """Add one immutable numeric estimate from a recorded job."""
    runs_dir = Path(runs_dir)
    run_key = _required_text(record.get("run_key"), "run_key")
    qubit = _required_text(record.get("qubit"), "qubit")
    jobs = _read_table(runs_dir / "jobs.csv", JOB_HEADER)
    matching = [job for job in jobs if job["run_key"] == run_key]
    if len(matching) != 1:
        raise RunCsvError(f"Unknown or duplicate run_key: {run_key}")
    job = matching[0]
    if job["status"] != "succeeded":
        raise RunCsvError("Record estimates only after the job succeeds")
    if qubit not in json.loads(job["qubits_json"]):
        raise RunCsvError(f"Qubit {qubit!r} is not covered by this job")
    targets = _read_table(runs_dir / f"targets_{job['dataset']}.csv", TARGET_HEADER)
    if (job["circuit"], qubit) not in {(row["circuit"], row["qubit"]) for row in targets}:
        raise RunCsvError(f"Estimate target is absent from official template: {(job['circuit'], qubit)}")
    try:
        value = float(record.get("estimate"))
    except (TypeError, ValueError) as exc:
        raise RunCsvError("estimate must be numeric") from exc
    if not math.isfinite(value):
        raise RunCsvError("estimate must be finite")
    path = runs_dir / "estimates.csv"
    rows = _read_table(path, ESTIMATE_HEADER)
    previous = [row for row in rows if (row["run_key"], row["qubit"]) == (run_key, qubit)]
    normalized = format(value, ".17g")
    if previous:
        if len(previous) == 1 and previous[0]["estimate"] == normalized:
            return
        raise RunCsvError(f"Conflicting estimate already recorded for {(run_key, qubit)}")
    rows.append({
        "run_key": run_key, "dataset": job["dataset"], "circuit": job["circuit"],
        "qubit": qubit, "estimate": normalized, "recorded_at_utc": _now(),
    })
    _write_table(path, ESTIMATE_HEADER, rows)


@_serialized
def select_estimate(runs_dir: Path, record: Mapping[str, Any]) -> None:
    """Set one submission candidate value without changing target order or keys."""
    runs_dir = Path(runs_dir)
    dataset = _required_text(record.get("dataset"), "dataset").lower()
    if dataset not in DATASETS:
        raise RunCsvError(f"dataset must be one of {sorted(DATASETS)}")
    target = (
        _required_text(record.get("circuit"), "circuit"),
        _required_text(record.get("qubit"), "qubit"),
    )
    targets = _read_table(runs_dir / f"targets_{dataset}.csv", TARGET_HEADER)
    target_keys = [(row["circuit"], row["qubit"]) for row in targets]
    if target not in target_keys or len(target_keys) != len(set(target_keys)):
        raise RunCsvError(f"Unknown or duplicate target: {target}")
    try:
        value = float(record.get("estimate"))
    except (TypeError, ValueError) as exc:
        raise RunCsvError("estimate must be numeric") from exc
    if not math.isfinite(value):
        raise RunCsvError("estimate must be finite")
    path = runs_dir / f"selected_{dataset}.csv"
    rows = _read_table(path, SELECTED_HEADER)
    selected_keys = [(row["circuit"], row["qubit"]) for row in rows]
    if selected_keys != target_keys:
        raise RunCsvError(f"Selected CSV no longer matches the template order: {path}")
    rows[selected_keys.index(target)]["estimate"] = format(value, ".17g")
    _write_table(path, SELECTED_HEADER, rows)


@_serialized
def validate_run_csv(runs_dir: Path) -> tuple[int, int]:
    """Check all present run records and return job/estimate counts."""
    runs_dir = Path(runs_dir)
    jobs = _read_table(runs_dir / "jobs.csv", JOB_HEADER)
    estimates = _read_table(runs_dir / "estimates.csv", ESTIMATE_HEADER)
    job_by_key: dict[str, dict[str, str]] = {}
    for job in jobs:
        try:
            options = json.loads(job["options_json"])
            qubits = json.loads(job["qubits_json"])
        except json.JSONDecodeError as exc:
            raise RunCsvError(f"Malformed JSON for run {job['run_key']}") from exc
        candidate = dict(job)
        candidate["options"] = options
        candidate["qubits"] = qubits
        if _normalize_job(candidate)["run_key"] != job["run_key"]:
            raise RunCsvError(f"Invalid run key: {job['run_key']}")
        if job["run_key"] in job_by_key:
            raise RunCsvError(f"Duplicate run key: {job['run_key']}")
        targets = _read_table(runs_dir / f"targets_{job['dataset']}.csv", TARGET_HEADER)
        allowed = {(target["circuit"], target["qubit"]) for target in targets}
        if any((job["circuit"], qubit) not in allowed for qubit in qubits):
            raise RunCsvError(f"Job contains a target absent from the official template: {job['run_key']}")
        job_by_key[job["run_key"]] = job
    seen: set[tuple[str, str]] = set()
    for estimate in estimates:
        key = (estimate["run_key"], estimate["qubit"])
        if key in seen:
            raise RunCsvError(f"Duplicate estimate: {key}")
        seen.add(key)
        job = job_by_key.get(estimate["run_key"])
        if job is None or job["status"] != "succeeded":
            raise RunCsvError(f"Estimate has no succeeded job: {key}")
        if estimate["dataset"] != job["dataset"] or estimate["circuit"] != job["circuit"]:
            raise RunCsvError(f"Estimate/job identity mismatch: {key}")
        if estimate["qubit"] not in json.loads(job["qubits_json"]):
            raise RunCsvError(f"Estimate qubit is outside job coverage: {key}")
        targets = _read_table(runs_dir / f"targets_{job['dataset']}.csv", TARGET_HEADER)
        if (estimate["circuit"], estimate["qubit"]) not in {
            (row["circuit"], row["qubit"]) for row in targets
        }:
            raise RunCsvError(f"Estimate target is absent from official template: {key}")
        try:
            value = float(estimate["estimate"])
        except ValueError as exc:
            raise RunCsvError(f"Nonnumeric estimate: {key}") from exc
        if not math.isfinite(value):
            raise RunCsvError(f"Nonfinite estimate: {key}")
    return len(jobs), len(estimates)
