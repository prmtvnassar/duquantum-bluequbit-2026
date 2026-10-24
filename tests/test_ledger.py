import csv
import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from tempfile import TemporaryDirectory
import threading
import time
from unittest import TestCase
from unittest.mock import patch
from otoc.ledger import locked, record_run, sync_history


class LedgerTests(TestCase):
    def test_transient_windows_sharing_violation_retries_release(self):
        with TemporaryDirectory() as folder:
            root = Path(folder)
            path = root / ".ledger.lock"
            original_unlink = Path.unlink
            attempts = []
            def transient_unlink(target, *args, **kwargs):
                if target == path:
                    attempts.append(target)
                    if len(attempts) == 1:
                        raise PermissionError("Temporary Windows sharing violation")
                return original_unlink(target, *args, **kwargs)
            with patch.object(Path, "unlink", transient_unlink):
                with locked(root):
                    self.assertTrue(path.exists())
            self.assertEqual(len(attempts), 2)
            self.assertFalse(path.exists())
            with locked(root):
                self.assertTrue(path.exists())

    def test_persistent_release_denial_keeps_pid_lock_and_raises(self):
        with TemporaryDirectory() as folder:
            root = Path(folder)
            path = root / ".ledger.lock"
            original_unlink = Path.unlink
            def denied_unlink(target, *args, **kwargs):
                if target == path:
                    raise PermissionError("Persistent Windows sharing violation")
                return original_unlink(target, *args, **kwargs)
            with patch.object(Path, "unlink", denied_unlink), patch("otoc.ledger.time.sleep"):
                with self.assertRaises(PermissionError):
                    with locked(root):
                        pass
            self.assertTrue(path.exists())

    def test_stale_reclaimers_cannot_remove_another_writer_lock(self):
        with TemporaryDirectory() as folder:
            root = Path(folder)
            (root / ".ledger.lock").write_text(json.dumps({"pid": -1}))
            active = 0
            max_active = 0
            mutex = threading.Lock()
            def write(_):
                nonlocal active, max_active
                with locked(root):
                    with mutex:
                        active += 1
                        max_active = max(active, max_active)
                    time.sleep(.02)
                    with mutex:
                        active -= 1
            # Even a stale PID observation cannot let a contender delete a lock
            # acquired while another contender is recovering the old owner.
            with patch("otoc.ledger.psutil.pid_exists", return_value=False):
                with ThreadPoolExecutor(max_workers=4) as pool:
                    list(pool.map(write, range(8)))
            self.assertEqual(max_active, 1)
            self.assertFalse((root / ".ledger.lock").exists())

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
