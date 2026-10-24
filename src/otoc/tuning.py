"""Calibrate method allocation, fusion gates, and stopping evidence on samples."""

from copy import deepcopy
import json
from pathlib import Path
import numpy as np

from bluequbit_samples.analysis import correlation_score
from bluequbit_samples.provenance import atomic_json
from .calibration import histories, sample_inputs, write_report
from .experiment_store import utc_now
from .adaptive import stopping_diagnostic, vector_comparison, trend_diagnostic


def replay_stopping(group, history, truth, settings):
    """Check every complete coarse-to-fine prefix, not just the final plateau."""
    series = {}
    for method in ("mps", "pps_threshold"):
        rows = [history[(s.circuit_id, method)] for s in group]
        common = set.intersection(*({json.dumps(r["parameters"],sort_keys=True) for r in h} for h in rows))
        parameter = "chi" if method == "mps" else "epsilon"
        levels = sorted(common, key=lambda p:json.loads(p)[parameter], reverse=method=="pps_threshold")
        series[method] = [[next(r["estimate"] for r in h if json.dumps(r["parameters"],sort_keys=True)==level)
                           for h in rows] for level in levels]
    prefixes = []
    for mi in range(3, len(series["mps"])+1):
        for pi in range(3, len(series["pps_threshold"])+1):
            m, p = np.array(series["mps"][:mi]), np.array(series["pps_threshold"][:pi])
            comparisons = [vector_comparison(m[-1],m[-2],settings["signal_floor"]),
                           vector_comparison(p[-1],p[-2],settings["signal_floor"]),
                           vector_comparison(m[-1],p[-1],settings["signal_floor"])]
            resolved = all(c["signal_resolved"] for c in comparisons)
            shape = max(c["shape_change"] for c in comparisons) if resolved else None
            scale = max(float(np.median(np.abs(m[-1]-np.median(m[-1])))),settings["scale_floor"])
            checks = []
            for q, sample in enumerate(group):
                d = stopping_diagnostic(m[:,q],p[:,q],scale,settings,shape,resolved)
                error = float(max(abs(m[-1,q]-truth[q]),abs(p[-1,q]-truth[q])))
                checks.append({"circuit_id":sample.circuit_id,"would_stop":d["stop"],
                               "actual_max_branch_error":error,
                               "false_stop":d["stop"] and error>settings["target_absolute_error"]})
            prefixes.append({"mps_levels":mi,"pps_levels":pi,"checks":checks,
                             "stopped_count":sum(c["would_stop"] for c in checks),
                             "false_stops":sum(c["false_stop"] for c in checks)})
    return {"status":"EVALUATED" if prefixes else "INSUFFICIENT_COMPLETE_HISTORIES",
            "prefixes":prefixes,"stopped_count":sum(p["stopped_count"] for p in prefixes),
            "false_stops":sum(p["false_stops"] for p in prefixes)}


def tune(store, settings):
    report=write_report(store,settings)
    history=histories(store.records())
    samples=sample_inputs()
    by_problem={p:[s for s in samples if s.sample==p] for p in ("S1","S2","S3")}
    truth={}
    for problem,group in by_problem.items():
        rows=[history[(s.circuit_id,"exact")] for s in group]
        if all(rows):
            truth[problem]=np.array([r[-1]["estimate"] for r in rows])
    recommendations={}
    for problem in by_problem:
        options=[b for b in report["benchmarks"] if b["problem"]==problem and b["method"]!="exact"
                 and b["complete"] and b["max_absolute_error"] is not None]
        accepted=[b for b in options if b["local_score"]>=100*settings["stopping"]["target_score_fraction"]
                  and b["max_absolute_error"]<=settings["stopping"]["target_absolute_error"]]
        if accepted:
            chosen=min(accepted,key=lambda b:b["wall_seconds"])
            recommendations[problem]={"status":"VALIDATED_LOCAL",**{k:chosen[k] for k in
                ("method","parameters","local_score","mae","max_absolute_error","wall_seconds")}}
        elif options:
            chosen=min(options,key=lambda b:(b["max_absolute_error"],-b["local_score"]))
            recommendations[problem]={"status":"TARGET_NOT_YET_MET",**{k:chosen[k] for k in
                ("method","parameters","local_score","mae","max_absolute_error","wall_seconds")}}
        else:
            recommendations[problem]={"status":"REFERENCE_OR_COVERAGE_INCOMPLETE"}

    # Two complete refinement steps in each branch, plus vector-shape and cross checks.
    # Assess both estimates against truth, so a shared bias cannot pass the calibration gate.
    stop_checks=[]
    for problem,group in by_problem.items():
        if problem not in truth:
            continue
        stop_checks.append({"problem":problem,**replay_stopping(group,history,truth[problem],settings["stopping"])})

    # Leave one entire circuit out when considering a single fusion weight.
    vectors={}
    for problem,group in by_problem.items():
        if problem in truth and all(history[(s.circuit_id,m)] for s in group for m in ("mps","pps_threshold")):
            vectors[problem]={m:np.array([history[(s.circuit_id,m)][-1]["estimate"] for s in group])
                              for m in ("mps","pps_threshold")}
    folds=[]
    if len(vectors)>=2:
        for held_out in vectors:
            train=[p for p in vectors if p!=held_out]
            def mean_score(weight,problems):
                return float(np.mean([correlation_score(weight*vectors[p]["mps"]+(1-weight)*vectors[p]["pps_threshold"],truth[p])[1]
                                      for p in problems]))
            # Prefer an endpoint in a score tie: fusion has to improve on direct estimates.
            weights=[0.,1.,0.25,0.5,0.75]
            weight=max(weights,key=lambda w:round(mean_score(w,train),10))
            anchor=max([0.,1.],key=lambda w:round(mean_score(w,train),10))
            held_score=mean_score(weight,[held_out])
            anchor_score=mean_score(anchor,[held_out])
            folds.append({"held_out":held_out,"trained_weight_mps":weight,"anchor_weight_mps":anchor,
                          "held_out_score":held_score,"anchor_score":anchor_score,
                          "gain":held_score-anchor_score})
    fusion_gate=bool(len(folds)==3 and all(f["gain"]>=-1e-6 for f in folds) and np.mean([f["gain"] for f in folds])>0.1)
    enable_fusion=False  # Native transfer and G4-family validation are unavailable.
    calibrated=deepcopy(settings)
    calibrated["local_recommendations"]=recommendations
    calibrated["fusion"].update(enabled=enable_fusion,reason="LOCO evidence" if enable_fusion else "No demonstrated consistent LOCO gain over direct estimates")
    # Optional extrapolation remains disabled until its separate held-out precision gate passes.
    evaluated=[c for c in stop_checks if c["status"]=="EVALUATED"]
    supported=bool(len(evaluated)==3 and all(c["stopped_count"]>0 and c["false_stops"]==0 for c in evaluated))
    calibrated["stopping"]["status"]="LOCAL_REPLAY_SUPPORTED" if supported else "LOCAL_DIAGNOSTICS_ONLY"
    calibrated["stopping"]["automatic_native_stop"]=False
    calibrated["cloud_transfer"]={"verified":False,"reason":"Native MPS/PPS sample quotes were $0.20; sample spending is prohibited",
                                  "required":"Native precision pilots on graded IDs within the authorized budget"}
    mps_chi=int(recommendations.get("S2",{}).get("parameters",{}).get("chi",256))
    pps_epsilon=float(recommendations.get("S3",{}).get("parameters",{}).get("epsilon",.0001))
    calibrated["version"]="workflow-final-1"
    calibrated["release_status"]=("READY" if len(truth)==3 and all(
        recommendations[p].get("status")=="VALIDATED_LOCAL" for p in by_problem)
        else "DRAFT_PENDING_SAMPLE_EVIDENCE")
    calibrated["remote_job_seconds"]=600
    calibrated["exact_job_seconds"]=600
    calibrated["baseline_quote_reserve_usd_per_row"]=.20
    calibrated["maximum_native_chi"]=512
    calibrated["gpu_enabled"]=True
    calibrated["gpu_total_seconds"]=27000
    calibrated["gpu_hour_seconds"]=2700
    calibrated["account_parallel_job_limit"]=5
    calibrated["scheduler_concurrency_reason"]="Serial execution protects budget accounting; imported exact G1 avoids repeating its 30 jobs"
    calibrated["pilot_qubits"]={"G1":[0,15,29],"G2":[0,18,35],"G3":[0,14,35],"G4":[0,19,37]}
    quotes=[json.loads(p.read_text()) for p in (store.root/"quotes").glob("*.json")]
    def quoted(cid,device,options):
        matches=[q for q in quotes if q["circuit_id"]==cid and q["device"]==device and q["options"]==options]
        return max(matches,key=lambda q:q["quoted_at"]) if matches else None
    desired=quoted("Duke_G2_0","mps.cpu",{"mps_bond_dimension":mps_chi})
    affordable=bool(desired and desired.get("cost_usd") is not None and desired["cost_usd"]<=.2
                    and desired.get("runtime_seconds") is not None and desired["runtime_seconds"]<=600)
    calibrated["graded_policy"]={
        "G1":{"primary":"cpu","fallback":"mps.cpu","chi":mps_chi,"reason":"Free exact CPU first; S2-calibrated MPS fallback if exact cannot complete"},
        "G2":{"primary":"mps.cpu" if affordable else "pauli-path","chi":mps_chi if affordable else 16,
              "epsilon":.001,"desired_mps_chi":mps_chi,"quality":"LOCAL_TARGET_MET" if affordable else "BUDGET_COMPROMISE",
              "reason":"S2 high-accuracy MPS is preferred, but live native quotes determine feasibility. PPS .001 is the affordable fallback; its S2 error exceeds the 0.01 target"},
        "G3":{"primary":"pauli-path","epsilon":pps_epsilon,"chi":16,
              "reason":"Mostly Clifford grid analogue S3; native transpilation differs; chi16 is an affordable independent pilot only"},
        "G4":{"primary":"pauli-path","chi":16,"epsilon":.001,"quality":"UNMATCHED_FAMILY",
              "reason":"Native MPS chi64 CPU/GPU quotes exceed the runtime/budget allocation. Use cheap PPS pilots and independent MPS chi16; neither has a matched G4 sample"}}
    calibrated["pilot_signal_gate"]=True
    imported=Path("runs/imports/kevin/g1_exact_actions.json")
    if imported.exists():
        source=json.loads(imported.read_text())
        calibrated["completed_anchors"]={"G1":{"status":"EXACT_REUSED","rows":len(source["records"]),
                                                   "source_commit":source["source_commit"]}}
    calibrated["quote_evidence"]={"G2_desired_mps":desired,"scope":"Representative ID only; every execution is freshly quoted"}
    atomic_json("reports/native_quotes.json",{"quotes":sorted(quotes,key=lambda q:q["quoted_at"]),"simulations_submitted":False})
    calibrated["calibrated_at"]=utc_now()
    atomic_json("configs/workflow_final.json",calibrated)
    evidence={"generated_at":utc_now(),"reference_problems":list(truth),"recommendations":recommendations,
              "stopping_checks":stop_checks,"fusion_loco":folds,"fusion_enabled":enable_fusion,
              "cross_method_stop_supported":supported,"fusion_local_gate_passed":fusion_gate,
              "limitations":["Samples are circuits, not independent qubit training examples",
                             "Local implementations and cloud kernels have distinct numerical behavior",
                             "A displayed 100 score is rounded and does not bound pointwise error",
                             "G4 has no matched Haar-grid calibration sample"]}
    atomic_json(store.root/"calibration_evidence.json",evidence)
    atomic_json("reports/calibration_evidence.json",evidence)
    atomic_json("reports/sample_benchmarks.json",report)
    trends={}
    for (cid,method),series in history.items():
        if method not in {"mps","pps_threshold"}: continue
        parameter="chi" if method=="mps" else "epsilon"
        trends[f"{cid}/{method}"]=trend_diagnostic([r["estimate"] for r in series],
            [r["parameters"][parameter] for r in series],settings["stopping"]["absolute_tolerance"])
    atomic_json("reports/trend_evidence.json",trends)
    return evidence
