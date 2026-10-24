"""Export one released Duke problem as a validated circuit_id,value CSV.

Example:
    python scripts/export_problem_submission.py --problem S1 --baseline
"""

from __future__ import annotations

import argparse
from pathlib import Path

from otoc.duke_submission import DukeSubmissionError, build_submission, write_submission


ROOT = Path(__file__).resolve().parents[1]
PROBLEM_DIRS = {
    "S1": "01_sample_S1", "S2": "02_sample_S2", "S3": "03_sample_S3",
    "G1": "04_graded_G1", "G2": "05_graded_G2", "G3": "06_graded_G3", "G4": "07_graded_G4",
}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--problem", choices=tuple(PROBLEM_DIRS), required=True)
    parser.add_argument("--values", type=Path, help="Default: problems/<problem>/selected.csv")
    parser.add_argument("--output", type=Path, help="Default: submissions/<problem>.csv")
    parser.add_argument("--baseline", action="store_true", help="Also save an immutable baseline checkpoint")
    parser.add_argument("--check-only", action="store_true", help="Validate without writing files")
    args = parser.parse_args()
    folder = ROOT / "problems" / PROBLEM_DIRS[args.problem]
    values = args.values or folder / "selected.csv"
    output = args.output or ROOT / "submissions" / f"{args.problem}.csv"
    try:
        payload = build_submission(folder / "local_submission_template.csv", values)
        if args.check_only:
            print(f"Valid {args.problem}: {len(payload.splitlines()) - 1} IDs")
            return
        if args.baseline:
            baseline = ROOT / "data" / "checkpoints" / f"{args.problem}_baseline.csv"
            write_submission(payload, baseline, immutable=True)
            print(f"Protected baseline: {baseline}")
        _, digest = write_submission(payload, output)
    except (OSError, DukeSubmissionError) as exc:
        parser.exit(2, f"Cannot export {args.problem}: {exc}\n")
    print(f"Wrote {output} (sha256 {digest})")


if __name__ == "__main__":
    main()
