"""Run the version-zero loop on released samples, with no cloud spending."""

from collections import defaultdict
from datetime import datetime, timezone
import csv
import hashlib
import io
import json
import os
from pathlib import Path
import statistics
import time

import numpy as np

from bluequbit_samples.analysis import correlation_score
from bluequbit_samples.inputs import discover_samples
from bluequbit_samples.models import RunConfig
from bluequbit_samples.provenance import atomic_json, source_sha256
from bluequbit_samples.runtime import execute
from .adaptive import priority, stopping_diagnostic, vector_comparison
from .duke_submission import build_submission, write_submission
from .experiment_store import digest, utc_now


def load_settings(path="configs/workflow_v0.json"):
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if value["sample_budget_usd"] != 0 or not 0 <= value["graded_budget_usd"] <= 30:
        raise ValueError("Samples must remain free; graded budget must be within the authorized $30")
    if not value["stop_on_unknown_cost"] or value["max_concurrent_jobs"] != 1:
        raise ValueError("This runner requires known costs and serial execution")
    if min(value["pps_thresholds"]) < 1e-5:
        raise ValueError("Workflow PPS thresholds must be at least 1e-5")
    # Team rule: lifetime account spend <= $20 per teammate (override via BQ_ACCOUNT_CAP_USD).
    value.setdefault("account_cap_usd", float(os.environ.get("BQ_ACCOUNT_CAP_USD", "20")))
    return value


def sample_inputs():
    report = discover_samples("problems", 50)
    if not report.ready:
        raise ValueError(report.issues)
    return report.samples


def recover_local_receipts(store):
    """Recover completed workers if a controller stopped before indexing results."""
    known = {i["record"].get("diagnostics",{}).get("attempt_directory") for i in store.records()}
    for path in (store.root / "local/attempts").glob("*/record.json"):
        record = json.loads(path.read_text())
        d = record["diagnostics"]
        if d.get("attempt_directory") in known:
            continue
        request = json.loads(path.with_name("request.json").read_text())
        record["cost_usd"] = 0.0
        store.save({"circuit_id":record["circuit_id"],"method":record["method"],
                    "parameters":request["parameters"],"input_sha256":record["qasm_sha256"],
                    "engine_source":d["source_sha256"],"origin":"local"},record)


def import_references(store, path="results/calibration/references/current_records.json"):
    samples = {s.circuit_id:s for s in sample_inputs()}
    count = 0
    for record in json.loads(Path(path).read_text(encoding="utf-8")):
        sample = samples.get(record["circuit_id"])
        if (sample is None or sample.qasm_sha256 != record["qasm_sha256"] or
                record["method"] != "exact" or record["status"] != "SUCCEEDED"):
            raise ValueError("Reference input identity or execution status is invalid")
        record["cost_usd"] = 0.0
        store.save({"circuit_id":sample.circuit_id, "method":"exact", "parameters":{},
                    "input_sha256":sample.qasm_sha256, "origin":"local_exact_reference",
                    "engine_source":record["diagnostics"]["source_sha256"]}, record)
        count += 1
    return count


def _precision(record):
    if record["method"] == "mps":
        return record["parameters"]["chi"]
    if record["method"] == "pps_threshold":
        return -record["parameters"]["epsilon"]
    return 0


def histories(items):
    latest = {}
    for item in sorted(items, key=lambda x:x["saved_at"]):
        record = item["record"]
        if record["status"] != "SUCCEEDED" or record.get("estimate") is None:
            continue  # A later failed retry cannot erase a valid earlier estimate.
        signature = (record["circuit_id"], record["method"], json.dumps(record["parameters"],sort_keys=True))
        latest[signature] = record
    result = defaultdict(list)
    for record in latest.values():
        if record["status"] == "SUCCEEDED" and record.get("estimate") is not None:
            result[(record["circuit_id"],record["method"])].append(record)
    for series in result.values():
        series.sort(key=_precision)
    return result


def diagnostics(samples, items, settings):
    history = histories(items)
    result = {}
    for problem in sorted({s.sample for s in samples}):
        group = [s for s in samples if s.sample == problem]
        steps, current = [], {}
        for method in ("mps","pps_threshold"):
            series = [history[(s.circuit_id,method)] for s in group]
            if all(series):
                current[method] = [h[-1]["estimate"] for h in series]
            if all(len(h) >= 2 for h in series):
                steps.append(vector_comparison([h[-1]["estimate"] for h in series],
                                               [h[-2]["estimate"] for h in series],settings["signal_floor"]))
        if len(current) == 2:
            steps.append(vector_comparison(current["mps"],current["pps_threshold"],settings["signal_floor"]))
        shape_ready = len(steps) == 3 and all(s["signal_resolved"] for s in steps)
        shape = max(s["shape_change"] for s in steps) if shape_ready else None
        values = np.asarray(current.get("mps", current.get("pps_threshold",[0.])))
        scale = max(float(np.median(np.abs(values-np.median(values)))),settings["scale_floor"])
        for sample in group:
            mh, ph = history[(sample.circuit_id,"mps")],history[(sample.circuit_id,"pps_threshold")]
            result[sample.circuit_id] = stopping_diagnostic([r["estimate"] for r in mh],
                    [r["estimate"] for r in ph],scale,settings,shape,shape_ready)
    return result


def run_local(store, settings, selected=("S1","S2","S3"), max_jobs=100, seconds=900):
    all_samples = sample_inputs()
    samples = [s for s in all_samples if s.sample in selected]
    config = RunConfig(cpu_threads=settings["cpu_threads"], memory_limit_mb=settings["memory_limit_mb"],
                       walltime_seconds=settings["per_job_seconds"], max_paulis=settings["max_paulis"])
    started, completed = time.monotonic(), 0
    code_hash = source_sha256()
    with store.lock():
        while completed < max_jobs and time.monotonic()-started < seconds:
            if (store.root / "STOP").exists():
                break
            deadline = datetime.fromisoformat(settings["deadline_utc"])
            if (deadline-datetime.now(timezone.utc)).total_seconds() < settings["submission_buffer_seconds"]:
                break
            items = store.records()
            active = [i for i in items if i["key"] not in settings.get("excluded_record_keys",[])]
            hist = histories(active)
            quality = diagnostics(samples,active,settings["stopping"])
            # Preserve validated results across operational fixes; invalidate a specific
            # record explicitly when a solver change affects its numerical validity.
            attempted = {digest({k:v for k,v in i["action"].items() if k != "engine_source"}) for i in active}
            failures = defaultdict(int)
            times = defaultdict(list)
            for item in active:
                record = item["record"]
                group = (record["sample"],record["method"])
                times[group].append(record["wall_seconds"])
                if record["status"] != "SUCCEEDED":
                    failures[group] += 1
            candidates = []
            for sample in samples:
                diag = quality[sample.circuit_id]
                # Provisional diagnostics are recorded, but cannot stop calibration early.
                if diag["stop"] and settings["stopping"]["status"] == "CALIBRATED":
                    continue
                for method in ("mps","pps_threshold"):
                    if failures[(sample.sample,method)] >= settings["failure_limit_per_problem_method"]:
                        continue
                    grid = ([{"chi":c} for c in settings["mps_chis"][sample.sample]] if method == "mps" else
                            [{"epsilon":e,"level":settings["local_pps_transpilation_level"]} for e in settings["pps_thresholds"]])
                    for parameters in grid:
                        action = {"circuit_id":sample.circuit_id,"method":method,"parameters":parameters,
                                  "input_sha256":sample.qasm_sha256,"engine_source":code_hash,"origin":"local"}
                        if digest({k:v for k,v in action.items() if k != "engine_source"}) in attempted:
                            continue
                        elapsed = statistics.median(times[(sample.sample,method)]) if times[(sample.sample,method)] else 5.0
                        branches = [hist[(sample.circuit_id,m)] for m in ("mps","pps_threshold")]
                        score = priority(100,diag["uncertainty"],elapsed,uncovered=not any(branches),
                                         missing_branch=not hist[(sample.circuit_id,method)])
                        # Round-robin precision coverage before refining an already deep history.
                        score /= 1 + len(hist[(sample.circuit_id,method)])
                        candidates.append((score,sample,method,parameters,action))
                        break
            if not candidates:
                break
            _, sample, method, parameters, action = max(candidates,key=lambda c:c[0])
            atomic_json(store.root / "status.json",{"status":"RUNNING","action":action,"completed_this_run":completed,
                                                       "updated_at":utc_now(),"sample_spend_usd":0.0})
            record = execute(sample,method,parameters,config,store.root / "local")
            payload = record.to_dict()
            payload["cost_usd"] = 0.0
            store.save(action,payload)
            completed += 1
            print(f"[{completed}] {sample.circuit_id} {method} {parameters}: {record.status}; "
                  f"value={record.estimate}; wall={record.wall_seconds:.2f}s",flush=True)
            write_report(store,settings,all_samples)
        atomic_json(store.root / "status.json",{"status":"IDLE","completed_this_run":completed,
                                                 "updated_at":utc_now(),"sample_spend_usd":0.0})
    return completed


def write_report(store, settings, samples=None):
    samples, items = samples or sample_inputs(), store.records()
    by_id = {s.circuit_id:s for s in samples}
    hist = histories(items)
    references = {cid:h[-1]["estimate"] for (cid,method),h in hist.items() if method == "exact" and h}
    grouped = defaultdict(dict)
    for (_,method), records in hist.items():
        for record in records:
            grouped[(record["sample"],method,json.dumps(record["parameters"],sort_keys=True))][record["circuit_id"]] = record
    benchmarks = []
    for (problem,method,param_json), records in sorted(grouped.items()):
        group = [s for s in samples if s.sample == problem]
        complete = set(records) == {s.circuit_id for s in group}
        row = {"problem":problem,"method":method,"parameters":json.loads(param_json),
               "completed":len(records),"required":len(group),"complete":complete,
               "wall_seconds":sum(r["wall_seconds"] for r in records.values()),"cost_usd":0.0,
               "local_score":None,"mae":None,"max_absolute_error":None}
        if complete:
            values = [records[s.circuit_id]["estimate"] for s in group]
            if all(s.circuit_id in references for s in group):
                exact = [references[s.circuit_id] for s in group]
                _, row["local_score"], _ = correlation_score(values,exact)
                errors = np.abs(np.asarray(values)-np.asarray(exact))
                row.update(mae=float(errors.mean()),max_absolute_error=float(errors.max()))
            identity = digest({"problem":problem,"method":method,"parameters":row["parameters"],"values":values})[:12]
            target = store.root / "submissions" / problem / f"{method}-{identity}.csv"
            buffer = io.StringIO(newline="")
            writer = csv.writer(buffer,lineterminator="\n")
            writer.writerow(("circuit_id","value"))
            writer.writerows((s.circuit_id,format(v,".17g")) for s,v in zip(group,values))
            payload = buffer.getvalue().encode()
            write_submission(payload,target,immutable=True)
            template = next(Path("problems").glob(f"*_sample_{problem}/local_submission_template.csv"))
            if build_submission(template,target) != payload:
                raise ValueError("Export failed round-trip validation")
            backend_names = sorted({r["backend"] for r in records.values()})
            implementation = ("BlueQubit exact CPU simulation by public sample ID" if backend_names == ["bluequbit.cpu"] else
                              "Local Qiskit Aer statevector simulation" if method == "exact" else
                              "Local Quimb matrix-product-state simulation" if method == "mps" else
                              "Local coefficient-cutoff Pauli propagation")
            note = (f"{implementation}, separately for every ID, starting in |0...0>. "
                    f"Computed Pauli Z on the qubit named by each ID; q0 is the rightmost Pauli character. "
                    f"Parameters: {param_json}. No shot sampling or score-derived labels. "
                    + ("Merged identical Pauli strings before each cutoff; summed I/Z-only terms on the initial state. "
                       "Independent implementation with Qiskit transpilation, not the BlueQubit PPS backend. "
                       if method == "pps_threshold" else "") + "BlueQubit compute cost: $0.")
            target.with_suffix(".txt").write_text(note+"\n",encoding="utf-8")
            row.update(csv_path=str(target.resolve()),sha256=hashlib.sha256(payload).hexdigest(),
                       submission_eligible=bool(np.ptp(values)>settings["stopping"]["signal_floor"]))
        benchmarks.append(row)
    report = {"updated_at":utc_now(),"benchmarks":benchmarks,"diagnostics":diagnostics(samples,items,settings["stopping"]),
              "record_count":len(items),"sample_cost_usd":0.0,"reference_count":len(references),
              "calibration_scope":"Local implementations. Cloud precision transfer requires separate verification."}
    atomic_json(store.root / "report.json",report)
    return report
