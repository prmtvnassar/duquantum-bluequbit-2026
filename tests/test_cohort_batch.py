from copy import deepcopy
from contextlib import redirect_stderr, redirect_stdout
from datetime import datetime, timedelta, timezone
import importlib.util
import io
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch

from bluequbit_samples.provenance import atomic_json
from otoc.bluequbit_adapter import BlueQubitAdapter, TERMINAL, validate_action
from otoc.cohort_batch import CohortBatchController
from otoc.coherent_selection import select_coherent_vector
from otoc.experiment_store import digest


OPTIONS = {"mps_bond_dimension": 32}
DIAGNOSTIC = {"targeted_diagnostics": True, "target_ids": ["Duke_G2_0"],
              "execution_timeout_seconds": 600, "quote_runtime_limit_seconds": 2000,
              "diagnostic_reason": "Measure a bounded fixed-precision diagnostic"}


def configuration():
    return {"version": "test", "release_status": "READY", "sample_budget_usd": 0,
            "graded_budget_usd": 30, "graded_reserve_fraction": .1, "stop_on_unknown_cost": True,
            "max_concurrent_jobs": 1, "max_remote_jobs": 800, "account_parallel_job_limit": 5,
            "remote_job_seconds": 600, "mps_chi32_job_seconds": 900,
            "deadline_utc": "2099-01-01T00:00:00+00:00", "submission_buffer_seconds": 1200,
            "cloud_pps_transpilation_level": 2, "stopping": {"signal_floor": .0001},
            "pilot_qubits": {p: [0, 1] for p in ("G2", "G3", "G4")},
            "graded_policy": {p: {"primary": "mps.cpu", "chi": 32, "reason": "test"}
                              for p in ("G2", "G3", "G4")}}


class FakeClock:
    def __init__(self):
        self.now = datetime(2030, 1, 1, tzinfo=timezone.utc)

    def __call__(self):
        return self.now

    def sleep(self, seconds):
        self.now += timedelta(seconds=seconds)


class FakeClient:
    def __init__(self, adapter):
        self.adapter = adapter
        self.jobs = {}
        self.run_calls, self.cancel_calls, self.completion_order = [], [], []
        self.polls_by_id, self.costs_by_id = {}, {}
        self.max_active, self.crash_after_submit = 0, False

    def add_job(self, cid):
        jid = "job-" + str(len(self.jobs))
        job = SimpleNamespace(job_id=jid, run_status="RUNNING", circuit_id=cid,
                              expectation_value=None, cost=None, run_time_ms=0, queue_time_ms=0,
                              remaining=self.polls_by_id.get(cid, 2), cancel_requested=False)
        self.jobs[jid] = job
        self.max_active = max(self.max_active, sum(j.run_status not in TERMINAL for j in self.jobs.values()))
        return job

    def run(self, cid, *, device, options, **kwargs):
        _, z = validate_action(cid, device, options)
        action = {"circuit_id": cid, "device": device, "options": options, "pauli": z}
        saved = json.loads((self.adapter.root / "remote_actions" / f"{digest(action)}.json").read_text())
        assert saved["status"] == "SUBMITTING"
        assert saved["quote"]["cost_usd"] >= 0
        assert saved["cohort_batch"]["budget_at_admission"]["planned_exposure_usd"] <= 27 + 1e-9
        self.run_calls.append(cid)
        job = self.add_job(cid)
        if self.crash_after_submit:
            raise ConnectionError("The service accepted the request but the response was lost")
        return job

    def get(self, jid):
        job = self.jobs[jid]
        if job.run_status not in TERMINAL:
            job.remaining -= 1
            if job.cancel_requested or job.remaining <= 0:
                job.run_status = "CANCELED" if job.cancel_requested else "COMPLETED"
                job.cost = self.costs_by_id.get(job.circuit_id, 0.0)
                job.expectation_value = .1 if job.run_status == "COMPLETED" else None
                job.run_time_ms = 100
                self.completion_order.append(job.circuit_id)
        return job

    def cancel(self, jid):
        self.cancel_calls.append(jid)
        self.jobs[jid].cancel_requested = True


class FakeAdapter:
    def __init__(self, root):
        self.root = Path(root)
        self.client = FakeClient(self)
        self.initial_spend, self.foreign_ids, self.unknown_costs = 0.0, [], 0
        self.quote_costs, self.quote_calls, self.saved = {}, [], []
        self.quote_runtimes = {}

    def _save(self, path, saved):
        atomic_json(path, saved)
        self.saved.append(deepcopy(saved))

    def quote(self, cid, device, options):
        self.quote_calls.append((cid, device, deepcopy(options)))
        cost = self.quote_costs.get(cid, 1.5 if options.get("mps_bond_dimension") == 64 else .2)
        quote = {"circuit_id": cid, "device": device, "options": deepcopy(options),
                 "cost_usd": cost, "runtime_seconds": self.quote_runtimes.get(cid, 1.0), "error": None}
        atomic_json(self.root / "quotes" / f"{digest([cid, device, options])}.json", quote)
        return quote

    def usage(self):
        jobs = list(self.client.jobs.values())
        active = [j.job_id for j in jobs if j.run_status not in TERMINAL] + list(self.foreign_ids)
        known = {j.job_id: j.cost for j in jobs if j.cost is not None}
        if self.initial_spend:
            known["prior-account-job"] = self.initial_spend
        return {"known_cost_usd": self.initial_spend + sum(j.cost or 0 for j in jobs),
                "known_job_costs_usd": known,
                "active_jobs": len(active), "active_job_ids": active,
                "unknown_terminal_costs": self.unknown_costs + sum(j.run_status in TERMINAL and j.cost is None for j in jobs),
                "job_count": len(jobs) + len(self.foreign_ids)}


def seed(adapter, cid, *, status="COMPLETED", job_id=None, options=None, cost=0.0):
    options = options or OPTIONS
    _, z = validate_action(cid, "mps.cpu", options)
    action = {"circuit_id": cid, "device": "mps.cpu", "options": deepcopy(options), "pauli": z}
    receipt = {"action": action, "status": status, "job_id": job_id or "seed-" + cid,
               "requested_at": "2030-01-01T00:00:00+00:00", "cost_usd": cost,
               "estimate": .1 if status == "COMPLETED" else None,
               "quote": {"circuit_id": cid, "device": "mps.cpu", "options": deepcopy(options),
                         "cost_usd": .2, "runtime_seconds": 1.0}}
    atomic_json(adapter.root / "remote_actions" / f"{digest(action)}.json", receipt)
    return receipt


class CohortBatchTests(TestCase):
    def prepare(self, folder, count=2):
        adapter = FakeAdapter(folder)
        clock = FakeClock()
        manifests = {p: [f"Duke_{p}_{q}" for q in range(count if p == "G2" else 2)]
                     for p in ("G2", "G3", "G4")}
        for p in ("G3", "G4"):
            for cid in manifests[p]:
                seed(adapter, cid)
        cohorts = {p: {"device": "mps.cpu", "options": deepcopy(OPTIONS)} for p in manifests}
        def controller(**kwargs):
            return CohortBatchController(adapter, configuration(), "G2", "mps.cpu", OPTIONS,
                        manifests=manifests, reserve_cohorts=cohorts, sleep=clock.sleep, clock=clock, **kwargs)
        return adapter, clock, manifests, cohorts, controller

    def test_two_slots_complete_out_of_order_without_duplicate_launches(self):
        with TemporaryDirectory() as folder:
            adapter, _, _, _, controller = self.prepare(folder, count=3)
            adapter.client.polls_by_id = {"Duke_G2_0": 3, "Duke_G2_1": 1, "Duke_G2_2": 2}
            result = controller().run()
            self.assertEqual(result["status"], "COMPLETE")
            self.assertEqual(adapter.client.max_active, 2)
            self.assertEqual(adapter.client.completion_order[0], "Duke_G2_1")
            self.assertEqual(len(set(adapter.client.run_calls)), 3)
            self.assertEqual(result["pending_job_ids"], [])

    def test_budget_boundary_reserves_first_launch_before_second_admission(self):
        with TemporaryDirectory() as folder:
            adapter, _, _, _, controller = self.prepare(folder)
            adapter.initial_spend = 26.6
            adapter.client.costs_by_id["Duke_G2_0"] = .2
            adapter.quote_costs["Duke_G2_1"] = .4
            result = controller().run()
            self.assertEqual(result["reason"], "budget_commitments_and_cohort_reserve")
            self.assertEqual(adapter.client.run_calls, ["Duke_G2_0"])
            self.assertEqual(adapter.client.max_active, 1)
            intent = next(r for r in adapter.saved if r["status"] == "SUBMITTING")
            self.assertAlmostEqual(intent["cohort_batch"]["budget_at_admission"]["planned_exposure_usd"], 27)

    def test_foreign_active_jobs_block_launches_even_below_account_limit(self):
        with TemporaryDirectory() as folder:
            adapter, _, _, _, controller = self.prepare(folder)
            adapter.foreign_ids = ["foreign-1"]
            result = controller().run()
            self.assertEqual(result["reason"], "foreign_active_jobs")
            self.assertEqual(adapter.client.run_calls, [])

    def test_unknown_terminal_account_cost_blocks_launches(self):
        with TemporaryDirectory() as folder:
            adapter, _, _, _, controller = self.prepare(folder)
            adapter.unknown_costs = 1
            result = controller().run()
            self.assertEqual(result["reason"], "unknown_terminal_cost")
            self.assertEqual(adapter.client.run_calls, [])

    def test_ambiguous_post_submit_crash_never_duplicates_on_resume(self):
        with TemporaryDirectory() as folder:
            adapter, _, _, _, controller = self.prepare(folder)
            adapter.client.crash_after_submit = True
            result = controller().run()
            self.assertEqual(result["reason"], "ambiguous_submission_intent")
            self.assertEqual(len(adapter.client.run_calls), 1)
            again = controller().run()
            self.assertEqual(again["reason"], "ambiguous_submission_intent")
            self.assertEqual(len(adapter.client.run_calls), 1)
            receipt = next(r for r in adapter.saved if r["status"] == "SUBMITTING")
            self.assertNotIn("job_id", receipt)
            self.assertEqual(receipt["cohort_batch"]["reserved_quote_usd"], .2)

    def test_resume_known_job_id_attaches_without_resubmitting(self):
        with TemporaryDirectory() as folder:
            adapter, _, _, _, controller = self.prepare(folder)
            job = adapter.client.add_job("Duke_G2_0")
            seed(adapter, "Duke_G2_0", status="RUNNING", job_id=job.job_id, cost=None)
            result = controller().run()
            self.assertEqual(result["status"], "COMPLETE")
            self.assertEqual(adapter.client.run_calls, ["Duke_G2_1"])

    def test_stop_cancels_both_owned_jobs_and_records_terminal_costs(self):
        with TemporaryDirectory() as folder:
            adapter, _, _, _, controller = self.prepare(folder)
            for cid in ("Duke_G2_0", "Duke_G2_1"):
                adapter.client.polls_by_id[cid] = 100
                job = adapter.client.add_job(cid)
                seed(adapter, cid, status="RUNNING", job_id=job.job_id, cost=None)
            (adapter.root / "STOP").write_text("stop", encoding="utf-8")
            result = controller().run()
            self.assertEqual(result["status"], "STOPPED")
            self.assertEqual(len(adapter.client.cancel_calls), 2)
            self.assertEqual(result["pending_job_ids"], [])
            self.assertEqual(adapter.client.run_calls, [])
            terminals = [r for r in adapter.saved if r["status"] == "CANCELED"]
            self.assertEqual(len(terminals), 2)
            self.assertTrue(all(r["cost_usd"] == 0 for r in terminals))

    def test_unknown_owned_terminal_cost_keeps_reservation_and_blocks_other_row(self):
        with TemporaryDirectory() as folder:
            adapter, _, _, _, controller = self.prepare(folder)
            adapter.client.polls_by_id["Duke_G2_0"] = 1
            adapter.client.costs_by_id["Duke_G2_0"] = None
            job = adapter.client.add_job("Duke_G2_0")
            seed(adapter, "Duke_G2_0", status="RUNNING", job_id=job.job_id, cost=None)
            result = controller(reconcile_seconds=6).run()
            self.assertEqual(result["reason"], "unknown_terminal_cost_reconciliation_pending")
            self.assertEqual(result["pending_job_ids"], [job.job_id])
            self.assertEqual(adapter.client.run_calls, [])

    def test_reserve_prices_match_selected_full_options_for_other_cohort(self):
        with TemporaryDirectory() as folder:
            adapter, _, _, cohorts, controller = self.prepare(folder)
            cohorts["G4"]["options"] = {"mps_bond_dimension": 64}
            result = controller().run()
            self.assertEqual(result["status"], "COMPLETE")
            self.assertEqual(result["reserve_rates"]["G4"], 1.5)
            self.assertEqual(result["budget"]["missing_unreserved_rows"]["G4"], 2)
            self.assertGreaterEqual(result["budget"]["missing_cohort_reserve_usd"], 3)
            self.assertTrue(any(p[0].startswith("Duke_G4") and p[2] == {"mps_bond_dimension": 64}
                                for p in adapter.quote_calls))

    def test_serial_runner_lock_prevents_any_api_calls(self):
        with TemporaryDirectory() as folder:
            adapter, _, _, _, controller = self.prepare(folder)
            atomic_json(adapter.root / "remote_runner.lock", {"pid": os.getpid()})
            with self.assertRaisesRegex(RuntimeError, "Another workflow runner"):
                controller().run()
            self.assertEqual(adapter.quote_calls, [])
            self.assertEqual(adapter.client.run_calls, [])

    def test_complete_usable_baseline_does_not_reserve_an_entire_refinement_cohort(self):
        with TemporaryDirectory() as folder:
            adapter, _, _, cohorts, controller = self.prepare(folder)
            original = seed(adapter, "Duke_G4_1")
            original["estimate"] = .2
            atomic_json(adapter.root / "remote_actions" / f"{digest(original['action'])}.json", original)
            cohorts["G4"]["options"] = {"mps_bond_dimension": 64}
            result = controller().run()
            self.assertEqual(result["status"], "COMPLETE")
            self.assertTrue(result["has_usable_baseline"]["G4"])
            self.assertEqual(result["budget"]["missing_unreserved_rows"]["G4"], 0)
            self.assertFalse(any(call[0].startswith("Duke_G4") for call in adapter.quote_calls))

    def test_cpu_and_two_slot_boundary_is_explicit(self):
        with TemporaryDirectory() as folder:
            _, _, _, _, controller = self.prepare(folder)
            with self.assertRaises(ValueError):
                controller(slots=3)

    def test_bounded_batch_drains_owned_jobs_before_exit(self):
        with TemporaryDirectory() as folder:
            adapter, _, _, _, controller = self.prepare(folder, count=3)
            result = controller(max_jobs=1).run()
            self.assertEqual(result["status"], "BOUNDED_STOP")
            self.assertEqual(len(adapter.client.run_calls), 1)
            self.assertEqual(result["pending_job_ids"], [])

    def test_existing_failed_target_blocks_remaining_cohort_before_spending(self):
        with TemporaryDirectory() as folder:
            adapter, _, _, _, controller = self.prepare(folder)
            seed(adapter, "Duke_G2_1", status="TERMINATED")
            result = controller().run()
            self.assertEqual(result["reason"], "failed_target_action_requires_review")
            self.assertEqual(adapter.client.run_calls, [])

    def test_known_local_terminal_charge_missing_from_account_index_blocks_admission(self):
        with TemporaryDirectory() as folder:
            adapter, _, _, _, controller = self.prepare(folder)
            adapter.initial_spend = 26.6
            seed(adapter, "Duke_G2_0", cost=.4)
            result = controller().run()
            self.assertEqual(result["reason"], "budget_commitments_and_cohort_reserve")
            self.assertAlmostEqual(result["actual_spent_floor_usd"], 27)
            self.assertEqual(adapter.client.run_calls, [])

    def test_durable_cost_union_survives_restart_and_account_index_regression(self):
        with TemporaryDirectory() as folder:
            adapter, _, _, _, controller = self.prepare(folder)
            adapter.initial_spend = 26.6
            first = controller()
            first._load()
            self.assertIsNone(first._usage_gate()[1])
            seed(adapter, "Duke_G2_0", cost=.4)
            adapter.initial_spend = 0  # The next account page omits prior jobs.
            result = controller().run()
            self.assertEqual(result["reason"], "budget_commitments_and_cohort_reserve")
            self.assertAlmostEqual(result["actual_spent_floor_usd"], 27)
            self.assertEqual(adapter.client.run_calls, [])

    def test_indexed_receipt_charge_is_counted_once(self):
        with TemporaryDirectory() as folder:
            adapter, _, _, _, controller = self.prepare(folder)
            adapter.initial_spend = 26.4
            job = adapter.client.add_job("Duke_G2_0")
            job.run_status, job.cost, job.expectation_value = "COMPLETED", .4, .1
            seed(adapter, "Duke_G2_0", job_id=job.job_id, cost=.4)
            result = controller().run()
            self.assertEqual(result["status"], "COMPLETE")
            self.assertAlmostEqual(result["budget"]["actual_spent_usd"], 26.8)
            self.assertEqual(adapter.client.run_calls, ["Duke_G2_1"])

    def test_teammate_charge_is_excluded_from_current_account(self):
        with TemporaryDirectory() as folder:
            adapter, _, _, _, controller = self.prepare(folder)
            imported = seed(adapter, "Duke_G3_0", cost=100)
            imported.update(origin="collaborator_kevin", account_scope="collaborator; not current API account")
            atomic_json(adapter.root / "remote_actions" / f"{digest(imported['action'])}.json", imported)
            result = controller().run()
            self.assertEqual(result["status"], "COMPLETE")
            self.assertEqual(result["actual_spent_floor_usd"], 0)

    def test_missing_account_cost_breakdown_fails_closed(self):
        with TemporaryDirectory() as folder:
            adapter, _, _, _, controller = self.prepare(folder)
            original_usage = adapter.usage
            def without_breakdown():
                usage = original_usage()
                usage.pop("known_job_costs_usd")
                return usage
            adapter.usage = without_breakdown
            result = controller().run()
            self.assertEqual(result["reason"], "unknown_account_cost_breakdown")
            self.assertEqual(adapter.client.run_calls, [])

    def test_stale_other_cohort_quote_is_refreshed_before_spending(self):
        with TemporaryDirectory() as folder:
            adapter, _, _, cohorts, controller = self.prepare(folder)
            cohorts["G4"]["options"] = {"mps_bond_dimension": 64}
            atomic_json(adapter.root / "quotes" / "stale.json", {
                "circuit_id": "Duke_G4_0", "device": "mps.cpu", "options": {"mps_bond_dimension": 64},
                "cost_usd": .01, "runtime_seconds": 1, "quoted_at": "2000-01-01T00:00:00+00:00"})
            adapter.initial_spend = 26.5
            result = controller().run()
            self.assertEqual(result["reason"], "budget_commitments_and_cohort_reserve")
            self.assertEqual(result["reserve_rates"]["G4"], 1.5)
            self.assertEqual(adapter.client.run_calls, [])

    def test_other_cohort_reserve_refreshes_during_long_running_batch(self):
        with TemporaryDirectory() as folder:
            adapter, clock, _, cohorts, controller = self.prepare(folder)
            cohorts["G4"]["options"] = {"mps_bond_dimension": 64}
            current = controller()
            current._load()
            current._initialize_cohorts()
            self.assertIsNone(current._reserve_rates())
            adapter.quote_costs["Duke_G4_0"] = 2.0
            clock.sleep(300)
            self.assertIsNone(current._reserve_rates())
            self.assertEqual(current.rates["G4"], 2.0)

    def test_stop_requests_cancellation_when_job_get_is_unavailable(self):
        with TemporaryDirectory() as folder:
            adapter, _, _, _, controller = self.prepare(folder)
            for cid in ("Duke_G2_0", "Duke_G2_1"):
                job = adapter.client.add_job(cid)
                seed(adapter, cid, status="RUNNING", job_id=job.job_id, cost=None)
            def unavailable(_):
                raise ConnectionError("Job read endpoint unavailable")
            adapter.client.get = unavailable
            (adapter.root / "STOP").write_text("stop", encoding="utf-8")
            result = controller(reconcile_seconds=6).run()
            self.assertEqual(result["reason"], "stop_file_reconciliation_pending")
            self.assertEqual(len(adapter.client.cancel_calls), 2)
            self.assertEqual(len(result["pending_job_ids"]), 2)
            self.assertEqual(adapter.client.run_calls, [])

    def test_timeout_requests_cancellation_when_job_get_is_unavailable(self):
        with TemporaryDirectory() as folder:
            adapter, clock, _, _, controller = self.prepare(folder)
            job = adapter.client.add_job("Duke_G2_0")
            seed(adapter, "Duke_G2_0", status="RUNNING", job_id=job.job_id, cost=None)
            clock.sleep(901)
            def unavailable(_):
                raise ConnectionError("Job read endpoint unavailable")
            adapter.client.get = unavailable
            result = controller(reconcile_seconds=6).run()
            self.assertEqual(result["reason"], "job_timeout_reconciliation_pending")
            self.assertEqual(adapter.client.cancel_calls, [job.job_id])
            self.assertEqual(adapter.client.run_calls, [])

    def test_terminal_cost_is_durable_before_receipt_releases_reservation(self):
        with TemporaryDirectory() as folder:
            adapter, _, _, _, controller = self.prepare(folder)
            adapter.client.costs_by_id["Duke_G2_0"] = .4
            original_save = adapter._save
            observed_terminal = []
            def check_journal(path, record):
                if record["status"] == "COMPLETED" and record.get("cost_usd") == .4:
                    journal = json.loads((adapter.root / "cohort_accounting.json").read_text())
                    self.assertEqual(journal["observed_job_costs_usd"][record["job_id"]], .4)
                    observed_terminal.append(record["job_id"])
                original_save(path, record)
            adapter._save = check_journal
            result = controller(max_jobs=1).run()
            self.assertEqual(result["status"], "BOUNDED_STOP")
            self.assertEqual(len(observed_terminal), 1)

    def test_ordinary_runtime_limit_is_unchanged(self):
        with TemporaryDirectory() as folder:
            adapter, _, _, _, controller = self.prepare(folder)
            current = controller()
            self.assertEqual(current.timeout, 900)
            self.assertEqual(current.quote_runtime_limit, 900)
            adapter.quote_runtimes["Duke_G2_0"] = 901
            result = current.run()
            self.assertEqual(result["reason"], "invalid_or_excessive_runtime")
            self.assertEqual(adapter.client.run_calls, [])

    def test_diagnostic_arguments_cannot_loosen_an_ordinary_cohort(self):
        with TemporaryDirectory() as folder:
            adapter, _, _, _, controller = self.prepare(folder)
            for arguments in ({"target_ids": ["Duke_G2_0"]}, {"execution_timeout_seconds": 600},
                              {"quote_runtime_limit_seconds": 2000}, {"diagnostic_reason": "check"}):
                with self.subTest(arguments=arguments), self.assertRaises(ValueError):
                    controller(**arguments)
            self.assertEqual(adapter.quote_calls, [])
            self.assertEqual(adapter.client.run_calls, [])

    def test_invalid_diagnostic_targets_and_caps_fail_before_api_calls(self):
        with TemporaryDirectory() as folder:
            adapter, _, _, _, controller = self.prepare(folder)
            cases = [{"target_ids": ids} for ids in (None, [], "Duke_G2_0", ["Duke_G2_0", "Duke_G2_0"],
                     ["Duke_G3_0"], ["Duke_G2_2"], ["Duke_G2_36"], [123])]
            cases += [{name: value} for name in ("execution_timeout_seconds", "quote_runtime_limit_seconds")
                      for value in (None, True, 0, .5, -1, 3601, float("nan"), float("inf"), "600")]
            for overrides in cases:
                with self.subTest(overrides=overrides), self.assertRaises(ValueError):
                    controller(**{**DIAGNOSTIC, **overrides})
            self.assertEqual(adapter.quote_calls, [])
            self.assertEqual(adapter.client.run_calls, [])

    def test_diagnostic_subset_keeps_full_cohort_reserve_and_cannot_form_export_vector(self):
        with TemporaryDirectory() as folder:
            adapter, _, manifests, _, controller = self.prepare(folder, count=3)
            current = controller(**{**DIAGNOSTIC, "target_ids": ["Duke_G2_1"]})
            result = current.run()
            self.assertEqual(result["status"], "DIAGNOSTICS_COMPLETE")
            self.assertEqual(adapter.client.run_calls, ["Duke_G2_1"])
            self.assertEqual(result["completed_rows"], 1)
            self.assertEqual(result["required_rows"], 3)
            self.assertEqual(result["completed_target_rows"], 1)
            self.assertEqual(result["required_target_rows"], 1)
            self.assertEqual(result["budget"]["missing_unreserved_rows"]["G2"], 2)
            self.assertAlmostEqual(result["budget"]["missing_cohort_reserve_usd"], .4)
            self.assertEqual(select_coherent_vector(list(current.records.values()), manifests["G2"],
                                                   "mps.cpu")["status"], "INCOMPLETE")

    def test_diagnostic_quote_above_execution_cap_requires_and_records_explicit_limits(self):
        with TemporaryDirectory() as folder:
            adapter, _, _, _, controller = self.prepare(folder)
            adapter.quote_runtimes["Duke_G2_0"] = 1878
            adapter.quote_costs["Duke_G2_0"] = 2.0
            result = controller(**DIAGNOSTIC).run()
            self.assertEqual(result["status"], "DIAGNOSTICS_COMPLETE")
            self.assertEqual(result["execution_timeout_seconds"], 600)
            self.assertEqual(result["quote_runtime_limit_seconds"], 2000)
            self.assertEqual(result["target_ids"], ["Duke_G2_0"])
            self.assertEqual(result["diagnostic_reason"], DIAGNOSTIC["diagnostic_reason"])
            intent = next(r for r in adapter.saved if r["status"] == "SUBMITTING")
            self.assertEqual(intent["timeout_seconds"], 600)
            self.assertEqual(intent["cohort_batch"]["quote_runtime_limit_seconds"], 2000)
            self.assertEqual(intent["cohort_batch"]["target_ids"], ["Duke_G2_0"])
            self.assertEqual(intent["cohort_batch"]["reserved_quote_usd"], 2.0)
            self.assertEqual(intent["cohort_batch"]["budget_at_admission"]["new_quote_usd"], 2.0)
            self.assertEqual(intent["scheduler_justification"], DIAGNOSTIC["diagnostic_reason"])

    def test_diagnostic_quote_limit_and_conservative_deadline_still_block(self):
        for remaining, quote_limit, expected in ((10000, 1800, "invalid_or_excessive_runtime"),
                                                  (3000, 2000, "deadline_buffer")):
            with self.subTest(reason=expected), TemporaryDirectory() as folder:
                adapter, clock, manifests, cohorts, _ = self.prepare(folder)
                adapter.quote_runtimes["Duke_G2_0"] = 1878
                settings = configuration()
                settings["deadline_utc"] = (clock() + timedelta(seconds=remaining)).isoformat()
                current = CohortBatchController(adapter, settings, "G2", "mps.cpu", OPTIONS,
                            manifests=manifests, reserve_cohorts=cohorts, sleep=clock.sleep, clock=clock,
                            **{**DIAGNOSTIC, "quote_runtime_limit_seconds": quote_limit})
                result = current.run()
                self.assertEqual(result["reason"], expected)
                self.assertEqual(adapter.client.run_calls, [])

    def test_diagnostic_requests_cancellation_at_execution_cap_and_keeps_failed_receipt(self):
        with TemporaryDirectory() as folder:
            adapter, _, _, _, controller = self.prepare(folder)
            adapter.client.polls_by_id["Duke_G2_0"] = 10000
            adapter.quote_runtimes["Duke_G2_0"] = 1878
            result = controller(**DIAGNOSTIC).run()
            self.assertEqual(result["status"], "BLOCKED")
            self.assertEqual(result["reason"], "failed_target_action_requires_review")
            self.assertEqual(len(adapter.client.cancel_calls), 1)
            canceled = next(r for r in adapter.saved if r["status"] == "CANCELED")
            age = (datetime.fromisoformat(canceled["cancel_requested_at"])
                   - datetime.fromisoformat(canceled["requested_at"])).total_seconds()
            self.assertEqual(age, 600)
            self.assertEqual(canceled["cancel_reason"], "job_timeout")
            again = controller(**DIAGNOSTIC).run()
            self.assertEqual(again["reason"], "failed_target_action_requires_review")
            self.assertEqual(adapter.client.run_calls, ["Duke_G2_0"])

    def test_diagnostic_resumes_known_target_and_reuses_completed_target_without_launches(self):
        with TemporaryDirectory() as folder:
            adapter, _, _, _, controller = self.prepare(folder)
            job = adapter.client.add_job("Duke_G2_0")
            seed(adapter, "Duke_G2_0", status="RUNNING", job_id=job.job_id, cost=None)
            first = controller(**DIAGNOSTIC).run()
            self.assertEqual(first["status"], "DIAGNOSTICS_COMPLETE")
            second = controller(**DIAGNOSTIC).run()
            self.assertEqual(second["status"], "DIAGNOSTICS_COMPLETE")
            self.assertEqual(adapter.client.run_calls, [])

    def test_diagnostic_resume_does_not_relax_saved_execution_cap(self):
        with TemporaryDirectory() as folder:
            adapter, clock, _, _, controller = self.prepare(folder)
            adapter.client.polls_by_id["Duke_G2_0"] = 10000
            job = adapter.client.add_job("Duke_G2_0")
            saved = seed(adapter, "Duke_G2_0", status="RUNNING", job_id=job.job_id, cost=None)
            saved["timeout_seconds"] = 30
            atomic_json(adapter.root / "remote_actions" / f"{digest(saved['action'])}.json", saved)
            clock.sleep(30)
            result = controller(**DIAGNOSTIC).run()
            self.assertEqual(result["reason"], "failed_target_action_requires_review")
            self.assertEqual(adapter.client.cancel_calls, [job.job_id])
            self.assertEqual(adapter.client.run_calls, [])

    def test_diagnostic_full_reserve_blocks_unfunded_targeted_launch(self):
        with TemporaryDirectory() as folder:
            adapter, _, _, _, controller = self.prepare(folder, count=3)
            adapter.initial_spend = 26.5
            result = controller(**DIAGNOSTIC).run()
            self.assertEqual(result["reason"], "budget_commitments_and_cohort_reserve")
            self.assertEqual(result["budget"]["missing_unreserved_rows"]["G2"], 2)
            self.assertAlmostEqual(result["budget"]["planned_exposure_usd"], 27.1)
            self.assertEqual(adapter.client.run_calls, [])

    def test_diagnostic_baseline_exemption_still_reserves_every_active_full_quote(self):
        with TemporaryDirectory() as folder:
            adapter, _, _, _, controller = self.prepare(folder, count=3)
            for q in range(3):
                saved = seed(adapter, f"Duke_G2_{q}", options={"mps_bond_dimension": 16})
                saved["estimate"] = .1 * q
                atomic_json(adapter.root / "remote_actions" / f"{digest(saved['action'])}.json", saved)
            adapter.quote_costs.update({"Duke_G2_0": 1.5, "Duke_G2_1": 1.5})
            result = controller(**{**DIAGNOSTIC, "target_ids": ["Duke_G2_0", "Duke_G2_1"]}).run()
            self.assertEqual(result["status"], "DIAGNOSTICS_COMPLETE")
            self.assertTrue(result["has_usable_baseline"]["G2"])
            intents = [r for r in adapter.saved if r["status"] == "SUBMITTING"]
            second = intents[1]["cohort_batch"]["budget_at_admission"]
            self.assertEqual(second["missing_cohort_reserve_usd"], 0)
            self.assertEqual(second["outstanding_quote_usd"], 1.5)
            self.assertEqual(second["new_quote_usd"], 1.5)

    def test_diagnostic_foreign_and_unknown_state_still_block(self):
        for condition, expected in (("foreign", "foreign_active_jobs"), ("unknown", "unknown_terminal_cost"),
                                     ("failed", "failed_target_action_requires_review"),
                                     ("outside_target", "foreign_unresolved_receipt")):
            with self.subTest(condition=condition), TemporaryDirectory() as folder:
                adapter, _, _, _, controller = self.prepare(folder)
                if condition == "foreign":
                    adapter.foreign_ids = ["foreign-1"]
                elif condition == "unknown":
                    adapter.unknown_costs = 1
                elif condition == "failed":
                    seed(adapter, "Duke_G2_0", status="TERMINATED")
                else:
                    job = adapter.client.add_job("Duke_G2_1")
                    seed(adapter, "Duke_G2_1", status="RUNNING", job_id=job.job_id, cost=None)
                result = controller(**DIAGNOSTIC).run()
                self.assertEqual(result["reason"], expected)
                self.assertEqual(adapter.client.run_calls, [])
                self.assertEqual(adapter.client.cancel_calls, [])

    def test_g4_chi64_diagnostic_uses_existing_full_baseline_and_new_full_quote(self):
        with TemporaryDirectory() as folder:
            adapter, clock, manifests, cohorts, _ = self.prepare(folder)
            baseline = seed(adapter, "Duke_G4_1")
            baseline["estimate"] = .2
            atomic_json(adapter.root / "remote_actions" / f"{digest(baseline['action'])}.json", baseline)
            adapter.quote_runtimes["Duke_G4_0"] = 1878
            current = CohortBatchController(adapter, configuration(), "G4", "mps.cpu", {"mps_bond_dimension": 64},
                        manifests=manifests, reserve_cohorts=cohorts, sleep=clock.sleep, clock=clock,
                        **{**DIAGNOSTIC, "target_ids": ["Duke_G4_0"]})
            result = current.run()
            self.assertEqual(result["status"], "DIAGNOSTICS_COMPLETE")
            self.assertTrue(result["has_usable_baseline"]["G4"])
            self.assertEqual(result["budget"]["missing_unreserved_rows"]["G4"], 0)
            self.assertEqual(result["budget"]["new_quote_usd"], 1.5)
            self.assertEqual(result["completed_rows"], 1)
            self.assertEqual(result["required_rows"], 2)
            self.assertEqual(adapter.client.run_calls, ["Duke_G4_0"])

    def test_diagnostic_mode_cannot_bypass_ready_budget_cpu_or_slot_requirements(self):
        with TemporaryDirectory() as folder:
            adapter, clock, manifests, cohorts, _ = self.prepare(folder)
            cases = [({"release_status": "NOT_READY"}, "mps.cpu", 2),
                     ({"sample_budget_usd": .1}, "mps.cpu", 2),
                     ({"graded_budget_usd": 31}, "mps.cpu", 2),
                     ({"stop_on_unknown_cost": False}, "mps.cpu", 2),
                     ({}, "mps.gpu", 2), ({}, "mps.cpu", 3)]
            for changed, device, slots in cases:
                with self.subTest(changed=changed, device=device, slots=slots), self.assertRaises(ValueError):
                    CohortBatchController(adapter, {**configuration(), **changed}, "G2", device, OPTIONS,
                            manifests=manifests, reserve_cohorts=cohorts, sleep=clock.sleep, clock=clock,
                            slots=slots, **DIAGNOSTIC)
            self.assertEqual(adapter.quote_calls, [])
            self.assertEqual(adapter.client.run_calls, [])


class DiagnosticCommandTests(TestCase):
    @staticmethod
    def command():
        path = Path(__file__).resolve().parents[1] / "scripts" / "run_cohort_batch.py"
        spec = importlib.util.spec_from_file_location("cohort_command_test", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_cli_routes_adapter_and_export_to_the_same_explicit_or_default_state_root(self):
        with TemporaryDirectory() as folder:
            options = Path(folder) / "options.json"
            options.write_text(json.dumps(OPTIONS))
            for selected in (None, Path(folder) / "shared account state"):
                with self.subTest(selected=selected):
                    command = self.command()
                    settings = configuration()
                    arguments = ["run_cohort_batch.py", "--execute", "--problem", "G2", "--device", "mps.cpu",
                                 "--options-file", str(options)]
                    if selected is not None:
                        arguments.extend(["--state-root", str(selected)])
                    expected = selected if selected is not None else Path("results/workflow")
                    with patch("sys.argv", arguments), patch.object(command, "BlueQubitAdapter") as adapter, \
                            patch.object(command, "load_settings", return_value=settings), \
                            patch.object(command, "run_cohort_batch", return_value={"status": "COMPLETE"}) as runner, \
                            patch.object(command, "export_complete", return_value=[]) as exporter, \
                            patch.object(command.logging, "disable"), redirect_stdout(io.StringIO()):
                        self.assertEqual(command.main(), 0)
                        adapter.assert_called_once_with(root=expected)
                        self.assertIs(runner.call_args.args[0], adapter.return_value)
                        exporter.assert_called_once_with(settings, root=expected)

    def test_diagnostic_cli_does_not_export_partial_or_complete_cohorts(self):
        for status in ("DIAGNOSTICS_COMPLETE", "COMPLETE"):
            with self.subTest(status=status), TemporaryDirectory() as folder:
                options = Path(folder) / "options.json"
                options.write_text(json.dumps(OPTIONS))
                command = self.command()
                arguments = ["run_cohort_batch.py", "--execute", "--problem", "G2", "--device", "mps.cpu",
                             "--options-file", str(options), "--targeted-diagnostics", "--target-ids", "Duke_G2_0",
                             "--execution-timeout", "600", "--quote-runtime-limit", "2000"]
                with patch("sys.argv", arguments), patch.object(command, "BlueQubitAdapter"), \
                        patch.object(command, "load_settings", return_value=configuration()), \
                        patch.object(command, "run_cohort_batch", return_value={"status": status}) as runner, \
                        patch.object(command, "export_complete") as exporter, \
                        patch.object(command.logging, "disable"), redirect_stdout(io.StringIO()):
                    self.assertEqual(command.main(), 0)
                    exporter.assert_not_called()
                    self.assertTrue(runner.call_args.kwargs["targeted_diagnostics"])
                    self.assertEqual(runner.call_args.kwargs["target_ids"], ["Duke_G2_0"])
                    self.assertEqual(runner.call_args.kwargs["execution_timeout_seconds"], 600)
                    self.assertEqual(runner.call_args.kwargs["quote_runtime_limit_seconds"], 2000)

    def test_diagnostic_cli_requires_mode_targets_and_both_caps_before_adapter_creation(self):
        command = self.command()
        base = ["run_cohort_batch.py", "--execute", "--problem", "G2", "--device", "mps.cpu",
                "--options-file", "not-read.json"]
        cases = [["--execution-timeout", "600"], ["--target-ids", "Duke_G2_0"],
                 ["--targeted-diagnostics", "--target-ids", "Duke_G2_0", "--execution-timeout", "600"],
                 ["--targeted-diagnostics", "--execution-timeout", "600", "--quote-runtime-limit", "2000"],
                 ["--targeted-diagnostics", "--target-ids", "Duke_G2_0", "--execution-timeout", "600",
                  "--quote-runtime-limit", "nan"]]
        for arguments in cases:
            with self.subTest(arguments=arguments), patch("sys.argv", base + arguments), \
                    patch.object(command, "BlueQubitAdapter") as adapter, redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit) as error:
                    command.main()
                self.assertEqual(error.exception.code, 2)
                adapter.assert_not_called()


class AccountCostIdentityTests(TestCase):
    def adapter(self, root, jobs):
        backend = SimpleNamespace(send_request=lambda **kwargs: SimpleNamespace(json=lambda: {"data": jobs}))
        return BlueQubitAdapter(root=root, client=SimpleNamespace(_backend_connection=backend))

    def test_usage_reports_known_costs_by_job_id_in_dollars(self):
        with TemporaryDirectory() as folder:
            jobs = [{"job_id": "a", "run_status": "COMPLETED", "cost": 40},
                    {"job_id": "b", "run_status": "RUNNING", "cost": None}]
            usage = self.adapter(folder, jobs).usage()
            self.assertEqual(usage["known_job_costs_usd"], {"a": .4})
            self.assertEqual(usage["known_cost_usd"], .4)
            self.assertEqual(usage["active_job_ids"], ["b"])

    def test_usage_does_not_supply_partial_mapping_for_ambiguous_job_ids(self):
        for ids in (("a", "a"), ("a", None)):
            with self.subTest(ids=ids), TemporaryDirectory() as folder:
                jobs = [{"job_id": jid, "run_status": "COMPLETED", "cost": 40} for jid in ids]
                usage = self.adapter(folder, jobs).usage()
                self.assertIsNone(usage["known_job_costs_usd"])
