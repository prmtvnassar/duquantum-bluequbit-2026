"""Run MPS or Pauli-path (PPS) jobs and record them in the run workbooks.

Examples:
    # Free test run: offline exact simulation, writes to scratch/offline/ copies only
    python scripts/run_jobs.py sample_1 --setup --offline
    python scripts/run_jobs.py sample_1 --method mps --slots 1 2 3 --offline

    # Real jobs (spends credits). --dry-run shows the plan without submitting anything.
    python scripts/run_jobs.py sample_1 --method pps --slots 1 --dry-run
    python scripts/run_jobs.py sample_1 sample_2 --method mps --slots 1
    python scripts/run_jobs.py hidden_2 --method mps --settings 512 --qubits 0 1 2

    # Collect jobs still running after an interrupt or timeout
    python scripts/run_jobs.py --resume

Settings: --slots reads χ / ε from each workbook's Status sheet (E5:G5, E6:G6) so the
values match its formulas; --settings takes explicit values. Circuits, devices and
limits come from scripts/runner.toml; how circuits are built is in scripts/runner/targets.py.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from runner.backends import CloudBackend, OfflineBackend, job_options  # noqa: E402
from runner.config import circuit_config, get_client, load_config  # noqa: E402
from runner.core import (Job, accepted_keys, backfill, execute, job_key, ledger_for,  # noqa: E402
                         resolve_settings, setup_workbook, workbook_path, _estimate_key)
from runner.targets import Context, build_targets  # noqa: E402
from runner.workbook import Workbook  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("circuits", nargs="*", help="circuit names from scripts/runner.toml")
    ap.add_argument("--method", choices=("mps", "pps"))
    ap.add_argument("--slots", type=int, nargs="+", choices=(1, 2, 3), default=[], help="Status precision slots")
    ap.add_argument("--settings", type=float, nargs="+", default=[], help="explicit χ or ε values")
    ap.add_argument("--transpile", type=int, help="PPS transpilation level (default: Status!E7)")
    ap.add_argument("--qubits", nargs="+", help="only these qubit IDs")
    ap.add_argument("--offline", action="store_true", help="free local fake backend; writes to scratch/offline/")
    ap.add_argument("--dry-run", action="store_true", help="print the plan, submit nothing")
    ap.add_argument("--yes", action="store_true", help="skip the confirmation prompt")
    ap.add_argument("--force", action="store_true", help="rerun cached jobs / overwrite --setup")
    ap.add_argument("--max-jobs", type=int, help="override limits.max_jobs_per_command")
    ap.add_argument("--no-workbook", action="store_true", help="ledger only, leave workbooks untouched")
    ap.add_argument("--setup", action="store_true", help="write circuit ID and qubit IDs into the workbook")
    ap.add_argument("--resume", action="store_true", help="collect jobs left running by an earlier command")
    args = ap.parse_args()

    cfg = load_config()
    ledger = ledger_for(args.offline)
    client = None

    def client_factory():
        nonlocal client
        if args.offline:
            raise RuntimeError("this circuit needs BlueQubit (stored IDs); it can't run with --offline")
        if client is None:
            client = get_client()
        return client

    def workbook(name: str) -> Workbook:
        return Workbook(workbook_path(cfg, name, args.offline))

    ctx = Context(cfg, client_factory, lambda name: workbook(name).qubit_ids())

    if args.resume:
        rows = ledger.unfinished("offline" if args.offline else "cloud")
        if not rows:
            print("No unfinished jobs in", ledger.path)
            return 0
        print(f"Resuming {len(rows)} jobs")
        backend = OfflineBackend(cfg) if args.offline else CloudBackend(cfg, client_factory())
        books = {} if args.no_workbook else {n: workbook(n) for n in {r["circuit"] for r in rows}}
        return report(execute(rows, backend, ledger, books, cfg))

    if not args.circuits:
        ap.error("name at least one circuit (or use --resume)")

    if args.setup:
        for name in args.circuits:
            c = circuit_config(cfg, name)
            qubits = [t.qubit for t in build_targets(name, c, ctx)] if c.get("qubits") != "workbook" else None
            if qubits is None:
                print(f"{name}: qubits come from the workbook; fill Qubits!A6.. by hand")
                continue
            wb = workbook(name)
            for msg in setup_workbook(wb, str(c.get("official_id", name)), qubits, args.force):
                print(f"{name}: {msg} ({wb.path.relative_to(Path.cwd()) if wb.path.is_relative_to(Path.cwd()) else wb.path})")
            wb.save()
        if not args.method:
            return 0

    if not args.method or not (args.slots or args.settings):
        ap.error("give --method and --slots or --settings")

    # ---------------------------------------------------------------- plan
    mode = "offline" if args.offline else "cloud"
    cached = {} if args.force else ledger.succeeded(mode)
    jobs, skipped, warnings, backfilled = [], [], [], 0
    for name in args.circuits:
        wb = workbook(name)
        settings, warn = resolve_settings(wb, args.method, args.slots, args.settings)
        warnings += warn
        transpile = None
        if args.method == "pps":
            transpile = args.transpile if args.transpile is not None else wb.transpile()
            transpile = None if transpile is None else int(transpile)
        in_workbook = set() if args.force else accepted_keys(wb)
        targets = build_targets(name, circuit_config(cfg, name), ctx)
        if args.qubits:
            unknown = set(args.qubits) - {t.qubit for t in targets}
            if unknown:
                ap.error(f"{name}: unknown qubit IDs {sorted(unknown)}")
            targets = [t for t in targets if t.qubit in set(args.qubits)]
        for setting in settings:
            for t in targets:
                key = job_key(cfg, t, args.method, setting, transpile)
                ekey = _estimate_key(t.qubit, args.method, *((setting, None) if args.method == "mps" else (None, setting)),
                                     float(transpile) if transpile is not None else None)
                if ekey in in_workbook:
                    skipped.append(key)
                    continue
                if key in cached:  # ledger has it but the workbook doesn't: copy it over, free
                    if not args.no_workbook and not args.dry_run:
                        backfill(wb, cached[key])
                        backfilled += 1
                    skipped.append(key)
                    continue
                device, _ = job_options(cfg, args.method, setting, transpile)
                jobs.append(Job(name, t, args.method, setting, transpile, device, key))
        wb.save()

    for w in warnings:
        print("WARNING:", w)
    print(f"Plan ({mode}): {len(jobs)} jobs to run, {len(skipped)} already done"
          + (f" ({backfilled} copied from the ledger into the workbook)" if backfilled else ""))
    by = {}
    for j in jobs:
        by.setdefault((j.circuit, j.device, j.setting, j.transpile), []).append(j.target.qubit)
    for (circuit, device, setting, transpile), qs in by.items():
        _, options = job_options(cfg, args.method, setting, transpile)
        print(f"  {circuit:10} {device:11} {options}  {len(qs)} qubits ({', '.join(qs[:8])}{'…' if len(qs) > 8 else ''})")
    if not jobs:
        return 0
    limit = args.max_jobs or int(cfg["limits"].get("max_jobs_per_command", 40))
    if len(jobs) > limit:
        print(f"Refusing: {len(jobs)} jobs exceeds the limit of {limit}. Use --max-jobs or narrow --qubits.")
        return 2
    if args.dry_run:
        print("Dry run: nothing submitted.")
        return 0
    if mode == "cloud" and not args.yes:
        if input(f"Submit {len(jobs)} BlueQubit jobs (spends credits)? [y/N] ").strip().lower() != "y":
            print("Cancelled.")
            return 1

    backend = OfflineBackend(cfg) if args.offline else CloudBackend(cfg, client_factory())
    books = {} if args.no_workbook else {n: workbook(n) for n in args.circuits}
    return report(execute(jobs, backend, ledger, books, cfg))


def report(summary: dict) -> int:
    print(f"Done: {summary['succeeded']} succeeded, {summary['failed']} failed, {summary['canceled']} canceled, "
          f"{summary['still_running']} still running; credits {summary['credits']:.4g}")
    return 0 if summary["failed"] == 0 else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (ValueError, RuntimeError, NotImplementedError, FileNotFoundError) as exc:
        sys.exit(f"Error: {exc}")
