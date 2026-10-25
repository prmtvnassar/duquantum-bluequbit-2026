"""Repository audit trail: one receipt per execution, plus atomic CSV views.

Receipts are written before execution. Cache reuse is an event, never a new run.
The lock serializes local and remote writers; no credentials or QASM are stored.
"""

from contextlib import contextmanager
import csv
from datetime import datetime, timezone
import errno
import hashlib
import io
import json
import os
from pathlib import Path
import tempfile
import time
import uuid

import psutil

if os.name == "nt":
    import msvcrt
else:
    import fcntl

REPO = Path(__file__).resolve().parents[2]
DEFAULT_ROOT = REPO / "runs"
FIELDS = ("run_id", "circuit_id", "problem", "qubit", "origin", "method", "backend",
          "parameters_json", "status", "estimate", "cost_usd", "wall_seconds",
          "job_id", "started_at", "finished_at", "input_sha256", "source_sha256",
          "reason", "error", "receipt")


def now():
    return datetime.now(timezone.utc).isoformat()


def relative(path):
    path = Path(path).resolve()
    return path.relative_to(REPO).as_posix() if path.is_relative_to(REPO) else str(path)


def atomic_bytes(path, content):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(dir=path.parent, prefix=path.name + ".", suffix=".tmp")
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        # Windows indexers may hold a just-written CSV briefly. A persistent lock
        # still fails closed instead of allowing an unlogged simulation.
        for retry in range(20):
            try:
                os.replace(temporary, path)
                break
            except PermissionError:
                if retry == 19:
                    raise
                time.sleep(.05)
    finally:
        Path(temporary).unlink(missing_ok=True)


def csv_bytes(fields, rows):
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=fields, lineterminator="\n", extrasaction="ignore")
    writer.writeheader()
    writer.writerows(rows)
    return buffer.getvalue().encode("utf-8")


@contextmanager
def _writer_guard(path, deadline):
    # Keep this inode/file identity permanently: unlinking an advisory lock lets
    # waiters lock different files. The OS releases the guard after a crash.
    with path.open("a+b") as stream:
        stream.seek(0, os.SEEK_END)
        if not stream.tell():
            stream.write(b"\0")
            stream.flush()
        while True:
            try:
                stream.seek(0)
                if os.name == "nt":
                    msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except OSError as exc:
                if exc.errno not in {errno.EACCES, errno.EAGAIN, errno.EDEADLK}:
                    raise
                if time.monotonic() >= deadline:
                    raise RuntimeError("Run ledger is locked; execution must not proceed unrecorded") from None
                time.sleep(.05)
        try:
            yield
        finally:
            stream.seek(0)
            if os.name == "nt":
                msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(stream.fileno(), fcntl.LOCK_UN)


def _release_lock(path):
    # Windows readers/indexers may briefly deny deletion. Keep ownership until
    # release succeeds; a persistent denial raises and leaves the PID lock intact.
    for retry in range(20):
        try:
            path.unlink(missing_ok=True)
            return
        except PermissionError:
            if retry == 19:
                raise
            time.sleep(.05)


@contextmanager
def locked(root=DEFAULT_ROOT):
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    path = root / ".ledger.lock"
    deadline = time.monotonic() + 30
    # Serialize stale-PID inspection/removal as well as ownership. Without this
    # guard a second reclaimer can delete a newly acquired PID lock after reading
    # the same dead owner. The PID file also respects already-running old writers.
    with _writer_guard(root / ".ledger.guard", deadline):
        while True:
            try:
                fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                with os.fdopen(fd, "w") as stream:
                    json.dump({"pid": os.getpid()}, stream)
                break
            except FileExistsError:
                try:
                    if not psutil.pid_exists(json.loads(path.read_text())["pid"]):
                        _release_lock(path)
                        continue
                except (ValueError, OSError, KeyError):
                    pass
                if time.monotonic() >= deadline:
                    raise RuntimeError("Run ledger is locked; execution must not proceed unrecorded")
                time.sleep(.05)
        try:
            yield
        finally:
            _release_lock(path)


def _event(root, kind, payload):
    value = {"event_id": uuid.uuid4().hex, "recorded_at": now(), "kind": kind, **payload}
    # One small atomic file per event survives interruption; CSV views can be rebuilt.
    path = Path(root) / "events" / (value["event_id"] + ".json")
    atomic_bytes(path, (json.dumps(value, indent=2, allow_nan=False) + "\n").encode())
    index = Path(root) / "decisions.csv"
    fields = ("event_id","recorded_at","kind","details_json")
    rows = []
    if index.exists():
        with index.open(newline="",encoding="utf-8") as stream:
            rows = list(csv.DictReader(stream))
    rows.append({"event_id":value["event_id"],"recorded_at":value["recorded_at"],"kind":kind,
                 "details_json":json.dumps(payload,sort_keys=True,allow_nan=False)})
    atomic_bytes(index,csv_bytes(fields,rows))


def event(kind, payload, root=DEFAULT_ROOT):
    with locked(root):
        _event(root, kind, payload)


def _views(root):
    root = Path(root)
    receipts = sorted((json.loads(p.read_text()) for p in (root / "records").glob("*.json")),
                      key=lambda r: (r.get("started_at") or "", r["run_id"]))
    rows = []
    for record in receipts:
        rows.append({**record, "parameters_json": json.dumps(record.get("parameters", {}), sort_keys=True),
                     "receipt": relative(root / "records" / (record["run_id"] + ".json"))})
    atomic_bytes(root / "jobs.csv", csv_bytes(FIELDS, rows))
    estimates = [r for r in rows if r["status"] in {"SUCCEEDED", "COMPLETED"} and r.get("estimate") is not None]
    atomic_bytes(root / "estimates.csv", csv_bytes(FIELDS, estimates))


def record_run(run_id, values, root=DEFAULT_ROOT):
    if not run_id or any(c not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_" for c in run_id):
        raise ValueError("Invalid ledger run identity")
    with locked(root):
        path = Path(root) / "records" / f"{run_id}.json"
        previous = json.loads(path.read_text()) if path.exists() else {}
        for identity in ("circuit_id", "method", "origin", "parameters", "job_id"):
            if identity == "parameters" and previous.get(identity) and values.get(identity):
                if all(values[identity].get(k) == v for k, v in previous[identity].items()):
                    continue  # The solver may add explicit effective defaults.
            if previous.get(identity) and values.get(identity) and previous[identity] != values[identity]:
                raise ValueError(f"Cannot change execution identity: {identity}")
        updated = {**previous, **values, "run_id": run_id}
        if updated == previous:
            return updated
        atomic_bytes(path, (json.dumps(updated, indent=2, allow_nan=False) + "\n").encode())
        _event(root, "run_state", {"run_id": run_id, "status": updated["status"],
                                   "previous_status": previous.get("status")})
        _views(root)
        return updated


def local_run_id(attempt):
    return "local-" + Path(attempt).name


def record_local(record, root=DEFAULT_ROOT, started_at=None):
    d = record.get("diagnostics", {})
    attempt = d.get("attempt_directory")
    if not attempt:
        raise ValueError("A local run needs its unique attempt directory")
    return record_run(local_run_id(attempt), {
        "circuit_id": record["circuit_id"], "problem": record["sample"], "qubit": record["qubit"],
        "origin": "local", "method": record["method"], "backend": record.get("backend", ""),
        "parameters": record["parameters"], "status": record["status"], "estimate": record.get("estimate"),
        "cost_usd": 0.0, "wall_seconds": record.get("wall_seconds"),
        "finished_at": d.get("recorded_at_utc"), "input_sha256": record["qasm_sha256"],
        "source_sha256": d.get("source_sha256"), "error": record.get("error"),
        "reason": "Sample calibration from public QASM", "raw_record": relative(Path(attempt) / "record.json"),
        "diagnostics": d, "package_versions": record.get("package_versions", {}),
        **({"started_at": started_at} if started_at else {}),
    }, root)


def record_remote(saved, root=DEFAULT_ROOT):
    action = saved["action"]
    key = hashlib.sha256(json.dumps(action, sort_keys=True, allow_nan=False).encode()).hexdigest()
    cid = action["circuit_id"]
    reason = saved.get("scheduler_justification", "Free exact sample reference")
    vector = {}
    if action.get("observables"):
        # Observable-list job (e.g. all_z): the CSV scalar `estimate` is the target
        # <Z_q> component; the full vector is kept only in this JSON record.
        vector = {"observables": action["observables"], "estimates_vector": saved.get("estimates_vector")}
        reason = f"observables={action['observables']} job; estimate is the <Z_q> component of estimates_vector; {reason}"
    return record_run("remote-" + key, {
        "circuit_id": cid, "problem": cid.split("_")[1], "qubit": int(cid.split("_")[2]),
        "origin": "bluequbit", "method": "exact" if action["device"] in {"cpu","gpu"} else action["device"],
        "backend": action["device"], "parameters": action["options"], "status": saved["status"],
        "estimate": saved.get("estimate"), "job_id": saved.get("job_id"), "cost_usd": saved.get("cost_usd"),
        "started_at": saved.get("requested_at"), "finished_at": saved.get("updated_at"),
        "wall_seconds": ((saved.get("compute_ms") or 0) + (saved.get("queue_ms") or 0))/1000,
        "reason": reason,
        "quote": saved.get("quote"), "error": saved.get("error"), "pauli": action["pauli"],
        "remote_receipt": saved, **vector,
    }, root)


def sync_history(repo=REPO, root=DEFAULT_ROOT):
    """Backfill every persisted worker request, including unfinished attempts."""
    repo, root = Path(repo), Path(root)
    counts = {"local_attempts": 0, "remote_attempts": 0, "unfinished": 0}
    active = set()
    for path in (repo / "results").rglob("*.lock"):
        try:
            value = json.loads(path.read_text())
            if any(psutil.pid_exists(int(value.get(k, 0))) for k in ("pid", "parent_pid", "worker_pid") if value.get(k)):
                active.add(path.stem)
        except (ValueError, OSError):
            pass
    for request in (repo / "results").glob("**/attempts/*/request.json"):
        attempt = request.parent
        data = json.loads(request.read_text())
        record = attempt / "record.json"
        started = datetime.fromtimestamp(request.stat().st_mtime, timezone.utc).isoformat()
        if record.exists():
            record_local(json.loads(record.read_text()), root, started_at=started)
        else:
            sample = data["sample"]
            running = any(key.startswith(attempt.name.split("-")[0]) for key in active)
            record_run(local_run_id(attempt), {"circuit_id": sample["circuit_id"], "problem": sample["sample"],
                       "qubit": sample["qubit"], "origin": "local", "method": data["method"],
                       "parameters": data["parameters"], "status": "RUNNING" if running else "INTERRUPTED_UNRESOLVED",
                       "started_at": started, "cost_usd": 0.0, "input_sha256": sample["qasm_sha256"],
                       "reason": "Recovered persisted worker request; no terminal receipt yet"}, root)
            counts["unfinished"] += 1
        counts["local_attempts"] += 1
    for path in (repo / "results/workflow/remote_actions").glob("*.json"):
        record_remote(json.loads(path.read_text()), root)
        counts["remote_attempts"] += 1
    for path in (repo / "results/workflow/records").glob("*.json"):
        target=root / "experiments" / path.name
        if target.exists() and target.read_bytes()!=path.read_bytes():
            raise ValueError("Tracked experiment differs from its immutable source")
        if not target.exists():
            atomic_bytes(target,path.read_bytes())
    with locked(root):
        events = sorted((json.loads(p.read_text()) for p in (root / "events").glob("*.json")),
                        key=lambda e:e["recorded_at"])
        rows = [{"event_id":e["event_id"],"recorded_at":e["recorded_at"],"kind":e["kind"],
                 "details_json":json.dumps({k:v for k,v in e.items() if k not in {"event_id","recorded_at","kind"}},sort_keys=True)}
                for e in events]
        atomic_bytes(root / "decisions.csv",csv_bytes(("event_id","recorded_at","kind","details_json"),rows))
        _views(root)
    atomic_bytes(root / "reconciliation.json", (json.dumps({"checked_at": now(), **counts}, indent=2)+"\n").encode())
    return counts
