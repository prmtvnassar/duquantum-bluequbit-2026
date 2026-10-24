"""Immutable raw experiment records and atomic derived checkpoints."""

from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path

import psutil
from bluequbit_samples.provenance import atomic_json
from .ledger import DEFAULT_ROOT, REPO


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, allow_nan=False).encode()).hexdigest()


class ExperimentStore:
    def __init__(self, root="results/workflow"):
        self.root = Path(root)
        (self.root / "records").mkdir(parents=True, exist_ok=True)
        self.canonical = DEFAULT_ROOT / "experiments" if self.root.resolve() == REPO / "results/workflow" else None
        if self.canonical:
            for saved in self.canonical.glob("*.json"):
                target = self.root / "records" / saved.name
                if not target.exists():
                    value = json.loads(saved.read_text())
                    if value["key"] != digest(value["action"]):
                        raise ValueError("Corrupt tracked experiment identity")
                    atomic_json(target,value)

    def records(self):
        return [json.loads(p.read_text(encoding="utf-8")) for p in sorted((self.root / "records").glob("*.json"))]

    def save(self, action, record):
        key = digest(action)
        path = self.root / "records" / f"{key}.json"
        if path.exists():
            item = json.loads(path.read_text(encoding="utf-8"))
            if self.canonical and not (self.canonical / path.name).exists():
                atomic_json(self.canonical / path.name,item)
            return item
        item = {"key": key, "action": action, "record": record, "saved_at": utc_now()}
        atomic_json(path, item)
        if self.canonical:
            atomic_json(self.canonical / path.name,item)
        return item

    @contextmanager
    def lock(self, name="runner"):
        if name not in {"runner","remote_runner"}:
            raise ValueError("Unknown lock name")
        path = self.root / f"{name}.lock"
        if path.exists():
            previous = json.loads(path.read_text())
            if psutil.pid_exists(previous["pid"]):
                raise RuntimeError("Another workflow runner is active")
            path.unlink()
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        with os.fdopen(fd, "w") as f:
            json.dump({"pid": os.getpid(), "created": utc_now()}, f)
        try:
            yield
        finally:
            path.unlink(missing_ok=True)
