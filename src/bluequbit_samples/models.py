"""Portable inputs, resource settings, and truthful result states."""

from dataclasses import asdict, dataclass, field
from typing import Any
import math


@dataclass(frozen=True)
class SampleCircuit:
    circuit_id: str
    sample: str
    qubit: int
    num_qubits: int
    qasm_sha256: str
    qasm_text: str
    source: str
    gate_count: int
    depth: int
    dataset_kind: str = "official"

    def __post_init__(self):
        if not 0 <= self.qubit < self.num_qubits:
            raise ValueError("Target qubit is outside the QASM register")
        if self.dataset_kind not in {"official", "synthetic"}:
            raise ValueError("dataset_kind must be official or synthetic")

    def manifest_row(self):
        return {k: v for k, v in asdict(self).items() if k != "qasm_text"}


@dataclass(frozen=True)
class RunConfig:
    profile: str = "local"
    cpu_threads: int = 2
    memory_limit_mb: int | None = None
    walltime_seconds: float = 300.0
    max_paulis: int = 200_000
    exact_crosscheck_max_qubits: int = 10
    check_atol: float = 1e-10
    pps_simplify_atol: float = 1e-12
    pps_simplify_rtol: float = 0.0
    expected_total: int = 50

    def __post_init__(self):
        if self.profile not in {"local", "nrp", "expanse"}:
            raise ValueError("Unknown execution profile")
        if self.cpu_threads < 1 or self.max_paulis < 1:
            raise ValueError("cpu_threads and max_paulis must be positive")
        if self.memory_limit_mb is not None and self.memory_limit_mb < 1:
            raise ValueError("memory_limit_mb must be positive")
        if not math.isfinite(self.walltime_seconds) or self.walltime_seconds <= 0:
            raise ValueError("walltime_seconds must be finite and positive")
        if self.exact_crosscheck_max_qubits < 0 or self.expected_total < 1:
            raise ValueError("Invalid crosscheck or expected-total setting")
        for value in (self.check_atol, self.pps_simplify_atol, self.pps_simplify_rtol):
            if not math.isfinite(value) or value < 0:
                raise ValueError("Tolerances must be finite and nonnegative")

    def effective_memory_mb(self):
        import os
        import psutil
        available = psutil.virtual_memory().available
        # psutil may see host RAM inside a container: also account for cgroup limits.
        for limit_file, used_file in [
            ("/sys/fs/cgroup/memory.max", "/sys/fs/cgroup/memory.current"),
            ("/sys/fs/cgroup/memory/memory.limit_in_bytes", "/sys/fs/cgroup/memory/memory.usage_in_bytes"),
        ]:
            try:
                from pathlib import Path
                raw = Path(limit_file).read_text().strip()
                if raw != "max":
                    available = min(available, max(0, int(raw) - int(Path(used_file).read_text())))
            except (OSError, ValueError):
                pass
        slurm_mb = os.environ.get("SLURM_MEM_PER_NODE")
        if slurm_mb:
            try:
                available = min(available, int(slurm_mb) * 2**20)
            except ValueError:
                pass
        safe_mb = max(1, int(0.60 * available / 2**20))
        return min(safe_mb, self.memory_limit_mb) if self.memory_limit_mb else safe_mb


@dataclass
class RunRecord:
    circuit_id: str
    sample: str
    qubit: int
    num_qubits: int
    qasm_sha256: str
    dataset_kind: str
    method: str
    parameters: dict[str, Any]
    status: str
    estimate: float | None = None
    dtype: str = "complex128"
    backend: str = ""
    wall_seconds: float = 0.0
    compute_seconds: float | None = None
    peak_rss: int | None = None
    package_versions: dict[str, str] = field(default_factory=dict)
    diagnostics: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
    cache_key: str | None = None
    cache_hit: bool = False

    @property
    def succeeded(self):
        return self.status == "SUCCEEDED" and self.estimate is not None and math.isfinite(self.estimate)

    def to_dict(self):
        return asdict(self)

