"""Rebuild the local submission-claim CSV from saved repository receipts only."""

from otoc.submission_registry import rebuild_submission_index


if __name__ == "__main__":
    count = rebuild_submission_index()
    print(f"Indexed {count} saved submission claims in runs/submissions.csv")
