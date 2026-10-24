"""Explicit fixed-cohort CPU execution with one controller and at most two slots."""

import argparse
import json
import logging
import math
from pathlib import Path

from otoc.bluequbit_adapter import BlueQubitAdapter
from otoc.calibration import load_settings
from otoc.cohort_batch import run_cohort_batch
from otoc.graded import export_complete


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="configs/workflow_final.json")
    parser.add_argument("--state-root", type=Path, default=Path("results/workflow"),
                        help="Shared account receipts, checkpoints and remote_runner lock directory")
    parser.add_argument("--problem", choices=["G2", "G3", "G4"], required=True)
    parser.add_argument("--device", choices=["mps.cpu", "pauli-path", "mps.gpu", "pauli-path.gpu"], required=True)
    parser.add_argument("--options-file", type=Path, required=True, help="JSON object with every selected native option")
    parser.add_argument("--slots", type=int, choices=[1, 2], default=2)
    parser.add_argument("--max-jobs", type=int)
    parser.add_argument("--reserve-cohorts-file", type=Path, help="Optional complete G2/G3/G4 device/options mapping")
    parser.add_argument("--targeted-diagnostics", action="store_true", help="Explicitly run selected diagnostic IDs without exporting a cohort")
    parser.add_argument("--target-ids", nargs="+", help="Diagnostic IDs from the selected problem's full retained template")
    parser.add_argument("--execution-timeout", type=float, help="Diagnostic cancellation-request cap in seconds, within 1..3600")
    parser.add_argument("--quote-runtime-limit", type=float, help="Diagnostic maximum quoted runtime in seconds, within 1..3600")
    parser.add_argument("--diagnostic-reason", help="Optional rationale recorded with every diagnostic receipt")
    parser.add_argument("--execute", action="store_true", help="Required; no network calls without this flag")
    args = parser.parse_args()
    if not args.execute:
        parser.error("Execution requires --execute; review the explicit cohort/options first")
    gpu = args.device in {"mps.gpu", "pauli-path.gpu"}
    if gpu and (not args.targeted_diagnostics or args.slots != 1):
        parser.error("GPU devices require --targeted-diagnostics and --slots 1")
    diagnostic_values = (args.target_ids, args.execution_timeout, args.quote_runtime_limit, args.diagnostic_reason)
    if not args.targeted_diagnostics and any(value is not None for value in diagnostic_values):
        parser.error("Diagnostic targets, caps and reason require --targeted-diagnostics")
    if args.targeted_diagnostics:
        if not args.target_ids or args.execution_timeout is None or args.quote_runtime_limit is None:
            parser.error("--targeted-diagnostics requires --target-ids, --execution-timeout and --quote-runtime-limit")
        if any(not math.isfinite(value) or not 1 <= value <= 3600
               for value in (args.execution_timeout, args.quote_runtime_limit)):
            parser.error("Both diagnostic runtime limits must be within 1..3600 seconds")
    settings = load_settings(args.config)  # Existing serial configuration remains unchanged.
    if gpu and settings.get("gpu_enabled") is not True:
        parser.error("GPU diagnostics require gpu_enabled in the selected configuration")
    options = json.loads(args.options_file.read_text(encoding="utf-8-sig"))
    reserves = (json.loads(args.reserve_cohorts_file.read_text(encoding="utf-8-sig"))
                if args.reserve_cohorts_file else None)
    logging.disable(logging.CRITICAL)
    result = run_cohort_batch(BlueQubitAdapter(root=args.state_root), settings, args.problem, args.device, options,
                              slots=args.slots, max_jobs=args.max_jobs, reserve_cohorts=reserves,
                              targeted_diagnostics=args.targeted_diagnostics, target_ids=args.target_ids,
                              execution_timeout_seconds=args.execution_timeout,
                              quote_runtime_limit_seconds=args.quote_runtime_limit,
                              diagnostic_reason=args.diagnostic_reason)
    print(json.dumps(result, indent=2), flush=True)
    if result["status"] == "COMPLETE" and not args.targeted_diagnostics:
        # Export reads saved receipts only. It never submits to the website.
        print(json.dumps({"complete_exports": export_complete(settings, root=args.state_root)}), flush=True)
    return 0 if result["status"] in {"COMPLETE", "DIAGNOSTICS_COMPLETE", "BOUNDED_STOP", "STOPPED"} else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(json.dumps({"status": "BLOCKED", "reason": "entrypoint_exception:" + type(exc).__name__}))
        raise SystemExit(1)
