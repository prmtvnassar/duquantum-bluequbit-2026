import csv
import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from otoc.ledger import record_run, sync_history


class LedgerTests(TestCase):
    def test_distinct_attempts_and_concurrent_writers_are_preserved(self):
        with TemporaryDirectory() as folder:
            root=Path(folder)
            def run(number):
                fields={"circuit_id":"Duke_S1_0","method":"mps","origin":"local","parameters":{"chi":4},
                        "status":"RUNNING","started_at":"2026-10-24T00:00:00+00:00"}
                record_run(f"attempt-{number}",fields,root)
                record_run(f"attempt-{number}",{**fields,"status":"SUCCEEDED","estimate":.5},root)
            with ThreadPoolExecutor(max_workers=2) as pool:
                list(pool.map(run,range(6)))
            with (root/"jobs.csv").open(newline="") as stream:
                rows=list(csv.DictReader(stream))
            self.assertEqual(len(rows),6)
            self.assertTrue(all(r["status"]=="SUCCEEDED" for r in rows))
            self.assertEqual(len(list((root/"events").glob("*.json"))),12)
            with self.assertRaises(ValueError):
                record_run("attempt-0",{"parameters":{"chi":8}},root)

    def test_recovery_does_not_invent_a_success_after_interruption(self):
        with TemporaryDirectory() as folder:
            repo=Path(folder)
            request=repo/"results/local/attempts/aabbcc-incomplete/request.json"
            request.parent.mkdir(parents=True)
            request.write_text(json.dumps({"sample":{"circuit_id":"Duke_S1_0","sample":"S1","qubit":0,
                                                     "qasm_sha256":"abc"},"method":"mps","parameters":{"chi":4}}))
            counts=sync_history(repo,repo/"runs")
            receipt=json.loads(next((repo/"runs/records").glob("*.json")).read_text())
            self.assertEqual(counts["unfinished"],1)
            self.assertEqual(receipt["status"],"INTERRUPTED_UNRESOLVED")
            self.assertNotIn("estimate",receipt)
