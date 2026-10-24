"""A single owner of bounded CPU cohorts or one targeted approximate GPU job.

Per-action SUBMITTING receipts are the reservation journal.  This controller
never calls the serial adapter.run(), weakens its gates, or starts worker threads.
Quotes constrain planned exposure; they are not service-enforced charge caps.
"""

from copy import deepcopy
import csv
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import time

from bluequbit_samples.provenance import atomic_json
from .bluequbit_adapter import SIZES, TERMINAL, validate_action
from .campaign_reasoning import recover_flat_policy
from .coherent_selection import select_coherent_vector
from .experiment_store import ExperimentStore, digest, utc_now
from .graded import baseline_route_policy, _options
from .ledger import REPO, atomic_bytes


CPU_DEVICES = {"mps.cpu", "pauli-path"}
GPU_DEVICES = {"mps.gpu", "pauli-path.gpu"}
CLOSED = TERMINAL | {"INVALID_RESULT"}
PROBLEMS = ("G2", "G3", "G4")
RESERVE_QUOTE_SECONDS = 300


def _money(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) and value >= 0


def _complete(record):
    value = record.get("estimate")
    return (record.get("status") == "COMPLETED" and _money(record.get("cost_usd"))
            and isinstance(value, (int, float)) and not isinstance(value, bool)
            and math.isfinite(value) and abs(value) <= 1 + 1e-8)


def _current_account(record):
    # Reviewed teammate imports are reusable estimates, not charges to this API
    # account. Unmarked local receipts remain current-account obligations.
    return (record.get("origin") != "collaborator_kevin"
            and record.get("account_scope") != "collaborator; not current API account")


def load_manifests():
    manifests = {}
    for problem in PROBLEMS:
        paths = list((REPO / "problems").glob(f"*_graded_{problem}/local_submission_template.csv"))
        if len(paths) != 1:
            raise ValueError("Need one retained template per graded cohort")
        with paths[0].open(newline="", encoding="utf-8-sig") as stream:
            rows = csv.DictReader(stream)
            if rows.fieldnames != ["circuit_id", "value"]:
                raise ValueError("Invalid retained template header")
            ids = [row["circuit_id"] for row in rows]
        expected = {f"Duke_{problem}_{q}" for q in range(SIZES[problem])}
        if len(ids) != len(expected) or set(ids) != expected:
            raise ValueError("Retained template has missing or duplicate IDs")
        manifests[problem] = ids
    return manifests


class CohortBatchController:
    """Fill one explicit cohort, reserving completion of all selected G2-G4 cohorts.

    Optional manifests, clock and sleep are injection points for offline tests.
    The command-line entry point always uses the retained complete templates.
    No network or filesystem mutation occurs until run() acquires remote_runner.
    """

    def __init__(self, adapter, settings, problem, device, options, *, slots=2,
                 max_jobs=None, reserve_cohorts=None, manifests=None, poll_seconds=3,
                 reconcile_seconds=60, sleep=time.sleep, clock=None,
                 targeted_diagnostics=False, target_ids=None, execution_timeout_seconds=None,
                 quote_runtime_limit_seconds=None, diagnostic_reason=None):
        if settings.get("release_status") != "READY":
            raise ValueError("Only a READY campaign may launch a cohort")
        if settings.get("sample_budget_usd") != 0 or not settings.get("stop_on_unknown_cost"):
            raise ValueError("Free samples and known costs remain mandatory")
        if not _money(settings.get("graded_budget_usd")) or not 0 < settings["graded_budget_usd"] <= 30:
            raise ValueError("Invalid graded budget")
        fraction = settings.get("graded_reserve_fraction")
        if not _money(fraction) or fraction >= 1:
            raise ValueError("Invalid graded reserve")
        if problem not in PROBLEMS or device not in CPU_DEVICES | GPU_DEVICES:
            raise ValueError("This controller only supports approximate G2-G4 CPU devices or targeted GPU diagnostics")
        if type(slots) is not int or not 1 <= slots <= 2:
            raise ValueError("Use one or two CPU slots")
        self.gpu = device in GPU_DEVICES
        if self.gpu:
            if targeted_diagnostics is not True or slots != 1 or settings.get("gpu_enabled") is not True:
                raise ValueError("GPU requires explicitly enabled targeted diagnostics and exactly one slot")
            for name, ceiling in (("gpu_total_seconds", 27000), ("gpu_hour_seconds", 2700)):
                if not _money(settings.get(name)) or not 0 < settings[name] <= ceiling:
                    raise ValueError("GPU quota limits must be finite, positive and within the account ceilings")
        if max_jobs is not None and (type(max_jobs) is not int or not 1 <= max_jobs <= 800):
            raise ValueError("max_jobs must be within 1..800")
        if not 0 < poll_seconds <= 60 or not 0 < reconcile_seconds <= 300:
            raise ValueError("Polling and reconciliation must be bounded")
        if type(targeted_diagnostics) is not bool:
            raise ValueError("Targeted diagnostics must be explicitly enabled")
        diagnostic_arguments = (target_ids, execution_timeout_seconds, quote_runtime_limit_seconds, diagnostic_reason)
        if not targeted_diagnostics and any(value is not None for value in diagnostic_arguments):
            raise ValueError("Targets and runtime overrides require explicit targeted diagnostics")
        if targeted_diagnostics:
            if (not isinstance(target_ids, (list, tuple)) or not target_ids
                    or any(not isinstance(cid, str) for cid in target_ids)
                    or len(target_ids) != len(set(target_ids))):
                raise ValueError("Targeted diagnostics require distinct explicit target IDs")
            for value in (execution_timeout_seconds, quote_runtime_limit_seconds):
                if not _money(value) or not 1 <= value <= 3600:
                    raise ValueError("Both diagnostic runtime limits must be finite and within 1..3600 seconds")
            if diagnostic_reason is not None and (not isinstance(diagnostic_reason, str) or not diagnostic_reason.strip()):
                raise ValueError("A supplied diagnostic reason must be nonempty text")
        self.adapter, self.settings = adapter, deepcopy(settings)
        self.root = Path(adapter.root)
        self.problem, self.device, self.options = problem, device, deepcopy(options)
        self.manifests = deepcopy(manifests) if manifests is not None else load_manifests()
        for p in PROBLEMS:
            ids = self.manifests[p]
            if not ids or len(ids) != len(set(ids)):
                raise ValueError("Every reservation cohort needs a nonempty distinct ID manifest")
            for cid in ids:
                if cid.split("_")[1] != p:
                    raise ValueError("Manifest problem mismatch")
                validate_action(cid, device, options)
        self.ids = self.manifests[problem]
        if targeted_diagnostics and not set(target_ids).issubset(self.ids):
            raise ValueError("Diagnostic target IDs must belong to the selected full retained manifest")
        self.targeted_diagnostics = targeted_diagnostics
        self.target_ids = ([cid for cid in self.ids if cid in target_ids] if targeted_diagnostics else list(self.ids))
        self.diagnostic_reason = (diagnostic_reason or
                "Explicit targeted diagnostic at fixed options; reserve the full quote and request cancellation at the execution cap"
                ) if targeted_diagnostics else None
        self.cohort_key = digest({"problem": problem, "device": device, "options": options})
        self.slots, self.max_jobs = slots, max_jobs or len(self.target_ids)
        self.poll_seconds, self.reconcile_seconds = poll_seconds, reconcile_seconds
        self.sleep = sleep
        self.clock = clock or (lambda: datetime.now(timezone.utc))
        self.reserve_override = deepcopy(reserve_cohorts)
        self.limit = settings["graded_budget_usd"] * (1 - fraction)
        self.timeout = settings["remote_job_seconds"]
        if device == "mps.cpu" and options.get("mps_bond_dimension") == 32:
            self.timeout = max(self.timeout, settings.get("mps_chi32_job_seconds", self.timeout))
        self.quote_runtime_limit = self.timeout
        if targeted_diagnostics:
            self.timeout = execution_timeout_seconds
            self.quote_runtime_limit = quote_runtime_limit_seconds
        self.records, self.cohorts, self.rates = {}, {}, {}
        self.reserve_quoted_at, self.observed_job_costs = {}, {}
        self.has_usable_baseline = {}
        self.launched, self.spent_floor = [], 0.0
        self.last_budget, self.blockage, self.wait_started = None, None, None
        self.last_gpu_quota = None
        self.stop_requested = False

    def _path(self, action):
        return self.root / "remote_actions" / f"{digest(action)}.json"

    def _load(self):
        self.records = {}
        for path in (self.root / "remote_actions").glob("*.json"):
            saved = json.loads(path.read_text(encoding="utf-8"))
            if digest(saved["action"]) != path.stem:
                raise ValueError("Remote receipt identity mismatch")
            self.records[path.stem] = saved
        path = self.root / "cohort_accounting.json"
        if path.exists():
            saved = json.loads(path.read_text(encoding="utf-8"))
            costs = saved.get("observed_job_costs_usd")
            floor = saved.get("actual_spent_floor_usd")
            if (saved.get("account_scope") != "current API account" or not _money(floor)
                    or not isinstance(costs, dict)
                    or any(not isinstance(jid, str) or not jid or not _money(cost)
                           for jid, cost in costs.items())
                    or floor + 1e-9 < sum(costs.values())):
                raise ValueError("Invalid durable account cost evidence")
            self.observed_job_costs = costs
            self.spent_floor = floor

    def _account_costs(self, usage):
        costs = usage.get("known_job_costs_usd")
        if (not isinstance(costs, dict)
                or any(not isinstance(jid, str) or not jid or not _money(cost)
                       for jid, cost in costs.items())):
            return "unknown_account_cost_breakdown"
        if not math.isclose(sum(costs.values()), usage["known_cost_usd"], rel_tol=1e-12, abs_tol=1e-9):
            return "inconsistent_account_cost_breakdown"
        observed = dict(self.observed_job_costs)
        for jid, cost in costs.items():
            observed[jid] = max(observed.get(jid, 0), cost)
        for record in self.records.values():
            if not _current_account(record) or not _money(record.get("cost_usd")):
                continue
            jid = record.get("job_id")
            if not isinstance(jid, str) or not jid:
                return "unknown_receipt_cost_identity"
            observed[jid] = max(observed.get(jid, 0), record["cost_usd"])
        self._persist_costs(observed)
        return None

    def _persist_costs(self, observed):
        floor = max(self.spent_floor, sum(observed.values()))
        if observed != self.observed_job_costs or floor != self.spent_floor:
            # Persist before admission. Receipts cover a crash between terminal
            # save and this journal, and per-ID maxima survive index regressions.
            journal = {
                "updated_at": self.clock().isoformat(), "account_scope": "current API account",
                "observed_job_costs_usd": observed, "actual_spent_floor_usd": floor}
            atomic_bytes(self.root / "cohort_accounting.json",
                         (json.dumps(journal, indent=2, allow_nan=False) + "\n").encode("utf-8"))
        self.observed_job_costs, self.spent_floor = observed, floor

    def _matches(self, record, problem, cohort):
        action = record["action"]
        return (action["circuit_id"] in self.manifests[problem]
                and action["device"] == cohort["device"] and action["options"] == cohort["options"])

    def _owned(self):
        return [r for r in self.records.values() if _current_account(r) and self._matches(r, self.problem,
                {"device": self.device, "options": self.options})
                and r["action"]["circuit_id"] in self.target_ids and r.get("job_id")]

    def _pending(self):
        return [r for r in self._owned() if r.get("status") not in CLOSED or not _money(r.get("cost_usd"))]

    def _save(self, record):
        # The adapter also writes the fsynced canonical audit before any launch.
        self.adapter._save(self._path(record["action"]), record)
        self.records[digest(record["action"])] = deepcopy(record)

    def _scope(self):
        return {"mode": "TARGETED_DIAGNOSTICS" if self.targeted_diagnostics else "FULL_COHORT",
                "target_ids": list(self.target_ids), "execution_timeout_seconds": self.timeout,
                "quote_runtime_limit_seconds": self.quote_runtime_limit,
                "diagnostic_reason": self.diagnostic_reason}

    def _checkpoint(self, status, reason=None):
        selected = {"device": self.device, "options": self.options}
        complete_ids = [r["action"]["circuit_id"] for r in self.records.values()
                        if self._matches(r, self.problem, selected) and _complete(r)]
        state = {"updated_at": utc_now(), "status": status, "reason": reason,
                 **self._scope(),
                 "cohort": {"problem": self.problem, **selected}, "cohort_key": self.cohort_key,
                 "slots": self.slots, "launched_job_ids": list(self.launched),
                 "pending_job_ids": [r["job_id"] for r in self._pending()],
                 "completed_rows": len(set(complete_ids)), "required_rows": len(self.ids),
                 "completed_target_rows": len(set(complete_ids) & set(self.target_ids)),
                 "required_target_rows": len(self.target_ids),
                 "budget_limit_usd": self.limit, "budget": self.last_budget,
                 "actual_spent_floor_usd": self.spent_floor,
                 "gpu_quota_admission": self.last_gpu_quota,
                 "reserve_cohorts": self.cohorts, "reserve_rates": self.rates,
                 "has_usable_baseline": self.has_usable_baseline,
                 "warning": "Quotes are nonbinding estimates; unresolved charges block new launches."}
        atomic_json(self.root / "cohort_batches" / f"{self.cohort_key}.json", state)
        owned = self._owned()
        atomic_json(self.root / "batch_status.json", {
            "updated_at": state["updated_at"], "status": status, "reason": reason,
            **self._scope(),
            "cohort": state["cohort"], "cohort_key": self.cohort_key,
            "completed_rows": state["completed_rows"], "required_rows": len(self.ids),
            "completed_target_rows": state["completed_target_rows"], "required_target_rows": len(self.target_ids),
            "gpu_quota_admission": self.last_gpu_quota,
            "last_progress_at": max((r.get("updated_at") or r.get("requested_at") or "" for r in owned), default=None),
            "owned_jobs": [{"job_id": r["job_id"], "circuit_id": r["action"]["circuit_id"],
                            "status": r.get("status"), "cost_usd": r.get("cost_usd")}
                           for r in owned],
            "source": "Bounded CPU cohort controller"})
        return state

    def _initialize_cohorts(self):
        effective, _ = recover_flat_policy(self.settings, list(self.records.values()))
        for problem in PROBLEMS:
            policy = baseline_route_policy(problem, list(self.records.values()), effective)
            self.cohorts[problem] = {"device": policy["primary"],
                                     "options": _options(policy["primary"], policy, effective)}
        if self.reserve_override is not None:
            if set(self.reserve_override) != set(PROBLEMS):
                raise ValueError("Reservation overrides must specify all G2-G4 cohorts")
            self.cohorts = deepcopy(self.reserve_override)
        self.cohorts[self.problem] = {"device": self.device, "options": deepcopy(self.options)}
        for problem, cohort in self.cohorts.items():
            if cohort["device"] not in CPU_DEVICES and not (self.gpu and problem == self.problem
                                                            and cohort["device"] == self.device):
                raise ValueError("Other reservation cohorts must use supported CPU devices")
            validate_action(self.manifests[problem][0], cohort["device"], cohort["options"])
            candidates = select_coherent_vector(list(self.records.values()), self.manifests[problem],
                                                  cohort["device"])["complete_candidates"]
            self.has_usable_baseline[problem] = any(
                max(candidate["values"]) - min(candidate["values"]) > self.settings["stopping"]["signal_floor"]
                for candidate in candidates)
        quotes = [r["quote"] for r in self.records.values() if r.get("quote")]
        for path in (self.root / "quotes").glob("*.json"):
            quotes.append(json.loads(path.read_text(encoding="utf-8")))
        # A rate is tied to the actual selected options, never a uniform row allowance.
        for problem, cohort in self.cohorts.items():
            matching = [q["cost_usd"] for q in quotes if q.get("circuit_id") in self.manifests[problem]
                        and q.get("device") == cohort["device"] and q.get("options") == cohort["options"]
                        and not q.get("error") and _money(q.get("cost_usd"))]
            self.rates[problem] = max(matching) if matching else None

    def _missing_unreserved(self, candidate=None):
        missing = {}
        for problem, cohort in self.cohorts.items():
            if self.has_usable_baseline.get(problem):
                # A complete older vector survives any unfinished refinement cohort.
                # Active/new quotes remain committed; only future coverage is exempt.
                missing[problem] = []
                continue
            covered = set()
            for record in self.records.values():
                if not self._matches(record, problem, cohort):
                    continue
                if _complete(record) or record.get("status") not in CLOSED or not _money(record.get("cost_usd")):
                    covered.add(record["action"]["circuit_id"])
            if candidate and candidate["circuit_id"] in self.manifests[problem]:
                covered.add(candidate["circuit_id"])
            missing[problem] = [cid for cid in self.manifests[problem] if cid not in covered]
        return missing

    def _usage_gate(self):
        usage = self.adapter.usage()
        if not _money(usage.get("known_cost_usd")):
            return usage, "unknown_account_cost"
        reason = self._account_costs(usage)
        if reason:
            return usage, reason
        active = usage.get("active_job_ids")
        if not isinstance(active, list) or any(not isinstance(j, str) or not j for j in active) or len(active) != len(set(active)):
            return usage, "unknown_active_job_identity"
        if usage.get("active_jobs") != len(active):
            return usage, "inconsistent_active_job_count"
        known_ids = {r["job_id"] for r in self._owned()}
        for record in self.records.values():
            if not _current_account(record):
                continue
            if record.get("status") not in CLOSED and not record.get("job_id"):
                return usage, "ambiguous_submission_intent"
            if record.get("status") not in CLOSED and record.get("job_id") not in known_ids:
                return usage, "foreign_unresolved_receipt"
            if record.get("status") in CLOSED and not _money(record.get("cost_usd")):
                return usage, "unknown_terminal_cost"
            if (record.get("job_id") in known_ids and record.get("status") in CLOSED
                    and not _complete(record)):
                return usage, "failed_target_action_requires_review"
        if set(active) - known_ids:
            return usage, "foreign_active_jobs"
        if usage.get("unknown_terminal_costs", 0):
            return usage, "unknown_terminal_cost"
        return usage, None

    def _reserve_rates(self):
        for problem, missing in self._missing_unreserved().items():
            quoted_at = self.reserve_quoted_at.get(problem)
            if missing and (quoted_at is None or (self.clock() - quoted_at).total_seconds() >= RESERVE_QUOTE_SECONDS):
                cohort = self.cohorts[problem]
                quote = self.adapter.quote(missing[0], cohort["device"], cohort["options"])
                if quote.get("error") or not _money(quote.get("cost_usd")):
                    return "missing_cohort_quote_evidence"
                self.rates[problem] = max(self.rates[problem] or 0, quote["cost_usd"])
                self.reserve_quoted_at[problem] = self.clock()
        return None

    def _next_action(self):
        for cid in self.target_ids:
            _, pauli = validate_action(cid, self.device, self.options)
            action = {"circuit_id": cid, "device": self.device, "options": deepcopy(self.options), "pauli": pauli}
            saved = self.records.get(digest(action))
            if saved is None:
                return action, None
            if saved.get("status") in CLOSED and _money(saved.get("cost_usd")) and not _complete(saved):
                return None, "failed_target_action_requires_review"
        return None, None

    def _admit(self, action):
        quote = self.adapter.quote(action["circuit_id"], self.device, self.options)
        if quote.get("error") or not _money(quote.get("cost_usd")):
            return None, "unknown_or_invalid_quote"
        runtime = quote.get("runtime_seconds")
        if not _money(runtime) or runtime > self.quote_runtime_limit:
            return None, "invalid_or_excessive_runtime"
        remaining = (datetime.fromisoformat(self.settings["deadline_utc"]) - self.clock()).total_seconds()
        if remaining < self.settings["submission_buffer_seconds"] + max(runtime, self.timeout):
            return None, "deadline_buffer"
        usage, reason = self._usage_gate()
        if reason:
            return None, reason
        inflight = {r["job_id"] for r in self._pending()} | set(usage["active_job_ids"])
        if len(inflight) >= min(self.slots, self.settings.get("account_parallel_job_limit", 5)):
            return None, "slots_full"
        if self.gpu:
            reason = self._gpu_admission(usage, runtime)
            if reason:
                return None, reason
        unindexed = len({r["job_id"] for r in self._pending()} - set(usage["active_job_ids"]))
        if usage.get("job_count", 0) + unindexed >= self.settings["max_remote_jobs"]:
            return None, "account_job_limit"
        self.rates[self.problem] = max(self.rates[self.problem] or 0, quote["cost_usd"])
        commitments = 0.0
        for record in self.records.values():
            if not _current_account(record):
                continue
            if record.get("status") not in CLOSED or not _money(record.get("cost_usd")):
                price = record.get("quote", {}).get("cost_usd")
                if not _money(price):
                    return None, "unknown_outstanding_commitment"
                commitments += price
        missing = self._missing_unreserved(action)
        if any(ids and self.rates[p] is None for p, ids in missing.items()):
            return None, "missing_cohort_quote_evidence"
        reserve = sum(len(ids) * (self.rates[p] or 0) for p, ids in missing.items())
        exposure = self.spent_floor + commitments + quote["cost_usd"] + reserve
        self.last_budget = {"actual_spent_usd": self.spent_floor, "outstanding_quote_usd": commitments,
                            "new_quote_usd": quote["cost_usd"], "missing_cohort_reserve_usd": reserve,
                            "planned_exposure_usd": exposure,
                            "missing_unreserved_rows": {p: len(ids) for p, ids in missing.items()}}
        if exposure > self.limit + 1e-9:
            return None, "budget_commitments_and_cohort_reserve"
        if (self.root / "STOP").exists():
            return None, "stop_file"
        return quote, None

    def _gpu_admission(self, usage, runtime):
        self.last_gpu_quota = None
        total, hour = usage.get("gpu_seconds"), usage.get("gpu_seconds_last_hour")
        if usage.get("gpu_time_known") is not True or not _money(total) or not _money(hour):
            return "unknown_gpu_time"
        if hour > total + 1e-9:
            return "inconsistent_gpu_time"
        # A terminal receipt missing from the account index may still be absent
        # from its GPU-time aggregate. Wait for indexing before another GPU launch.
        indexed = usage["known_job_costs_usd"]
        if any(_current_account(record) and "gpu" in record["action"]["device"]
               and record.get("status") in CLOSED and record.get("job_id") not in indexed
               for record in self.records.values()):
            return "gpu_job_accounting_pending"
        self.last_gpu_quota = {
            "actual_gpu_seconds": total, "actual_gpu_seconds_last_hour": hour,
            "reserved_quote_seconds": runtime,
            "planned_gpu_seconds": total + runtime,
            "planned_gpu_seconds_last_hour": hour + runtime,
            "gpu_total_limit_seconds": self.settings["gpu_total_seconds"],
            "gpu_hour_limit_seconds": self.settings["gpu_hour_seconds"],
            "reservation_basis": "Full fresh runtime quote; no cancellation-cap or speedup discount"}
        if total + runtime > self.settings["gpu_total_seconds"] + 1e-9:
            return "gpu_total_quota_reserve"
        if hour + runtime > self.settings["gpu_hour_seconds"] + 1e-9:
            return "gpu_rolling_hour_quota"
        return None

    def _launch(self, action, quote):
        saved = {"action": action, "status": "SUBMITTING", "requested_at": self.clock().isoformat(),
                 "quote": deepcopy(quote), "timeout_seconds": self.timeout,
                 "scheduler_justification": "Complete one explicitly selected CPU cohort with at most two reserved asynchronous jobs; no extrapolation or mixed-configuration rows",
                 "cohort_batch": {"cohort_key": self.cohort_key, "slots": self.slots,
                                  **self._scope(),
                                  "gpu_quota_at_admission": deepcopy(self.last_gpu_quota),
                                  "reserved_quote_usd": quote["cost_usd"], "budget_at_admission": deepcopy(self.last_budget)}}
        if self.targeted_diagnostics:
            saved["scheduler_justification"] = self.diagnostic_reason
        self._save(saved)
        try:
            job = self.adapter.client.run(action["circuit_id"], device=self.device, asynchronous=True,
                    pauli_sum=[(action["pauli"], 1.0)], options=deepcopy(self.options),
                    tags={"workflow": self.settings["version"], "action_key": digest(action)}, force_run=False)
        except Exception as exc:
            saved["submission_exception_type"] = type(exc).__name__
            self._save(saved)
            return "ambiguous_submission_intent"
        saved.update(job_id=job.job_id, status=job.run_status)
        self._save(saved)
        self.launched.append(job.job_id)
        # Terminal returns still pass through polling to persist actual cost before release.
        return None

    def _cancel_if_due(self, saved):
        age = (self.clock() - datetime.fromisoformat(saved["requested_at"])).total_seconds()
        timeout = saved.get("timeout_seconds", self.timeout)
        if self.targeted_diagnostics:
            # Resuming cannot relax a stricter cap recorded by the original run.
            timeout = min(timeout, self.timeout)
        expired = age >= timeout if self.targeted_diagnostics else age > timeout
        cancel = self.stop_requested or expired
        if cancel and not saved.get("cancel_requested_at"):
            saved.update(status="CANCEL_REQUESTED", cancel_requested_at=self.clock().isoformat(),
                         cancel_reason="stop_file" if self.stop_requested else "job_timeout")
            self._save(saved)
            try:
                self.adapter.client.cancel(saved["job_id"])
            except Exception as exc:
                saved["cancel_exception_type"] = type(exc).__name__
                self._save(saved)
        return saved.get("cancel_reason") if saved.get("cancel_requested_at") else None

    def _poll(self):
        problem = None
        for original in list(self._pending()):
            saved = deepcopy(original)
            try:
                job = self.adapter.client.get(saved["job_id"])
            except Exception as exc:
                problem = "job_reconciliation_unavailable"
                saved["poll_exception_type"] = type(exc).__name__
                self._save(saved)
                # STOP and deadlines still request cancellation when the read
                # endpoint is unavailable; cancellation keeps its reservation.
                if saved.get("status") not in CLOSED:
                    problem = self._cancel_if_due(saved) or problem
                continue
            if job.run_status in TERMINAL:
                cost = job.cost
                if _money(cost):
                    observed = dict(self.observed_job_costs)
                    observed[saved["job_id"]] = max(observed.get(saved["job_id"], 0), cost)
                    # Charge evidence is durable before a terminal receipt can
                    # release the reservation, even if the process dies next.
                    self._persist_costs(observed)
                saved.update(status=job.run_status, estimate=job.expectation_value, cost_usd=cost,
                             compute_ms=job.run_time_ms, queue_ms=job.queue_time_ms)
                if job.run_status == "COMPLETED" and _money(cost) and not _complete(saved):
                    saved.update(status="INVALID_RESULT", error="Invalid bounded expectation")
                if saved != original:
                    saved["updated_at"] = self.clock().isoformat()
                    self._save(saved)
                if not _money(cost):
                    problem = "unknown_terminal_cost"
                elif job.run_status != "COMPLETED" or saved["status"] == "INVALID_RESULT":
                    problem = "failed_target_action_requires_review"
                continue
            cancel_reason = self._cancel_if_due(saved)
            if cancel_reason:
                problem = cancel_reason
            elif job.run_status != saved.get("status"):
                saved.update(status=job.run_status, updated_at=self.clock().isoformat())
                self._save(saved)
        return problem

    def _run_locked(self):
        self._load()
        self._initialize_cohorts()
        while True:
            self.stop_requested = self.stop_requested or (self.root / "STOP").exists()
            poll_reason = self._poll()
            usage, reason = self._usage_gate()
            reason = reason or poll_reason
            if self.stop_requested:
                reason = "stop_file"
            pending = self._pending()
            if not pending and reason:
                return self._checkpoint("STOPPED" if self.stop_requested else "BLOCKED", reason)
            if self.spent_floor > self.limit + 1e-9:
                reason = "actual_cost_budget_limit"
            if not reason and (not self.targeted_diagnostics or self._next_action()[0] is not None):
                reason = self._reserve_rates()
            # Sequential admissions see the receipt reservation from every prior launch.
            while not reason and len(self._pending()) < self.slots and len(self.launched) < self.max_jobs:
                action, reason = self._next_action()
                if action is None or reason:
                    break
                quote, reason = self._admit(action)
                if reason:
                    break
                reason = self._launch(action, quote)
            pending = self._pending()
            self.blockage = reason
            if not pending:
                if reason:
                    return self._checkpoint("BLOCKED", reason)
                _, incomplete_reason = self._next_action()
                count = sum(_complete(r) and self._matches(r, self.problem, self.cohorts[self.problem])
                            and r["action"]["circuit_id"] in self.target_ids
                            for r in self.records.values())
                if count == len(self.target_ids):
                    return self._checkpoint("DIAGNOSTICS_COMPLETE" if self.targeted_diagnostics else "COMPLETE")
                if len(self.launched) >= self.max_jobs:
                    return self._checkpoint("BOUNDED_STOP", "max_jobs_reached")
                return self._checkpoint("BLOCKED", incomplete_reason or "no_admissible_action")
            # Ambiguity/unknown costs/cancellation are reconciled for a bounded interval;
            # reservations remain on disk if service state cannot be established.
            transient = reason in {"ambiguous_submission_intent", "unknown_terminal_cost", "job_reconciliation_unavailable",
                                   "stop_file", "job_timeout", "cancellation_pending"}
            if transient:
                self.wait_started = self.wait_started or self.clock()
                if (self.clock() - self.wait_started).total_seconds() >= self.reconcile_seconds:
                    return self._checkpoint("BLOCKED", reason + "_reconciliation_pending")
            else:
                self.wait_started = None
            self._checkpoint("DRAINING" if reason else "RUNNING", reason)
            self.sleep(self.poll_seconds)

    def run(self):
        with ExperimentStore(self.root).lock("remote_runner"):
            try:
                return self._run_locked()
            except Exception as exc:
                # Do not print SDK exception bodies, which may contain sensitive data.
                return self._checkpoint("BLOCKED", "controller_exception:" + type(exc).__name__)


def run_cohort_batch(adapter, settings, problem, device, options, **kwargs):
    return CohortBatchController(adapter, settings, problem, device, options, **kwargs).run()
