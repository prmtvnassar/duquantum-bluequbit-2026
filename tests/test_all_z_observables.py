"""Offline tests for observable-list (all_z) MPS jobs through the audited adapter.

A fake SDK client answers every request locally; the real ledger writes into a
temporary root.  No network, no repository ``runs/`` or ``results/`` mutation.
"""

from contextlib import redirect_stderr, redirect_stdout
import csv
import importlib.util
import io
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch
import zlib

from bluequbit.tools import format_pauli_sum
from otoc.bluequbit_adapter import BlueQubitAdapter, SIZES, observable_pauli_sums, validate_action
from otoc.coherent_selection import select_coherent_vector
from otoc.cohort_batch import _complete
from otoc.experiment_store import digest
from otoc.graded import valid
from otoc.ledger import FIELDS, event, record_remote


OPTIONS = {"mps_bond_dimension": 16}


def settings():
    return {"version": "test", "deadline_utc": "2099-01-01T00:00:00+00:00", "submission_buffer_seconds": 1200,
            "graded_budget_usd": 30., "graded_reserve_fraction": .1, "max_remote_jobs": 800,
            "per_job_seconds": 900, "protected_baseline_usd": 0}


def component(pauli):
    """Qubit index encoded by a single-Z Pauli string (q0 rightmost)."""
    return len(pauli) - 1 - pauli.index("Z")


class FakeConnection:
    """Answers GET /jobs (usage) and estimate-only POST /jobs (quote) offline."""

    def __init__(self):
        self.posts = []

    def send_request(self, req_type, path, params=None, data=None, headers=None, **kwargs):
        if req_type == "GET" and path == "/jobs":
            return SimpleNamespace(json=lambda: {"data": [], "total_count": 0})
        assert req_type == "POST" and path == "/jobs"
        body = zlib.decompress(data) if (headers or {}).get("content-encoding") == "gzip" else data
        payload = json.loads(body)
        assert payload["estimate_only"], "The adapter quotes only through estimate_only"
        self.posts.append(payload)
        return SimpleNamespace(json=lambda: {"data": {"estimated_cost": 20, "estimate_ms": 30000}})


class FakeClient:
    def __init__(self, *, terminal="COMPLETED", malformed=False):
        self._backend_connection = FakeConnection()
        self.run_calls, self.cancel_calls, self.jobs = [], [], {}
        self.terminal, self.malformed = terminal, malformed

    def run(self, cid, *, device, asynchronous, pauli_sum, options, tags, force_run):
        assert asynchronous and not force_run
        self.run_calls.append({"circuit_id": cid, "device": device, "pauli_sum": pauli_sum,
                               "options": options, "tags": tags})
        job = SimpleNamespace(job_id=f"job-{len(self.jobs)}", run_status="RUNNING", expectation_value=None,
                              cost=None, run_time_ms=None, queue_time_ms=None, estimated_cost=0, pauli_sum=pauli_sum)
        self.jobs[job.job_id] = job
        return job

    def get(self, jid):
        job = self.jobs[jid]
        job.run_status, job.cost, job.run_time_ms, job.queue_time_ms = self.terminal, 0.0, 1000, 10
        if self.terminal == "COMPLETED":
            if isinstance(job.pauli_sum[0], list):  # list of sums: one value per sum, request order
                job.expectation_value = [(component(s[0][0]) + 1) / 100 for s in job.pauli_sum]
                if self.malformed:
                    job.expectation_value = job.expectation_value[:-1]
            else:
                job.expectation_value = (component(job.pauli_sum[0][0]) + 1) / 100
        return job

    def cancel(self, jid):
        self.cancel_calls.append(jid)


class Harness:
    """Adapter on a temporary workflow root with the real ledger in a temporary runs root."""

    def __init__(self, folder, **client_kwargs):
        self.root = Path(folder) / "workflow"
        self.ledger = Path(folder) / "runs"
        self.client = FakeClient(**client_kwargs)
        self.adapter = BlueQubitAdapter(self.root, self.client)
        self.patches = [patch("otoc.bluequbit_adapter.time.sleep"),
                        patch("otoc.bluequbit_adapter.event", side_effect=lambda kind, payload: event(kind, payload, root=self.ledger)),
                        patch("otoc.bluequbit_adapter.record_remote", side_effect=lambda saved: record_remote(saved, root=self.ledger))]

    def __enter__(self):
        for item in self.patches:
            item.start()
        return self

    def __exit__(self, *exc):
        for item in self.patches:
            item.stop()

    def run(self, cid, observables=None, device="mps.cpu", options=OPTIONS):
        return self.adapter.run(cid, device, options, settings(), "feature vector test", observables=observables)

    def receipt(self, action):
        return json.loads((self.root / "remote_actions" / f"{digest(action)}.json").read_text())

    def ledger_record(self, action):
        return json.loads((self.ledger / "records" / f"remote-{digest(action)}.json").read_text())


class PauliSumConstructionTests(TestCase):
    def test_all_z_list_has_one_single_site_z_per_qubit_with_q0_rightmost(self):
        problem, z, sums = observable_pauli_sums("Duke_G4_5", "mps.cpu", OPTIONS, "all_z")
        self.assertEqual((problem, len(sums)), ("G4", 38))
        self.assertEqual(sums[0], [("I" * 37 + "Z", 1.0)])
        self.assertEqual(sums[37], [("Z" + "I" * 37, 1.0)])
        self.assertEqual(sums[5], [(z, 1.0)])
        for j, pauli_sum in enumerate(sums):
            self.assertEqual(pauli_sum, [("I" * (38 - 1 - j) + "Z" + "I" * j, 1.0)])
            self.assertEqual(component(pauli_sum[0][0]), j)
        # The installed SDK keeps a list of sums as a list of sums (shape preserved).
        self.assertEqual(format_pauli_sum(sums), sums)
        self.assertEqual(format_pauli_sum([(z, 1.0)]), [(z, 1.0)])

    def test_single_observable_path_is_unchanged(self):
        problem, z, sums = observable_pauli_sums("Duke_G4_5", "mps.cpu", OPTIONS)
        self.assertEqual(sums, [(validate_action("Duke_G4_5", "mps.cpu", OPTIONS)[1], 1.0)])
        self.assertEqual((problem, z), ("G4", z))

    def test_all_z_is_rejected_outside_mps_before_any_api_call(self):
        pps = {"pauli_path_truncation_threshold": .001, "pauli_path_circuit_transpilation_level": 1}
        with TemporaryDirectory() as folder, Harness(folder) as h:
            for device, options in (("pauli-path", pps), ("pauli-path.gpu", pps), ("cpu", {}), ("gpu", {})):
                with self.subTest(device=device):
                    with self.assertRaisesRegex(ValueError, "mps.cpu/mps.gpu only"):
                        h.adapter.run("Duke_G4_0", device, options, settings(), "x", observables="all_z")
                    with self.assertRaisesRegex(ValueError, "mps.cpu/mps.gpu only"):
                        h.adapter.quote("Duke_G4_0", device, options, observables="all_z")
            with self.assertRaisesRegex(ValueError, "Unknown observable set"):
                h.run("Duke_G4_0", observables="all_x")
            self.assertEqual(h.client.run_calls, [])
            self.assertEqual(h.client._backend_connection.posts, [])
            self.assertFalse((h.root / "remote_actions").exists())


class AdapterReceiptTests(TestCase):
    def test_single_and_all_z_actions_have_distinct_keys_and_receipts(self):
        with TemporaryDirectory() as folder, Harness(folder) as h:
            single = h.run("Duke_G4_5")
            vector = h.run("Duke_G4_5", observables="all_z")
            self.assertEqual(single["action"], {"circuit_id": "Duke_G4_5", "device": "mps.cpu", "options": OPTIONS,
                                                "pauli": validate_action("Duke_G4_5", "mps.cpu", OPTIONS)[1]})
            self.assertEqual(vector["action"], {**single["action"], "observables": "all_z"})
            self.assertNotEqual(digest(single["action"]), digest(vector["action"]))
            self.assertEqual(len(list((h.root / "remote_actions").glob("*.json"))), 2)
            self.assertNotIn("estimates_vector", single)
            self.assertNotIn("observables", single["action"])
            self.assertEqual(single["estimate"], .06)
            self.assertEqual(len(h.client.run_calls), 2)
            self.assertEqual(h.client.run_calls[0]["pauli_sum"], [(single["action"]["pauli"], 1.0)])
            self.assertEqual(h.client.run_calls[1]["pauli_sum"], observable_pauli_sums("Duke_G4_5", "mps.cpu", OPTIONS, "all_z")[2])
            self.assertEqual(h.client.run_calls[1]["tags"]["action_key"], digest(vector["action"]))
            # Separate ledger rows and quote files; the all_z quote carries its marker.
            self.assertEqual(len(list((h.ledger / "records").glob("remote-*.json"))), 2)
            quotes = [json.loads(p.read_text()) for p in (h.root / "quotes").glob("*.json")]
            self.assertEqual(sorted((q.get("observables") for q in quotes), key=str), [None, "all_z"])
            self.assertEqual([q["observable_count"] for q in quotes if q.get("observables")], [38])

    def test_quote_sends_the_same_observable_list_as_the_run(self):
        with TemporaryDirectory() as folder, Harness(folder) as h:
            h.run("Duke_G4_3", observables="all_z")
            posts = h.client._backend_connection.posts
            self.assertEqual(len(posts), 1)
            wire = posts[0]["circuit"]["pauli_sum"]
            self.assertEqual(posts[0]["circuit"]["circuit_id"], "Duke_G4_3")
            self.assertEqual(posts[0]["circuit"]["options"], OPTIONS)
            self.assertEqual(len(wire), 38)
            self.assertEqual(wire[0], [["I" * 37 + "Z", 1.0]])
            self.assertEqual(wire[3], [[validate_action("Duke_G4_3", "mps.cpu", OPTIONS)[1], 1.0]])
            self.assertEqual([tuple(map(tuple, s)) for s in wire],
                             [tuple(s) for s in h.client.run_calls[0]["pauli_sum"]])

    def test_receipt_vector_and_ledger_scalar_are_the_target_component(self):
        with TemporaryDirectory() as folder, Harness(folder) as h:
            saved = h.run("Duke_G4_19", observables="all_z")
            self.assertEqual(saved["status"], "COMPLETED")
            self.assertEqual(len(saved["estimates_vector"]), 38)
            self.assertEqual(saved["estimates_vector"], [(j + 1) / 100 for j in range(38)])
            self.assertEqual(saved["estimate"], saved["estimates_vector"][19])
            self.assertEqual(saved["observables_count"], 38)
            self.assertEqual(saved["cost_usd"], 0.0)
            record = h.ledger_record(saved["action"])
            self.assertEqual(record["estimate"], .2)
            self.assertEqual(record["qubit"], 19)
            self.assertEqual(record["estimates_vector"], saved["estimates_vector"])
            self.assertEqual(record["observables"], "all_z")
            self.assertIn("all_z", record["reason"])
            self.assertEqual(record["remote_receipt"]["action"]["observables"], "all_z")
            for name in ("jobs.csv", "estimates.csv"):
                with (h.ledger / name).open(newline="", encoding="utf-8") as stream:
                    rows = list(csv.DictReader(stream))
                self.assertEqual(tuple(rows[0].keys()), FIELDS)
                self.assertEqual(len(rows), 1)
                self.assertEqual(float(rows[0]["estimate"]), .2)
                self.assertIn("all_z", rows[0]["reason"])
            # Existing consumers read the scalar and never see the vector key.
            self.assertTrue(valid(saved))
            self.assertTrue(_complete(saved))
            chosen = select_coherent_vector([saved], ["Duke_G4_19"], "mps.cpu")
            self.assertEqual(chosen["status"], "COMPLETE")
            self.assertEqual(chosen["selected"]["values"], [.2])

    def test_malformed_vector_is_an_invalid_result_with_raw_value_kept(self):
        with TemporaryDirectory() as folder, Harness(folder, malformed=True) as h:
            saved = h.run("Duke_G4_0", observables="all_z")
            self.assertEqual(saved["status"], "INVALID_RESULT")
            self.assertIsNone(saved["estimate"])
            self.assertEqual(len(saved["estimates_vector"]), 37)
            self.assertIn("not a list of 38", saved["error"])
            self.assertFalse(valid(saved))
            record = h.ledger_record(saved["action"])
            self.assertEqual(record["status"], "INVALID_RESULT")
            with (h.ledger / "estimates.csv").open(newline="", encoding="utf-8") as stream:
                self.assertEqual(list(csv.DictReader(stream)), [])

    def test_completed_all_z_receipt_is_reused_without_a_new_submission(self):
        with TemporaryDirectory() as folder, Harness(folder) as h:
            first = h.run("Duke_G4_0", observables="all_z")
            second = h.run("Duke_G4_0", observables="all_z")
            self.assertEqual(first["estimates_vector"], second["estimates_vector"])
            self.assertEqual(len(h.client.run_calls), 1)


class FeatureRunnerTests(TestCase):
    @staticmethod
    def command():
        path = Path(__file__).resolve().parents[1] / "scripts" / "run_feature_jobs.py"
        spec = importlib.util.spec_from_file_location("feature_jobs_command_test", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def runner(self, h, ids, **kwargs):
        log = h.root.parent / "feature.log"
        code, entries = self.command().run_feature_jobs(h.adapter, settings(), "G4", "mps.cpu", OPTIONS, ids,
                                                        "all_z", "feature vector test", log)
        lines = [json.loads(line) for line in log.read_text(encoding="utf-8").splitlines()] if log.exists() else []
        return code, entries, lines

    def test_skips_completed_ids_and_resumes_remaining_in_order(self):
        with TemporaryDirectory() as folder, Harness(folder) as h:
            h.run("Duke_G4_1", observables="all_z")
            h.run("Duke_G4_2")  # single-observable receipt does not satisfy the all_z action
            self.assertEqual(len(h.client.run_calls), 2)
            code, entries, lines = self.runner(h, ["Duke_G4_1", "2", "Duke_G4_0"])
            self.assertEqual(code, 0)
            self.assertEqual([e["status"] for e in entries], ["SKIPPED_COMPLETED", "COMPLETED", "COMPLETED"])
            self.assertEqual([e["circuit_id"] for e in entries], ["Duke_G4_1", "Duke_G4_2", "Duke_G4_0"])
            self.assertEqual(entries, lines)
            self.assertEqual([c["circuit_id"] for c in h.client.run_calls[2:]], ["Duke_G4_2", "Duke_G4_0"])
            self.assertTrue(all(isinstance(c["pauli_sum"][0], list) and len(c["pauli_sum"]) == 38 for c in h.client.run_calls[2:]))
            self.assertEqual([e["vector_length"] for e in entries], [38, 38, 38])
            self.assertEqual(entries[2]["estimate"], .01)
            self.assertFalse((h.root / "remote_runner.lock").exists())
            # Second invocation: everything is skipped, no new submissions.
            code, entries, _ = self.runner(h, ["0", "1", "2"])
            self.assertEqual((code, [e["status"] for e in entries]), (0, ["SKIPPED_COMPLETED"] * 3))
            self.assertEqual(len(h.client.run_calls), 4)

    def test_stop_file_blocks_the_next_launch_after_skips(self):
        with TemporaryDirectory() as folder, Harness(folder) as h:
            h.run("Duke_G4_1", observables="all_z")
            (h.root / "STOP").write_text("hold", encoding="utf-8")
            code, entries, _ = self.runner(h, ["1", "0", "2"])
            self.assertEqual(code, 1)
            self.assertEqual([e["status"] for e in entries], ["SKIPPED_COMPLETED", "BLOCKED_STOP"])
            self.assertEqual(len(h.client.run_calls), 1)

    def test_first_canceled_or_unknown_cost_outcome_exits_nonzero(self):
        with TemporaryDirectory() as folder, Harness(folder, terminal="CANCELED") as h:
            code, entries, _ = self.runner(h, ["0", "1"])
            self.assertEqual(code, 1)
            self.assertEqual([e["status"] for e in entries], ["CANCELED"])
            self.assertEqual(len(h.client.run_calls), 1)
        with TemporaryDirectory() as folder, Harness(folder, malformed=True) as h:
            code, entries, _ = self.runner(h, ["0", "1"])
            self.assertEqual((code, [e["status"] for e in entries]), (1, ["INVALID_RESULT"]))

    def test_runner_rejects_foreign_or_duplicate_ids_before_locking(self):
        with TemporaryDirectory() as folder, Harness(folder) as h:
            for ids in (["Duke_G2_0"], ["0", "Duke_G4_0"], ["38"], []):
                with self.subTest(ids=ids), self.assertRaises(ValueError):
                    self.runner(h, ids)
            self.assertEqual(h.client.run_calls, [])
            self.assertFalse((h.root.parent / "feature.log").exists())

    def test_runner_refuses_when_remote_runner_lock_is_held(self):
        with TemporaryDirectory() as folder, Harness(folder) as h:
            with patch("otoc.experiment_store.psutil.pid_exists", return_value=True):
                (h.root / "remote_runner.lock").write_text(json.dumps({"pid": 1}))
                with self.assertRaisesRegex(RuntimeError, "Another workflow runner is active"):
                    self.runner(h, ["0"])
            self.assertEqual(h.client.run_calls, [])

    def test_cli_requires_execute_and_builds_no_adapter(self):
        command = self.command()
        with TemporaryDirectory() as folder:
            options = Path(folder) / "options.json"
            options.write_text(json.dumps(OPTIONS))
            base = ["run_feature_jobs.py", "--problem", "G4", "--device", "mps.cpu", "--options-file", str(options),
                    "--observables", "all_z", "--ids", "0", "--timeout", "900", "--justification", "x",
                    "--log", str(Path(folder) / "log.jsonl")]
            for arguments in (base, base + ["--execute", "--timeout", "0"], base + ["--execute", "--justification", " "]):
                with self.subTest(arguments=arguments[-3:]), patch("sys.argv", arguments), \
                        patch.object(command, "BlueQubitAdapter") as adapter, redirect_stderr(io.StringIO()):
                    with self.assertRaises(SystemExit) as error:
                        command.main()
                    self.assertEqual(error.exception.code, 2)
                    adapter.assert_not_called()
            with patch("sys.argv", base + ["--execute"]), patch.object(command, "BlueQubitAdapter") as adapter, \
                    patch.object(command, "load_settings", return_value=settings()), \
                    patch.object(command, "run_feature_jobs", return_value=(0, [])) as runner, \
                    patch.object(command.logging, "disable"), redirect_stdout(io.StringIO()):
                self.assertEqual(command.main(), 0)
                adapter.assert_called_once()
                self.assertEqual(runner.call_args.args[1]["per_job_seconds"], 900.0)
                self.assertEqual(runner.call_args.args[2:8], ("G4", "mps.cpu", OPTIONS, ["0"], "all_z", "x"))
