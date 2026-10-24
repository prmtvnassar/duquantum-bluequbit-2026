"""Where jobs actually run: BlueQubit (cloud) or a free offline stand-in for testing."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

from .targets import Target

# SDK run_status -> workbook Jobs status (the sheet's dropdown values).
STATUS = {
    "PENDING": "running", "QUEUED": "running", "RUNNING": "running",
    "COMPLETED": "succeeded", "CANCELED": "canceled",
    "FAILED_VALIDATION": "failed", "TERMINATED": "failed", "NOT_ENOUGH_FUNDS": "failed",
}


@dataclass
class Outcome:
    job_id: str
    status: str                  # running | succeeded | failed | canceled
    estimate: float | None = None
    wall_s: float | None = None
    credits: float | None = None
    error: str = ""


def job_options(cfg: dict, method: str, setting: float, transpile: int | None) -> tuple[str, dict]:
    backend = cfg["backend"]
    names = backend["option_names"]
    extra = backend.get("extra_options", {}).get(method, {})
    if method == "exact":
        return backend.get("exact_device", "cpu"), dict(extra)
    if method == "mps":
        return backend["mps_device"], {names["mps_setting"]: int(setting), **extra}
    options = {names["pps_setting"]: float(setting), **extra}
    if transpile is not None:
        options[names["pps_transpile"]] = int(transpile)
    return backend["pps_device"], options


def _scalar(value) -> float | None:
    if isinstance(value, (list, tuple)):
        if len(value) != 1:
            raise ValueError(f"expected one expectation value, got {len(value)}")
        value = value[0]
    return None if value is None else float(value)


class CloudBackend:
    mode = "cloud"

    def __init__(self, cfg: dict, client):
        self.cfg = cfg
        self.client = client

    def submit(self, target: Target, method: str, setting: float, transpile: int | None, name: str, tags: dict) -> Outcome:
        device, options = job_options(self.cfg, method, setting, transpile)
        result = self.client.run(target.circuit, device=device, asynchronous=True, job_name=name[:200],
                                 pauli_sum=list(target.pauli_sum), options=options, tags=tags)
        cap = self.cfg["limits"].get("max_cost_per_job")
        estimate = getattr(result, "estimated_cost", None)
        if cap is not None and estimate is not None and float(estimate) > float(cap):
            try:  # over budget: cancel before it runs up a bill
                self.client.cancel(result.job_id)
            except Exception:
                pass
            return Outcome(result.job_id, "canceled",
                           error=f"estimated cost ${float(estimate):.2f} > cap ${float(cap):.2f}; canceled")
        return self._outcome(result)

    def cancel(self, job_id: str) -> Outcome:
        try:
            result = self.client.cancel(job_id)
            out = self._outcome(result[0] if isinstance(result, list) else result)
        except Exception as exc:  # e.g. it finished just before the cancel landed
            out = self.poll([job_id])[0]
            if out.status == "running":
                out = Outcome(job_id, "canceled", error=f"cancel failed: {exc}")
        if out.status == "running":
            out.status = "canceled"
        return out

    def poll(self, job_ids: list[str]) -> list[Outcome]:
        if not job_ids:
            return []
        results = self.client.get(list(job_ids))
        return [self._outcome(r) for r in (results if isinstance(results, list) else [results])]

    @staticmethod
    def _outcome(r) -> Outcome:
        status = STATUS.get(r.run_status, "failed")
        out = Outcome(r.job_id, status, credits=r.cost,
                      wall_s=None if r.run_time_ms is None else r.run_time_ms / 1000,
                      error="" if status != "failed" else f"{r.run_status}: {r.error_message or ''}".strip())
        if status == "succeeded":
            try:
                out.estimate = _scalar(r.expectation_value)
            except ValueError as exc:
                out.status, out.error = "failed", str(exc)
            if out.estimate is None and out.status == "succeeded":
                out.status, out.error = "failed", "completed without an expectation value"
        return out


class OfflineBackend:
    """Exact statevector value, then a deterministic, FAKE approximation error that shrinks
    as χ grows or ε falls. Only for exercising the pipeline; the numbers mean nothing."""

    mode = "offline"

    def __init__(self, cfg: dict):
        self.cfg = cfg
        self.done: dict[str, Outcome] = {}

    def submit(self, target: Target, method: str, setting: float, transpile: int | None, name: str, tags: dict) -> Outcome:
        import numpy as np
        from qiskit.quantum_info import SparsePauliOp, Statevector

        if isinstance(target.circuit, str):
            raise ValueError("offline mode cannot run stored circuit IDs")
        job_options(self.cfg, method, setting, transpile)  # same option validation as cloud
        exact = float(np.real(Statevector(target.circuit).expectation_value(
            SparsePauliOp.from_list(list(target.pauli_sum)))))
        seed = int(hashlib.sha256(f"{name}".encode()).hexdigest()[:8], 16)
        noise = np.random.default_rng(seed).normal()
        if method == "exact":
            estimate = exact
        elif method == "mps":
            estimate = exact * (1 - 4 / setting) + noise * 0.5 / setting
        else:
            estimate = exact * (1 - 5 * setting) + noise * setting
        job_id = f"offline-{seed:08x}"
        self.done[job_id] = Outcome(job_id, "succeeded", float(estimate), wall_s=0.0, credits=0.0)
        return Outcome(job_id, "running")

    def cancel(self, job_id: str) -> Outcome:
        return Outcome(job_id, "canceled")

    def poll(self, job_ids: list[str]) -> list[Outcome]:
        return [self.done.get(j, Outcome(j, "failed", error="offline job lost (process restarted)")) for j in job_ids]
