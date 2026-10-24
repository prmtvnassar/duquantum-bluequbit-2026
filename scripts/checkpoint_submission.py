"""Validate a selected estimate CSV and save a complete atomic checkpoint.

Example:
    python scripts/checkpoint_submission.py --template kit/submission_template.csv \
        --estimates runs/csv/selected_hidden.csv --kind baseline
"""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path

from otoc.submission import SubmissionError, checkpoint_from_files, read_estimates, read_template, validate_against_template


ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--template", type=Path, required=True)
    parser.add_argument("--estimates", type=Path, required=True)
    parser.add_argument("--kind", choices=("baseline", "latest"), default="baseline")
    parser.add_argument("--output", type=Path, help="Default: data/checkpoints/<kind>.csv")
    parser.add_argument("--check-only", action="store_true", help="Validate without writing a checkpoint")
    args = parser.parse_args()
    destination = args.output or ROOT / "data" / "checkpoints" / f"{args.kind}.csv"
    try:
        if args.check_only:
            template = read_template(args.template)
            estimates = read_estimates(args.estimates)
            validate_against_template(template, estimates)
            print(f"Valid: {len(template)} rows match the template")
            return
        created = checkpoint_from_files(
            args.template, args.estimates, destination, immutable=args.kind == "baseline"
        )
    except (OSError, SubmissionError) as exc:
        parser.exit(2, f"Cannot checkpoint: {exc}\n")
    digest = hashlib.sha256(destination.read_bytes()).hexdigest()
    outcome = "Wrote" if created else "Kept identical"
    print(f"{outcome} {destination} (sha256 {digest})")


if __name__ == "__main__":
    main()
