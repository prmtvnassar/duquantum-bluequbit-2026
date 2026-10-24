"""Isolated CPU tasks with portable limits, integrity-checked caching, and receipts."""

from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import time
import uuid

import psutil

from .models import RunConfig, RunRecord
from .provenance import atomic_json, package_versions, source_sha256
from otoc.ledger import event, local_run_id, now, record_local, record_run, relative


def _digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def _kill_tree(process):
    try:
        children = psutil.Process(process.pid).children(recursive=True)
    except psutil.Error:
        children = []
    for child in reversed(children):
        try:
            child.kill()
        except psutil.Error:
            pass
    if process.poll() is None:
        process.kill()
    process.wait(timeout=10)


def _lock_busy(path):
    try:
        owner = json.loads(path.read_text(encoding="utf-8"))
        if owner.get("hostname") != platform.node():
            return True  # A different node's exit cannot be inferred locally.
        return any(psutil.pid_exists(int(owner[k])) for k in ("parent_pid", "worker_pid") if owner.get(k))
    except (OSError, ValueError, TypeError):
        return True


def execute(sample, method, parameters=None, config=None, output_dir="results/samples"):
    """Run one task. Only successful integrity-checked results are reused."""
    if method not in {"exact", "mps", "pps", "pps_threshold"}:
        raise ValueError("Unknown local simulation method")
    parameters = parameters or {}
    if method == "exact" and parameters:
        raise ValueError("Exact execution does not accept approximation parameters")
    allowed = {"mps": {"chi"}, "pps": {"eta"}, "pps_threshold": {"epsilon", "level"}}
    if set(parameters) - allowed.get(method, set()):
        raise ValueError("Unsupported method parameter")
    config = config or RunConfig()
    root = Path(output_dir)
    for subdir in ("cache", "attempts", "locks"):
        (root / subdir).mkdir(parents=True, exist_ok=True)
    identity = {"circuit_id": sample.circuit_id, "qubit": sample.qubit,
                "qasm_sha256": sample.qasm_sha256, "dataset_kind": sample.dataset_kind,
                "method": method, "parameters": parameters, "config": asdict(config),
                "source_sha256": source_sha256(), "package_versions": package_versions()}
    key = _digest(identity)
    cache_path = root / "cache" / f"{key}.json"
    if cache_path.exists():
        try:
            saved = json.loads(cache_path.read_text(encoding="utf-8"))
            if saved["identity"] == identity and saved["record_sha256"] == _digest(saved["record"]):
                result = RunRecord(**saved["record"])
                if result.succeeded:
                    result.cache_hit = True
                    event("cache_reuse", {"circuit_id": sample.circuit_id, "cache_key": key,
                                          "source_attempt": result.diagnostics.get("attempt_directory")})
                    return result
        except (OSError, ValueError, KeyError, TypeError):
            pass
    record = RunRecord(sample.circuit_id, sample.sample, sample.qubit, sample.num_qubits,
                       sample.qasm_sha256, sample.dataset_kind, method, parameters,
                       "FAILED", cache_key=key, package_versions=package_versions())
    lock_path = root / "locks" / f"{key}.lock"
    if lock_path.exists() and not _lock_busy(lock_path):
        lock_path.unlink(missing_ok=True)
    try:
        descriptor = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        record.status = "ALREADY_RUNNING"
        record.error = "Equivalent task has an active or unverified writer lock"
        event("blocked_duplicate", {"circuit_id": sample.circuit_id, "cache_key": key})
        return record
    owner = {"hostname": platform.node(), "parent_pid": os.getpid(),
             "created_at": datetime.now(timezone.utc).isoformat()}
    with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
        json.dump(owner, stream)
    attempt = root / "attempts" / f"{key[:16]}-{uuid.uuid4().hex[:12]}"
    attempt.mkdir()
    request_path, response_path = attempt / "request.json", attempt / "response.json"
    atomic_json(request_path, {"sample": asdict(sample), "method": method,
                              "parameters": parameters, "config": asdict(config)})
    record_run(local_run_id(attempt), {"circuit_id": sample.circuit_id, "problem": sample.sample,
               "qubit": sample.qubit, "origin": "local", "method": method, "parameters": parameters,
               "status": "RUNNING", "started_at": now(), "cost_usd": 0.0,
               "input_sha256": sample.qasm_sha256, "source_sha256": identity["source_sha256"],
               "reason": "Sample calibration from public QASM", "request": relative(request_path)})
    process = None
    started = time.perf_counter()
    peak_rss = 0
    memory_limit = config.effective_memory_mb() * 2**20
    try:
        env = os.environ.copy()
        env.update(OMP_NUM_THREADS=str(config.cpu_threads), OPENBLAS_NUM_THREADS=str(config.cpu_threads),
                   MKL_NUM_THREADS=str(config.cpu_threads), NUMBA_NUM_THREADS=str(config.cpu_threads),
                   PYTHONIOENCODING="utf-8", MPLBACKEND="Agg")
        with (attempt / "worker.log").open("w", encoding="utf-8") as log:
            process = subprocess.Popen(
                [sys.executable, "-m", "bluequbit_samples._worker", str(request_path.resolve()), str(response_path.resolve())],
                stdout=log, stderr=subprocess.STDOUT, env=env)
            owner["worker_pid"] = process.pid
            atomic_json(lock_path, owner)
            termination = None
            while process.poll() is None:
                try:
                    worker = psutil.Process(process.pid)
                    rss = sum(p.memory_info().rss for p in [worker, *worker.children(recursive=True)] if p.is_running())
                    peak_rss = max(peak_rss, rss)
                except psutil.Error:
                    pass
                if peak_rss > memory_limit:
                    termination = "MEMORY_LIMIT"
                    _kill_tree(process)
                    break
                if time.perf_counter() - started > config.walltime_seconds:
                    termination = "TIMED_OUT"
                    _kill_tree(process)
                    break
                time.sleep(0.05)
            if termination:
                record.status = termination
                record.error = "Worker terminated by the parent resource monitor; no estimate accepted"
            elif process.returncode == 0 and response_path.exists():
                record = RunRecord(**json.loads(response_path.read_text(encoding="utf-8")))
                record.cache_key = key
            else:
                record.error = f"Worker exited {process.returncode}; inspect {attempt / 'worker.log'}"
    except Exception as exc:
        record.status = "FAILED"
        record.error = f"{type(exc).__name__}: {exc}"
    finally:
        if process is not None and process.poll() is None:
            _kill_tree(process)
        lock_path.unlink(missing_ok=True)
    record.wall_seconds = time.perf_counter() - started
    record.peak_rss = max(peak_rss, int(record.diagnostics.get("worker_peak_rss", 0)))
    record.diagnostics.update(memory_limit_bytes=memory_limit, profile=config.profile,
                              attempt_directory=str(attempt), source_sha256=identity["source_sha256"],
                              recorded_at_utc=datetime.now(timezone.utc).isoformat())
    atomic_json(attempt / "record.json", record.to_dict())
    record_local(record.to_dict())
    if record.succeeded:
        payload = record.to_dict()
        atomic_json(cache_path, {"identity": identity, "record": payload, "record_sha256": _digest(payload)})
    with (root / "audit.jsonl").open("a", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(record.to_dict(), ensure_ascii=False, allow_nan=False) + "\n")
    return record

