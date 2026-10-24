"""Record a verified website submission, including its mandatory explanation."""
import argparse
from pathlib import Path
from otoc.submission_registry import record_submission

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--problem", required=True)
    parser.add_argument("--attempt", required=True, type=int)
    parser.add_argument("--csv", required=True)
    parser.add_argument("--note-file", required=True)
    parser.add_argument("--score", required=True, type=float)
    args = parser.parse_args()
    result = record_submission(args.problem, args.attempt, args.csv,
                               Path(args.note_file).read_text(), args.score)
    print(f"Recorded {result['problem']} attempt {result['attempt']}: {result['displayed_score']}")
