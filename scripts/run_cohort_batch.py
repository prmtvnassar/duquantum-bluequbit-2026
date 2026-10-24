"""Explicit fixed-cohort CPU execution with one controller and at most two slots."""

import argparse
import json
import logging
from pathlib import Path

from otoc.bluequbit_adapter import BlueQubitAdapter
from otoc.calibration import load_settings
from otoc.cohort_batch import run_cohort_batch
from otoc.graded import export_complete


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="configs/workflow_final.json")
    parser.add_argument("--problem", choices=["G2", "G3", "G4"], required=True)
    parser.add_argument("--device", choices=["mps.cpu", "pauli-path"], required=True)
    parser.add_argument("--options-file", type=Path, required=True, help="JSON object with every selected native option")
    parser.add_argument("--slots", type=int, choices=[1, 2], default=2)
    parser.add_argument("--max-jobs", type=int)
    parser.add_argument("--reserve-cohorts-file", type=Path, help="Optional complete G2/G3/G4 device/options mapping")
    parser.add_argument("--execute", action="store_true", help="Required; no network calls without this flag")
    args = parser.parse_args()
    if not args.execute:
        parser.error("Execution requires --execute; review the explicit cohort/options first")
    settings = load_settings(args.config)  # Existing serial configuration remains unchanged.
    options = json.loads(args.options_file.read_text(encoding="utf-8-sig"))
    reserves = (json.loads(args.reserve_cohorts_file.read_text(encoding="utf-8-sig"))
                if args.reserve_cohorts_file else None)
    logging.disable(logging.CRITICAL)
    result = run_cohort_batch(BlueQubitAdapter(), settings, args.problem, args.device, options,
                              slots=args.slots, max_jobs=args.max_jobs, reserve_cohorts=reserves)
    print(json.dumps(result, indent=2), flush=True)
    if result["status"] == "COMPLETE":
        # Export reads saved receipts only. It never submits to the website.
        print(json.dumps({"complete_exports": export_complete(settings)}), flush=True)
    return 0 if result["status"] in {"COMPLETE", "BOUNDED_STOP", "STOPPED"} else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(json.dumps({"status": "BLOCKED", "reason": "entrypoint_exception:" + type(exc).__name__}))
        raise SystemExit(1)
