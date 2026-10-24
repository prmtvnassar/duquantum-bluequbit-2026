"""Initialize and safely update the machine-readable run records.

Examples:
    python scripts/run_csv.py init --dataset hidden --template kit/submission_template.csv
    python scripts/run_csv.py job --json-file scratch/job.json
    python scripts/run_csv.py estimate --json-file scratch/estimate.json
    python scripts/run_csv.py select --json-file scratch/selection.json
    python scripts/run_csv.py validate
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from otoc.run_csv import RunCsvError, prepare_run_csv, record_estimate, select_estimate, upsert_job, validate_run_csv


ROOT = Path(__file__).resolve().parents[1]


def _object(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as source:
        value = json.load(source)
    if not isinstance(value, dict):
        raise RunCsvError(f"{path}: expected one JSON object")
    return value


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runs-dir", type=Path, default=ROOT / "runs" / "csv")
    commands = parser.add_subparsers(dest="command", required=True)
    initialize = commands.add_parser("init", help="Import official target IDs and prepare blank selections")
    initialize.add_argument("--dataset", choices=("sample", "hidden"), required=True)
    initialize.add_argument("--template", type=Path, required=True)
    for name in ("job", "estimate", "select"):
        command = commands.add_parser(name, help=f"Record one {name} from a JSON object")
        command.add_argument("--json-file", type=Path, required=True)
    commands.add_parser("validate", help="Validate job and estimate records")
    args = parser.parse_args()
    try:
        if args.command == "init":
            paths = prepare_run_csv(args.template, args.dataset, args.runs_dir)
            for kind, path in paths.items():
                print(f"{kind}: {path}")
        elif args.command == "job":
            print(f"run_key: {upsert_job(args.runs_dir, _object(args.json_file))}")
        elif args.command == "estimate":
            record_estimate(args.runs_dir, _object(args.json_file))
            print("Estimate recorded")
        elif args.command == "select":
            select_estimate(args.runs_dir, _object(args.json_file))
            print("Selected estimate updated")
        else:
            jobs, estimates = validate_run_csv(args.runs_dir)
            print(f"Valid: {jobs} jobs, {estimates} estimates")
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        parser.exit(2, f"Run CSV error: {exc}\n")


if __name__ == "__main__":
    main()
