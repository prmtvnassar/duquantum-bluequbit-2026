"""Hashes, environment identity, and atomic UTF-8 result files."""

import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import sys
import tempfile

PACKAGES = ("qiskit", "qiskit-aer", "quimb", "qiskit-addon-obp", "qiskit-addon-utils",
            "numpy", "scipy", "pandas", "matplotlib", "psutil")


def package_versions():
    result = {"python": platform.python_version()}
    for name in PACKAGES:
        try:
            result[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            result[name] = "NOT_INSTALLED"
    return result


def file_sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as stream:
        for block in iter(lambda: stream.read(2**20), b""):
            digest.update(block)
    return digest.hexdigest()


def source_sha256():
    digest = hashlib.sha256()
    for path in sorted(Path(__file__).parent.glob("*.py")):
        digest.update(path.name.encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()


def atomic_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)
            stream.write("\n")
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def environment_receipt(config):
    import psutil
    from dataclasses import asdict
    # Only selected non-secret scheduler fields are collected, never the full environment.
    scheduler = {name: os.environ[name] for name in
                 ("SLURM_JOB_ID", "SLURM_JOB_NAME", "SLURM_CPUS_PER_TASK", "SLURM_MEM_PER_NODE",
                  "JOB_NAME", "POD_NAME", "POD_UID", "POD_NAMESPACE") if name in os.environ}
    return {"platform": platform.platform(), "hostname": platform.node(),
            "python_executable": sys.executable, "package_versions": package_versions(),
            "source_sha256": source_sha256(), "config": asdict(config),
            "memory_total_bytes": psutil.virtual_memory().total,
            "memory_available_bytes": psutil.virtual_memory().available,
            "scheduler": scheduler, "requested_device": "CPU",
            "note": "Scheduler allocation is not proof of successful application execution."}
