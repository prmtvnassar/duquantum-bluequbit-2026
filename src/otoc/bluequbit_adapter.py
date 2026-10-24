"""By-ID cloud jobs with quotation, accounting, and restart-safe submission.

The SDK's low-level estimate-only helper is used because its high-level estimate
method cannot include precision options. Unknown quotes fail closed.
"""

from datetime import datetime, timezone, timedelta
import math
from pathlib import Path
import time
import json

from bluequbit_samples.provenance import atomic_json
from .config import get_client
from .experiment_store import digest, utc_now
from .ledger import DEFAULT_ROOT, REPO, event, record_remote


START = "2026-10-24T15:30:00+00:00"
SIZES = {"S1":4,"S2":16,"S3":30,"G1":30,"G2":36,"G3":36,"G4":38}
TERMINAL = {"COMPLETED","FAILED_VALIDATION","TERMINATED","CANCELED","NOT_ENOUGH_FUNDS",
            "JOBS_LIMIT_EXCEEDED","HACKATHON_PARALLEL_JOBS_LIMIT","HACKATHON_GPU_QUOTA_COOLDOWN"}


def validate_action(circuit_id, device, options):
    parts = circuit_id.split("_")
    if len(parts) != 3 or parts[0] != "Duke" or parts[1] not in SIZES:
        raise ValueError("Unknown challenge ID")
    q = int(parts[2])
    n = SIZES[parts[1]]
    if not 0 <= q < n or str(q) != parts[2]:
        raise ValueError("Invalid target qubit")
    if device not in {"cpu","gpu","mps.cpu","mps.gpu","pauli-path","pauli-path.gpu"}:
        raise ValueError("Unsupported challenge device")
    if device.startswith("mps") and (not isinstance(options.get("mps_bond_dimension"),int) or options["mps_bond_dimension"] < 1):
        raise ValueError("An explicit MPS bond dimension is required")
    if device.startswith("pauli-path"):
        threshold = options.get("pauli_path_truncation_threshold")
        if threshold is None or not math.isfinite(threshold) or threshold < 1e-5:
            raise ValueError("PPS requires an explicit finite threshold of at least 1e-5")
        if options.get("pauli_path_circuit_transpilation_level",2) not in (0,1,2,3):
            raise ValueError("Invalid PPS transpilation level")
    return parts[1], "I"*(n-1-q)+"Z"+"I"*q


def cost_gate(problem, quote, usage, settings, justification=""):
    cost = quote.get("cost_usd")
    if quote.get("error") or cost is None or not math.isfinite(cost) or cost < 0:
        return False, "unknown_or_invalid_quote"
    if usage.get("unknown_terminal_costs",0):
        return False, "unreconciled_job_costs"
    if usage.get("active_jobs",0):
        return False, "another_cloud_job_is_active"
    if "gpu" in quote.get("device",""):
        if not usage.get("gpu_time_known",False):
            return False,"unreconciled_gpu_time"
        seconds=quote.get("runtime_seconds")
        if seconds is None or seconds+usage.get("gpu_seconds",0)>settings.get("gpu_total_seconds",27000):
            return False,"gpu_total_quota_reserve"
        if seconds+usage.get("gpu_seconds_last_hour",0)>settings.get("gpu_hour_seconds",2700):
            return False,"gpu_rolling_hour_quota"
    if usage.get("job_count",0) >= settings["max_remote_jobs"]:
        return False, "job_limit_reserve"
    if problem.startswith("S"):
        return (cost == 0, "free_sample" if cost == 0 else "sample_budget_is_zero")
    if not justification.strip():
        return False, "graded_action_needs_scheduler_justification"
    available = settings["graded_budget_usd"]*(1-settings["graded_reserve_fraction"])-usage["known_cost_usd"]
    available -= settings.get("protected_baseline_usd",0)
    return (cost <= available, "within_graded_budget" if cost <= available else "graded_budget_reserve")


class BlueQubitAdapter:
    def __init__(self, root="results/workflow", client=None):
        self.root = Path(root)
        self.root.mkdir(parents=True,exist_ok=True)
        self.client = client or get_client()
        if self.root.resolve()==REPO / "results/workflow":
            for receipt in (DEFAULT_ROOT / "records").glob("remote-*.json"):
                saved=json.loads(receipt.read_text()).get("remote_receipt")
                if saved:
                    path=self.root / "remote_actions" / f"{digest(saved['action'])}.json"
                    if not path.exists():
                        atomic_json(path,saved)

    def _save(self, path, saved):
        atomic_json(path, saved)
        record_remote(saved)
        atomic_json(self.root / "remote_status.json", {
            "updated_at": utc_now(),
            "status": saved["status"],
            "circuit_id": saved["action"]["circuit_id"],
            "device": saved["action"]["device"],
            "job_id": saved.get("job_id"),
            "requested_at": saved.get("requested_at"),
            "cost_usd": saved.get("cost_usd"),
            "source": "BlueQubit SDK job receipt",
        })

    def usage(self):
        # SDK 0.19's search raises TypeError on a valid empty data:null response.
        # Read the same endpoint, accepting null only when total_count is zero.
        jobs, offset = [], 0
        while True:
            response = self.client._backend_connection.send_request(req_type="GET",path="/jobs",
                       params={"limit":100,"offset":offset,"created_later_than":START}).json()
            data = response.get("data")
            if data is None and response.get("total_count") == 0:
                data = []
            if not isinstance(data,list):
                raise RuntimeError("Account usage is unavailable; no jobs may be submitted")
            jobs.extend(data)
            if len(data)<100:
                break
            offset += len(data)
        costs = [float(j["cost"])/100 for j in jobs if j.get("cost") is not None]
        gpu_seconds,gpu_hour,gpu_known=0.,0.,True
        hour=datetime.now(timezone.utc)-timedelta(hours=1)
        from dateutil.parser import isoparse
        for job in jobs:
            if "gpu" not in (job.get("device") or ""):
                continue
            try:
                start,end=isoparse(job["run_start"]),isoparse(job["run_end"])
                gpu_seconds+=max(0,(end-start).total_seconds())
                gpu_hour+=max(0,(end-max(start,hour)).total_seconds())
            except (ValueError,TypeError,KeyError):
                gpu_known=False
        value = {"observed_at":utc_now(),"source":"BlueQubit job API","job_count":len(jobs),
                 "known_cost_usd":sum(costs),"active_jobs":sum(j.get("run_status") not in TERMINAL for j in jobs),
                 "gpu_time_known":gpu_known,"gpu_seconds":gpu_seconds,"gpu_seconds_last_hour":gpu_hour,
                 "unknown_terminal_costs":sum(j.get("run_status") in TERMINAL and j.get("cost") is None for j in jobs)}
        atomic_json(self.root / "api_usage.json",value)
        return value

    def quote(self,circuit_id,device,options):
        from bluequbit.api.jobs import submit_jobs
        _, z = validate_action(circuit_id,device,options)
        try:
            result = submit_jobs(self.client._backend_connection,circuit_id,device,
                                 pauli_sum=[(z,1.0)],options=options,estimate_only=True,force_run=False)
        except Exception as exc:
            result={"error_message":"Quote failed: "+type(exc).__name__}
        raw_cost = result.get("estimated_cost")
        quote = {"circuit_id":circuit_id,"device":device,"options":options,"quoted_at":utc_now(),
                 "cost_usd":None if raw_cost is None else float(raw_cost)/100,
                 "runtime_seconds":None if result.get("estimate_ms") is None else float(result["estimate_ms"])/1000,
                 "error":result.get("error_message"),"warning":result.get("warning_message"),
                 "binding_cost_cap":False}
        atomic_json(self.root / "quotes" / f"{digest([circuit_id,device,options])}.json",quote)
        event("quote", quote)
        return quote

    def quote_for_plan(self,circuit_id,device,options):
        path=self.root / "quotes" / f"{digest([circuit_id,device,options])}.json"
        if path.exists():
            saved=json.loads(path.read_text())
            age=(datetime.now(timezone.utc)-datetime.fromisoformat(saved["quoted_at"])).total_seconds()
            if age<=300:
                return saved  # Scheduling only; run() always obtains a fresh quote.
        return self.quote(circuit_id,device,options)

    def run(self,circuit_id,device,options,settings,justification=""):
        problem,z = validate_action(circuit_id,device,options)
        action = {"circuit_id":circuit_id,"device":device,"options":options,"pauli":z}
        key = digest(action)
        path = self.root / "remote_actions" / f"{key}.json"
        if path.exists():
            saved = json.loads(path.read_text())
            if saved["status"] in TERMINAL:
                record_remote(saved)
                event("remote_reuse", {"action_key":key,"job_id":saved.get("job_id"),"status":saved["status"]})
                return saved
            if not saved.get("job_id"):
                raise RuntimeError("Previous submission has uncertain status; reconcile it before resubmitting")
            job = self.client.get(saved["job_id"])
        else:
            if (self.root / "STOP").exists():
                event("blocked_action", {"action":action,"reason":"stop_file"})
                return {"status":"BLOCKED_STOP"}
            usage, quote = self.usage(), self.quote(circuit_id,device,options)
            allowed, reason = cost_gate(problem,quote,usage,settings,justification)
            if not allowed:
                event("blocked_action", {"action":action,"reason":reason,"quote":quote})
                return {"status":"BLOCKED_COST_POLICY","reason":reason,"quote":quote}
            runtime = quote.get("runtime_seconds")
            if runtime is None or not math.isfinite(runtime) or runtime < 0 or runtime > settings["per_job_seconds"]:
                event("blocked_action", {"action":action,"reason":"invalid_or_excessive_runtime","quote":quote})
                return {"status":"BLOCKED_RUNTIME","quote":quote}
            remaining = (datetime.fromisoformat(settings["deadline_utc"])-datetime.now(timezone.utc)).total_seconds()
            if remaining < settings["submission_buffer_seconds"] + (quote["runtime_seconds"] or 600):
                event("blocked_action", {"action":action,"reason":"deadline"})
                return {"status":"BLOCKED_DEADLINE"}
            saved = {"action":action,"status":"SUBMITTING","requested_at":utc_now(),"quote":quote,
                     "scheduler_justification":justification}
            self._save(path,saved)
            # No automatic resubmission after a network exception: SUBMITTING stays on disk.
            job = self.client.run(circuit_id,device=device,asynchronous=True,pauli_sum=[(z,1.0)],
                                  options=options,tags={"workflow":settings["version"],"action_key":key},force_run=False)
            saved.update(job_id=job.job_id,status=job.run_status)
            self._save(path,saved)
        started = time.monotonic()
        while job.run_status not in TERMINAL:
            age=(datetime.now(timezone.utc)-datetime.fromisoformat(saved["requested_at"])).total_seconds()
            if (self.root / "STOP").exists() or max(age,time.monotonic()-started) > settings["per_job_seconds"]:
                self.client.cancel(job.job_id)
                saved.update(status="CANCEL_REQUESTED",updated_at=utc_now())
                self._save(path,saved)
                return saved
            if problem.startswith("S") and job.estimated_cost not in (None,0):
                self.client.cancel(job.job_id)
                atomic_json(self.root / "cost_alert.json",{"reason":"sample_quote_changed","job_id":job.job_id})
                saved.update(status="CANCEL_REQUESTED",updated_at=utc_now())
                self._save(path,saved)
                return saved
            time.sleep(3)
            job = self.client.get(job.job_id)
            if job.run_status != saved["status"] and job.run_status not in TERMINAL:
                saved.update(status=job.run_status, updated_at=utc_now())
                self._save(path, saved)
        saved.update(status=job.run_status,estimate=job.expectation_value,cost_usd=job.cost,
                     compute_ms=job.run_time_ms,queue_ms=job.queue_time_ms,updated_at=utc_now())
        self._save(path,saved)
        if job.cost is None or (problem.startswith("S") and job.cost != 0):
            (self.root / "STOP").write_text("Unreconciled or unexpected cloud cost",encoding="utf-8")
        usage = self.usage()
        if usage["known_cost_usd"] > settings["graded_budget_usd"]*(1-settings["graded_reserve_fraction"]):
            (self.root / "STOP").write_text("Campaign reserve reached; preserve budget",encoding="utf-8")
        if job.run_status == "COMPLETED" and (job.expectation_value is None or
                not math.isfinite(float(job.expectation_value)) or abs(float(job.expectation_value))>1+1e-8):
            saved.update(status="INVALID_RESULT",error="Completed job has no valid bounded expectation")
            self._save(path,saved)
        return saved
