"""Reconcile every saved local/cloud execution into the tracked runs ledger."""
import json
from otoc.ledger import sync_history
from otoc.submission_registry import sync_submissions

if __name__ == "__main__":
    print(json.dumps(sync_history(), indent=2))
    print(json.dumps({"official_submissions": sync_submissions()}, indent=2))
