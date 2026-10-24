"""Plan jobs, apply safety checks, submit, poll and record results."""

from __future__ import annotations

import hashlib
import json
import shutil
import time
from dataclasses import dataclass
from pathlib import Path

from .backends import Outcome, job_options
from .config import OFFLINE_DIR, ROOT, circuit_config
from .ledger import Ledger
from .targets import Target
from .workbook import ESTIMATES, JOBS, QUBIT_IDS, STATUS_COUNT, STATUS_ID, Workbook, qubit_cell


@dataclass
class Job:
    circuit: str          # config key, e.g. "sample_1"
    target: Target
    method: str           # "mps" | "pps"
    setting: float        # χ or ε
    transpile: int | None
    device: str
    key: str              # cache key

    @property
    def name(self) -> str:
        return f"{self.circuit}-q{self.target.qubit}-{self.method}{_fmt(self.setting)}"

    @property
    def tags(self) -> dict:
        return {"circuit": self.circuit, "qubit": self.target.qubit, "method": self.method,
                "setting": self.setting, "transpile": self.transpile}


def _fmt(x: float) -> str:
    return str(int(x)) if float(x).is_integer() else repr(float(x))


def job_key(cfg: dict, target: Target, method: str, setting: float, transpile: int | None) -> str:
    device, options = job_options(cfg, method, setting, transpile)
    blob = json.dumps([target.fingerprint(), list(target.pauli_sum), device, options], sort_keys=True, default=str)
    return hashlib.sha256(blob.encode()).hexdigest()[:20]


def workbook_path(cfg: dict, circuit: str, offline: bool) -> Path:
    """Offline runs write to copies under scratch/offline/, never to runs/."""
    real = ROOT / circuit_config(cfg, circuit)["workbook"]
    if not offline:
        return real
    copy = OFFLINE_DIR / real.name
    if not copy.exists():
        copy.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(real, copy)
    return copy


def ledger_for(offline: bool) -> Ledger:
    return Ledger((OFFLINE_DIR if offline else ROOT / "runs") / "ledger.csv")


def resolve_settings(wb: Workbook, method: str, slots: list[int], explicit: list[float]) -> tuple[list[float], list[str]]:
    """Settings to run, plus warnings. Slots read Status so values match the formulas exactly."""
    if method == "exact":
        return [0.0], []
    ladder = wb.settings(method)
    warnings = []
    chosen = []
    for s in slots:
        value = ladder[s - 1]
        if not isinstance(value, float):
            raise ValueError(f"{wb.path.name}: Status has no {method.upper()} setting in slot {s}")
        chosen.append(value)
    for value in explicit:
        if value not in ladder:
            warnings.append(f"{wb.path.name}: {method.upper()} setting {_fmt(value)} is not in the Status slots "
                            f"{[_fmt(v) for v in ladder if v is not None]}; the Qubits sheet won't show it.")
        chosen.append(float(value))
    return chosen, warnings


def accepted_keys(wb: Workbook) -> set[tuple]:
    """(qubit, method, setting, transpile) with Accepted = 1 already in the Estimates sheet."""
    keys = set()
    for values in wb.table(ESTIMATES["sheet"], ESTIMATES["first"], ESTIMATES["last"], ESTIMATES["cols"]).values():
        qubit, method, chi, eps, transpile, _, _, accepted = values
        if accepted == 1 and qubit not in (None, ""):
            keys.add(_estimate_key(qubit, method, chi, eps, transpile))
    sheet, _, first, last = QUBIT_IDS
    for qubit, exact in wb.table(sheet, first, last, ["A", "B"]).values():
        if qubit not in (None, "") and isinstance(exact, float):
            keys.add(_estimate_key(qubit, "exact", None, 0.0, None))
    return keys


def _estimate_key(qubit, method, chi, eps, transpile) -> tuple:
    q = str(int(qubit)) if isinstance(qubit, float) and qubit.is_integer() else str(qubit).strip()
    m = str(method).strip().lower()
    return (q, m, chi if m == "mps" else eps, transpile if m == "pps" else None)


def record(wb: Workbook, job_row: dict, outcome: Outcome, jobs_row: bool = True) -> None:
    """Jobs row for every finished job; Estimates row (Accepted = 1) for successes.
    An earlier accepted estimate for the same qubit and setting is set to 0, not deleted."""
    method = job_row["method"]
    if method == "exact":
        record_exact(wb, job_row, outcome, jobs_row)
        return
    setting = float(job_row["setting"])
    transpile = float(job_row["transpile"]) if job_row.get("transpile") not in (None, "") else None
    chi, eps = (setting, None) if method == "mps" else (None, setting)
    if jobs_row:
        wb.append_row(JOBS, [outcome.job_id, method.upper(), chi, eps, transpile if method == "pps" else None,
                             outcome.status, qubit_cell(job_row["qubit"]), outcome.wall_s, outcome.credits,
                             outcome.error or f"runner {job_row['job_key']}"])
    if outcome.status != "succeeded":
        return
    key = _estimate_key(job_row["qubit"], method, chi, eps, transpile)
    table = wb.table(ESTIMATES["sheet"], ESTIMATES["first"], ESTIMATES["last"], ESTIMATES["cols"])
    for row, values in table.items():
        if values[7] == 1 and values[0] not in (None, "") and _estimate_key(*values[:5]) == key:
            wb.set(ESTIMATES["sheet"], f"H{row}", 0)
    wb.append_row(ESTIMATES, [qubit_cell(job_row["qubit"]), method.upper(), chi, eps,
                              transpile if method == "pps" else None, outcome.estimate, outcome.job_id, 1])


def record_exact(wb: Workbook, job_row: dict, outcome: Outcome, jobs_row: bool = True) -> None:
    """Exact results: a Jobs row, and the value in Qubits!B ("Exact sample") on the qubit's row."""
    if jobs_row:
        wb.append_row(JOBS, [outcome.job_id, "Exact", None, None, None, outcome.status, qubit_cell(job_row["qubit"]),
                             outcome.wall_s, outcome.credits, outcome.error or f"runner {job_row['job_key']}"])
    if outcome.status != "succeeded":
        return
    sheet, col, first, last = QUBIT_IDS
    for row, value in zip(range(first, last + 1), wb.column(sheet, col, first, last)):
        if value is not None and _estimate_key(value, "exact", None, None, None)[0] == str(job_row["qubit"]):
            wb.set(sheet, f"B{row}", outcome.estimate)
            return
    raise ValueError(f"{wb.path.name}: qubit {job_row['qubit']} is not in Qubits!A; run --setup first")


def backfill(wb: Workbook, ledger_row: dict) -> None:
    """Copy a result the ledger already has into the workbook, without rerunning it."""
    def num(x):
        return None if x in (None, "") else float(x)
    known_jobs = {v[0] for v in wb.table(JOBS["sheet"], JOBS["first"], JOBS["last"], ["A"]).values()}
    outcome = Outcome(ledger_row["job_id"], "succeeded", num(ledger_row["estimate"]),
                      num(ledger_row["wall_s"]), num(ledger_row["credits"]))
    record(wb, ledger_row, outcome, jobs_row=ledger_row["job_id"] not in known_jobs)


def setup_workbook(wb: Workbook, official_id: str, qubits: list[str], force: bool) -> list[str]:
    """Fill Status!B4 (circuit ID), Status!B5 (count) and Qubits!A6.. (IDs)."""
    current_id = wb.get(*STATUS_ID)
    current = wb.qubit_ids()
    if (current_id not in (None, "") or current) and not force:
        if str(current_id) == official_id and current == qubits:
            return ["already set up"]
        raise ValueError(f"{wb.path.name}: Status/Qubits already filled (ID {current_id!r}, {len(current)} qubits); "
                         "use --force to overwrite")
    if len(qubits) > 160:
        raise ValueError("the Qubits sheet holds at most 160 qubits")
    wb.set(*STATUS_ID, official_id)
    wb.set(*STATUS_COUNT, len(qubits))
    for i in range(160):
        wb.set("Qubits", f"A{6 + i}", qubit_cell(qubits[i]) if i < len(qubits) else None)
    return [f"wrote circuit ID {official_id!r} and {len(qubits)} qubit IDs"]


def execute(jobs: list[Job], backend, ledger: Ledger, workbooks: dict[str, Workbook], cfg: dict, log=print) -> dict:
    """Submit with at most max_in_flight jobs running; record each result as it lands."""
    limits = cfg["limits"]
    pending = list(jobs)
    in_flight: dict[str, dict] = {}
    summary = {"succeeded": 0, "failed": 0, "canceled": 0, "credits": 0.0}
    deadline = time.time() + float(limits.get("job_timeout_s", 7200))

    def finish(row: dict, out: Outcome):
        ledger.append(**{**row, "status": out.status, "estimate": out.estimate, "wall_s": out.wall_s,
                         "credits": out.credits, "error": out.error, "recorded_utc": None})
        wb = workbooks.get(row["circuit"])
        if wb is not None:
            record(wb, row, out)
        summary[out.status] += 1
        summary["credits"] += float(out.credits or 0)
        value = "" if out.estimate is None else f" = {out.estimate:.6g}"
        log(f"  {out.status:9} {row['circuit']} q{row['qubit']} {row['method']} {row['setting']}{value}"
            f"{'  ' + out.error if out.error else ''}")

    try:
        # Jobs already running from an earlier command (resume) are passed as dict rows.
        for row in [j for j in pending if isinstance(j, dict)]:
            in_flight[row["job_id"]] = row
        pending = [j for j in pending if not isinstance(j, dict)]
        while pending or in_flight:
            while pending and len(in_flight) < int(limits.get("max_in_flight", 10)):
                job = pending.pop(0)
                row = {"mode": backend.mode, "circuit": job.circuit, "qubit": job.target.qubit, "method": job.method,
                       "setting": _fmt(job.setting), "transpile": "" if job.transpile is None else job.transpile,
                       "device": job.device, "job_key": job.key}
                try:
                    out = backend.submit(job.target, job.method, job.setting, job.transpile, job.name, job.tags)
                except Exception as exc:  # rejected before a job ID existed
                    if "PARALLEL_JOBS_LIMIT" in str(exc):  # platform is busy: retry later, don't fail
                        pending.insert(0, job)
                        if not in_flight:
                            log("  platform parallel-job limit reached (other jobs on this account?); waiting")
                            time.sleep(float(limits.get("poll_interval_s", 5)) * 6)
                        break
                    log(f"  rejected  {job.name}: {exc}")
                    ledger.append(**row, job_id=f"rejected-{job.key}", status="failed", error=str(exc))
                    summary["failed"] += 1
                    continue
                row["job_id"] = out.job_id
                ledger.append(**row, status="running")
                if out.status == "running":
                    in_flight[out.job_id] = row
                else:
                    finish(row, out)
            if in_flight:
                if backend.mode == "cloud":
                    time.sleep(float(limits.get("poll_interval_s", 5)))
                for out in backend.poll(list(in_flight)):
                    if out.status != "running":
                        finish(in_flight.pop(out.job_id), out)
            for wb in workbooks.values():
                wb.save()
            if in_flight and time.time() > deadline:
                log(f"Stopped waiting after job_timeout_s; {len(in_flight)} jobs still running. Use --resume later.")
                break
    except KeyboardInterrupt:
        log(f"\nInterrupted. {len(in_flight)} submitted jobs keep running on BlueQubit; "
            f"{len(pending)} were never submitted. Run with --resume to collect results.")
    finally:
        for wb in workbooks.values():
            wb.save()
    summary["still_running"] = len(in_flight)
    return summary
