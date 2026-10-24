"""Record browser-observed or user-reported submission evidence and explanation."""
import argparse
from pathlib import Path
from otoc.submission_registry import DEFAULT_OWNER, EVIDENCE_SOURCES, NOTE_EVIDENCE, record_submission

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--problem", required=True)
    parser.add_argument("--attempt", required=True, type=int)
    parser.add_argument("--csv", required=True)
    parser.add_argument("--note-file", required=True)
    parser.add_argument("--score", required=True, type=float)
    parser.add_argument("--time-penalty-hours", type=float,
                        help="Reported/displayed time penalty in hours; omitted means unknown")
    parser.add_argument("--evidence-source", choices=EVIDENCE_SOURCES, default="browser_observed",
                        help="Use user_report when the upload and score were reported without browser verification")
    parser.add_argument("--owner", default=DEFAULT_OWNER,
                        help="Submitter slug; use a separate owner for a teammate's attempt")
    parser.add_argument("--note-evidence", choices=NOTE_EVIDENCE, default="submitted_text",
                        help="Use prepared_explanation when the exact website explanation was not confirmed")
    args = parser.parse_args()
    result = record_submission(args.problem, args.attempt, args.csv,
                               Path(args.note_file).read_text(encoding="utf-8-sig"), args.score,
                               evidence_source=args.evidence_source, owner=args.owner,
                               note_evidence=args.note_evidence, time_penalty_hours=args.time_penalty_hours)
    print(f"Recorded {result.get('owner', DEFAULT_OWNER)} {result['problem']} attempt {result['attempt']}: "
          f"{result['displayed_score']} ({result.get('status', 'VERIFIED_BROWSER')})")
