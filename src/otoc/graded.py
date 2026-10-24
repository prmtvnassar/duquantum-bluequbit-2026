"""Budgeted hidden-ID planning, direct selection, and auditable decisions."""
from datetime import datetime, timezone
from copy import deepcopy
import csv
import io
import json
import math
from pathlib import Path
from bluequbit_samples.provenance import atomic_json
from .bluequbit_adapter import SIZES, cost_gate
from .duke_submission import build_submission, write_submission
from .experiment_store import digest, utc_now
from .ledger import event
from .adaptive import trend_diagnostic
from .campaign_reasoning import recover_flat_policy, empirical_seconds, complete_vector_trends
from .coherent_selection import select_coherent_vector

POINTS = {"G1":300,"G2":600,"G3":800,"G4":1000}


def family(device):
    return "exact" if device in {"cpu","gpu"} else "mps" if device.startswith("mps") else "pps"


def score_progress(problem):
    receipts=[json.loads(p.read_text()) for p in (Path("submissions")/problem).glob("attempt-*.json")]
    receipts.sort(key=lambda r:r["attempt"])
    scores=[r["displayed_score"] for r in receipts]
    best=max(scores) if scores else None
    return {"observed_submissions":len(scores),"best_displayed_score":best,
            "recent_score_change":scores[-1]-scores[-2] if len(scores)>1 else None,
            "priority_room":max(.01,1-best/POINTS[problem]) if best is not None else 1.,
            "interpretation":"Whole-problem effort allocation only; never infer or fit individual hidden labels"}


def action_history(root):
    records=[json.loads(p.read_text()) for p in (Path(root)/"remote_actions").glob("*.json")]
    if Path(root).resolve()==Path("results/workflow").resolve():
        imported=Path("runs/imports/kevin/g1_exact_actions.json")
        if imported.exists():
            records.extend(json.loads(imported.read_text())["records"])
    return sorted(records,key=lambda r:r.get("updated_at") or r.get("requested_at") or "")


def valid(record):
    value = record.get("estimate")
    return (record["status"] == "COMPLETED" and value is not None and math.isfinite(float(value))
            and abs(float(value)) <= 1+1e-8 and record.get("cost_usd") is not None)


def precision(record):
    options = record["action"]["options"]
    return options.get("mps_bond_dimension",0) if record["action"]["device"].startswith("mps") else -options.get("pauli_path_truncation_threshold",1.)


def select_record(records, problem, settings):
    candidates = [r for r in records if valid(r)]
    exact = [r for r in candidates if family(r["action"]["device"])=="exact"]
    if exact:
        return exact[-1], "Exact statevector result takes precedence"
    policy = settings["graded_policy"][problem]
    primary = policy.get("fallback") if policy["primary"]=="cpu" else policy["primary"]
    preferred = [r for r in candidates if family(r["action"]["device"])==family(primary)]
    if family(primary)=="pps":
        level=policy.get("transpilation_level",settings["cloud_pps_transpilation_level"])
        preferred=[r for r in preferred if r["action"]["options"].get("pauli_path_circuit_transpilation_level",2)==level]
    if preferred:
        return max(preferred,key=precision), "Highest completed precision in the sample-informed primary method"
    if candidates:
        return candidates[-1], "Available direct fallback; primary unavailable, accuracy unverified"
    return None, "No completed valid direct estimate"


def _options(device, policy, settings):
    if device==policy.get("primary") and policy.get("baseline_options") is not None:
        return deepcopy(policy["baseline_options"])
    if device=="cpu":
        return {}
    if device.startswith("mps"):
        return {"mps_bond_dimension":policy.get("chi",256)}
    return {"pauli_path_truncation_threshold":policy.get("epsilon",.001),
            "pauli_path_circuit_transpilation_level":policy.get("transpilation_level",settings["cloud_pps_transpilation_level"])}


def _candidate(cid,device,options,reason,stage,uncertainty=1.):
    return {"circuit_id":cid,"problem":cid.split("_")[1],"device":device,"options":options,
            "reason":reason,"stage":stage,"uncertainty":uncertainty}


def baseline_route_policy(problem,records,settings):
    policy=deepcopy(settings["graded_policy"][problem])
    if family(policy["primary"])=="exact":
        return policy
    options=_options(policy["primary"],policy,settings)
    routes={}
    for r in records:
        a=r["action"]
        if valid(r) and a["circuit_id"].split("_")[1]==problem and a["options"]==options and family(a["device"])==family(policy["primary"]):
            routes.setdefault(a["device"],set()).add(a["circuit_id"])
    if routes:
        policy["primary"]=min(routes,key=lambda d:(-len(routes[d]),d!=policy["primary"],d))
    return policy


def candidates_for(problem,records,settings):
    policy, suggestions = baseline_route_policy(problem,records,settings), []
    discovery=settings.get("discovery",{})
    if discovery.get("enabled") and problem!="G1":
        # A bounded representation check survives a temporary switch to MPS.
        for q in settings["pilot_qubits"][problem]:
            cid=f"Duke_{problem}_{q}"
            matching=[r for r in records if r["action"]["circuit_id"]==cid and valid(r)]
            pps=[r for r in matching if family(r["action"]["device"])=="pps"]
            if any(abs(r["estimate"])<=settings["stopping"]["signal_floor"] for r in pps):
                options={"pauli_path_truncation_threshold":discovery.get("pps_threshold",.001),
                         "pauli_path_circuit_transpilation_level":discovery.get("pps_transpilation_level",1)}
                suggestions.append(_candidate(cid,"pauli-path",options,
                    "Bounded alternate-transpilation pilot at fixed threshold; test representation sensitivity without assuming accuracy or abandoning PPS after MPS recovery","discovery"))
            probe_q=discovery.get("mps_probe_qubits",{}).get(problem,settings["pilot_qubits"][problem][1])
            if q==probe_q and any(family(r["action"]["device"])=="mps" for r in matching):
                suggestions.append(_candidate(cid,"mps.cpu",{"mps_bond_dimension":discovery.get("mps_chi",32)},
                    "Bounded central-pilot bond sensitivity check before bulk low-chi coverage; a nonconstant pilot is not accuracy evidence","discovery"))
    pilot_values=[]
    for pilot in settings["pilot_qubits"][problem]:
        chosen,_=select_record([r for r in records if r["action"]["circuit_id"]==f"Duke_{problem}_{pilot}"],problem,settings)
        if chosen:
            pilot_values.append(chosen["estimate"])
    pilots_complete=len(pilot_values)==len(settings["pilot_qubits"][problem])
    pilot_resolved=bool(pilots_complete and max(pilot_values)-min(pilot_values)>settings["stopping"]["signal_floor"])
    first_pilot=f"Duke_{problem}_{settings['pilot_qubits'][problem][0]}"
    paired=any(r["action"]["circuit_id"]==first_pilot and valid(r)
               and family(r["action"]["device"])!=family(policy["primary"]) for r in records)
    for q in range(SIZES[problem]):
        if policy["primary"]!="cpu" and settings.get("pilot_signal_gate",False) and (not pilot_resolved or (problem=="G4" and not paired)) and q not in settings["pilot_qubits"][problem]:
            continue  # Do not spend an entire baseline on an unresolved flat pilot.
        cid = f"Duke_{problem}_{q}"
        attempts = [r for r in records if r["action"]["circuit_id"]==cid]
        good = [r for r in attempts if valid(r)]
        chosen,_ = select_record(attempts,problem,settings)
        if any(family(r["action"]["device"])=="exact" for r in good):
            continue
        primary = policy["primary"]
        baseline_options=_options(primary,policy,settings)
        coherent_row=any(r["action"]["device"]==primary and r["action"]["options"]==baseline_options for r in good)
        if primary!="cpu" and not coherent_row:
            suggestions.append(_candidate(cid,primary,baseline_options,
                               "Missing row in selected single-device, fixed-options baseline cohort. "+policy["reason"],"coverage"))
            continue
        if primary=="cpu" and any(r["action"]["device"]=="cpu" for r in attempts):
            primary = policy["fallback"]
        if not chosen:
            if any(r["action"]["device"]==primary for r in attempts):
                primary="pauli-path" if primary.startswith("mps") else "mps.cpu"
            suggestions.append(_candidate(cid,primary,_options(primary,policy,settings),
                               "Missing baseline row; use an unattempted direct method. "+policy["reason"],"coverage"))
            continue
        if primary=="cpu":
            primary=policy["fallback"]
        secondary = "pauli-path" if primary.startswith("mps") else "mps.cpu"
        if q in settings["pilot_qubits"][problem] and not any(family(r["action"]["device"])==family(secondary) for r in attempts):
            suggestions.append(_candidate(cid,secondary,_options(secondary,policy,settings),
                               "Independent native-method pilot; local/cloud transfer unvalidated","cross_pilot"))
        family_rows=[r for r in good if family(r["action"]["device"])==family(primary) and
                     (family(primary)!="pps" or r["action"]["options"].get("pauli_path_circuit_transpilation_level",2)==policy.get("transpilation_level",settings["cloud_pps_transpilation_level"]))]
        history_device=max(family_rows,key=precision)["action"]["device"] if family_rows else primary
        by_precision={precision(r):r for r in good if r["action"]["device"]==history_device and
                      (family(primary)!="pps" or r["action"]["options"].get("pauli_path_circuit_transpilation_level",2)==policy.get("transpilation_level",settings["cloud_pps_transpilation_level"]))}
        history = [by_precision[p] for p in sorted(by_precision)]
        if not history:
            continue
        options=dict(history[-1]["action"]["options"])
        if primary.startswith("mps"):
            old=options["mps_bond_dimension"]
            if old>=settings["maximum_native_chi"]:
                continue
            options["mps_bond_dimension"]=min(2*old,settings["maximum_native_chi"])
        else:
            finer=[e for e in settings["pps_thresholds"] if e<options["pauli_path_truncation_threshold"]]
            if not finer:
                continue
            options["pauli_path_truncation_threshold"]=max(finer)
        parameter="mps_bond_dimension" if primary.startswith("mps") else "pauli_path_truncation_threshold"
        trend=trend_diagnostic([r["estimate"] for r in history],[r["action"]["options"][parameter] for r in history],
                               settings["stopping"]["absolute_tolerance"])
        uncertainty=trend["priority_uncertainty"]
        cross=[r for r in good if family(r["action"]["device"])==family(secondary)]
        if cross:
            uncertainty=max(uncertainty,abs(history[-1]["estimate"]-cross[-1]["estimate"]))
        suggestions.append(_candidate(cid,primary,options,
                           "Refine based on within-method "+trend["classification"]+" trend and cross-method sensitivity; convergence is not certified","refine",uncertainty))
        suggestions[-1]["trend"]=trend
    attempted={(r["action"]["circuit_id"],family(r["action"]["device"]),json.dumps(r["action"]["options"],sort_keys=True)) for r in records}
    exact_attempted={(r["action"]["circuit_id"],r["action"]["device"],json.dumps(r["action"]["options"],sort_keys=True)) for r in records}
    return [s for s in suggestions if ((s["circuit_id"],s["device"],json.dumps(s["options"],sort_keys=True)) not in exact_attempted
            if s["stage"]=="coverage" else (s["circuit_id"],family(s["device"]),json.dumps(s["options"],sort_keys=True)) not in attempted)]


def plan_next(adapter,settings,problems=("G1","G2","G3","G4"),quote_limit=8):
    if not 1<=quote_limit<=32 or any(p not in POINTS for p in problems):
        raise ValueError("Invalid graded planning scope")
    usage, records = adapter.usage(), action_history(adapter.root)
    settings, recovery = recover_flat_policy(settings, records)
    for p in POINTS:
        settings["graded_policy"][p]=baseline_route_policy(p,records,settings)
    vector_trends=complete_vector_trends(records,SIZES,settings["stopping"]["signal_floor"])
    uncovered={}
    for p in POINTS:
        policy=settings["graded_policy"][p]
        options=_options(policy["primary"],policy,settings)
        uncovered[p]=sum(not any(valid(r) and r["action"]["circuit_id"]==f"Duke_{p}_{q}" and
                         (family(r["action"]["device"])=="exact" or
                          (r["action"]["device"]==policy["primary"] and r["action"]["options"]==options))
                         for r in records) for q in range(SIZES[p]))
    baseline_rates={p:max(settings["baseline_quote_reserve_usd_per_row"],
                          settings.get("baseline_quote_reserve_by_problem",{}).get(p,0)) for p in ("G2","G3","G4")}
    for r in records:
        a=r["action"];p=a["circuit_id"].split("_")[1]
        if p not in baseline_rates:
            continue
        policy=settings["graded_policy"][p]
        price=r.get("quote",{}).get("cost_usd")
        if (a["device"]==policy["primary"] and a["options"]==_options(policy["primary"],policy,settings)
                and isinstance(price,(int,float)) and math.isfinite(price) and price>=0):
            baseline_rates[p]=max(baseline_rates[p],price)
    remaining=(datetime.fromisoformat(settings["deadline_utc"])-datetime.now(timezone.utc)).total_seconds()
    pending={p:candidates_for(p,records,settings) for p in problems}
    for p in pending:
        pending[p].sort(key=lambda a:({"discovery":-1,"coverage":0,"cross_pilot":1,"refine":2}[a["stage"]],-a["uncertainty"]))
    shortlist=[]
    while len(shortlist)<quote_limit and any(pending.values()):
        for p in problems:
            if pending[p] and len(shortlist)<quote_limit:
                shortlist.append(pending[p].pop(0))
    for item in shortlist:
        quote_fn=getattr(adapter,"quote_for_plan",adapter.quote)
        quote=quote_fn(item["circuit_id"],item["device"],item["options"])
        limit=settings["exact_job_seconds"] if item["device"]=="cpu" else settings["remote_job_seconds"]
        if family(item["device"])=="mps" and item["options"].get("mps_bond_dimension",0)==32:
            limit=max(limit,settings.get("mps_chi32_job_seconds",limit))
        if item["stage"]=="discovery":
            limit=settings["discovery"].get("mps_timeout_seconds",900) if family(item["device"])=="mps" else settings["discovery"].get("pps_timeout_seconds",180)
        seconds=quote.get("runtime_seconds")
        if item["device"]=="cpu" and (quote.get("cost_usd")!=0 or quote.get("error") or seconds is None or seconds>limit):
            item.update(device="mps.cpu",options=_options("mps.cpu",settings["graded_policy"][item["problem"]],settings),
                        reason=item["reason"]+"; exact quote unavailable, paid, or too slow; MPS fallback")
            quote=quote_fn(item["circuit_id"],item["device"],item["options"])
            seconds,limit=quote.get("runtime_seconds"),settings["remote_job_seconds"]
        alternatives=[quote]
        if settings.get("gpu_enabled",False) and item["stage"]!="coverage" and item["device"] in {"mps.cpu","pauli-path"}:
            gpu="mps.gpu" if item["device"]=="mps.cpu" else "pauli-path.gpu"
            alternative=quote_fn(item["circuit_id"],gpu,item["options"])
            alternatives.append(alternative)
            def feasible(q):
                t=q.get("runtime_seconds")
                return (cost_gate(item["problem"],q,usage,settings,item["reason"])[0]
                        and t is not None and math.isfinite(t) and 0<=t<=limit)
            feasible_quotes=[q for q in alternatives if feasible(q)]
            if feasible_quotes:
                quote=min(feasible_quotes,key=lambda q:(q["cost_usd"],q["runtime_seconds"]))
                item["device"]=quote.get("device",item["device"])
                seconds=quote["runtime_seconds"]
        allowed,gate=cost_gate(item["problem"],quote,usage,settings,item["reason"])
        if seconds is None or not math.isfinite(seconds) or seconds<0 or seconds>limit:
            allowed,gate=False,"invalid_or_excessive_runtime"
        if remaining<settings["submission_buffer_seconds"]+(seconds or limit):
            allowed,gate=False,"deadline_buffer"
        # G1 exact CPU is expected to be free. Preserve estimated paid coverage for G2-G4.
        counts={p:uncovered[p] for p in ("G2","G3","G4")}
        if item["stage"]=="coverage" and item["problem"]!="G1":
            counts[item["problem"]]=max(0,counts[item["problem"]]-1)
        rates=dict(baseline_rates)
        if item["stage"]=="coverage" and item["problem"] in rates and quote.get("cost_usd") is not None:
            rates[item["problem"]]=max(rates[item["problem"]],quote["cost_usd"])
        reserve=sum(counts[p]*rates[p] for p in counts)
        available=settings["graded_budget_usd"]*(1-settings["graded_reserve_fraction"])-usage["known_cost_usd"]
        if quote.get("cost_usd") is not None and quote["cost_usd"]>0 and quote["cost_usd"]+reserve>available:
            allowed,gate=False,"protect_remaining_baseline_budget"
        if (adapter.root/"STOP").exists():
            allowed,gate=False,"stop_file"
        runtime_model=empirical_seconds(item,records,seconds)
        predicted_seconds=runtime_model["seconds"]
        if remaining<settings["submission_buffer_seconds"]+predicted_seconds:
            allowed,gate=False,"empirical_deadline_buffer"
        denominator=(quote.get("cost_usd") or 0)+max(predicted_seconds,1)/3600
        multiplier={"discovery":1e7,"coverage":1e6,"cross_pilot":1e6 if item["problem"]=="G4" else 10,"refine":1}[item["stage"]]
        progress=score_progress(item["problem"])
        score=multiplier*POINTS[item["problem"]]/SIZES[item["problem"]]*max(item["uncertainty"],.001)/denominator
        if item["stage"]=="refine": score*=progress["priority_room"]
        shape_key=f"{item['problem']}/{item['device']}/{item['options'].get('pauli_path_circuit_transpilation_level')}"
        shape=vector_trends.get(shape_key)
        shape_multiplier=1.
        if item["stage"]=="refine" and shape and shape.get("row_influence") is not None:
            q=int(item["circuit_id"].split("_")[-1])
            shape_multiplier+=SIZES[item["problem"]]*shape["row_influence"][q]
            if shape["status"]=="SIGN_REVERSAL":
                shape_multiplier+=1.  # Negative affine scaling is not score-invariant.
            score*=shape_multiplier
        item.update(quote=quote,allowed=allowed,gate=gate,priority=score if allowed else 0,
                    protected_baseline_usd=reserve,timeout_seconds=limit,route_quotes=alternatives,score_progress=progress,
                    runtime_model=runtime_model,shape_priority_multiplier=shape_multiplier)
        if "gpu" in item["device"]:
            item["timeout_seconds"]=min(limit,settings.get("gpu_total_seconds",27000)-usage.get("gpu_seconds",0),
                                        settings.get("gpu_hour_seconds",2700)-usage.get("gpu_seconds_last_hour",0))
    shortlist.sort(key=lambda a:a["priority"],reverse=True)
    plan={"generated_at":utc_now(),"usage":usage,"missing_rows":uncovered,"actions":shortlist,
          "next":next((s for s in shortlist if s["allowed"]),None),"status":"PLAN_ONLY",
          "policy_recovery":recovery,
          "baseline_quote_rates":baseline_rates,
          "vector_trends":vector_trends,
          "warning":"Sample allocation is a prior. Budget/deadline stops do not certify numerical convergence. Flat pilot vectors block bulk coverage and require refinement/review."}
    atomic_json(adapter.root/"graded_plan.json",plan)
    event("graded_decision",plan)
    return plan


def export_complete(settings,root="results/workflow"):
    records,exports=action_history(root),[]
    settings,recovery=recover_flat_policy(settings,records)
    for problem in POINTS:
        template=next(Path("problems").glob(f"*_graded_{problem}/local_submission_template.csv"))
        with template.open(newline="",encoding="utf-8-sig") as handle:
            ids=[row["circuit_id"] for row in csv.DictReader(handle)]
        policy=settings["graded_policy"][problem]
        primary_options=({"pauli_path_circuit_transpilation_level":policy.get("transpilation_level",settings["cloud_pps_transpilation_level"])}
                         if family(policy["primary"])=="pps" else None)
        cohort=select_coherent_vector(records,ids,policy["primary"],primary_options=primary_options,
                                      fallback_device=policy.get("fallback"))
        atomic_json(Path(root)/"coherent_candidates"/f"{problem}.json",cohort)
        if cohort["selected"] is None:
            continue
        chosen=[]
        for record in cohort["selected"]["records"]:
            chosen.append({"circuit_id":record["action"]["circuit_id"],"value":record["estimate"],"job_id":record["job_id"],
                           "device":record["action"]["device"],"options":record["action"]["options"],
                           "selection_reason":cohort["selected"]["selection_reason"],"cost_usd":record["cost_usd"]})
        if len(chosen)!=SIZES[problem]:
            continue
        buffer=io.StringIO(newline="")
        writer=csv.writer(buffer,lineterminator="\n")
        writer.writerow(("circuit_id","value"))
        writer.writerows((r["circuit_id"],format(r["value"],".17g")) for r in chosen)
        payload=buffer.getvalue().encode()
        target=Path(root)/"submissions"/problem/f"direct-{digest(chosen)[:12]}.csv"
        write_submission(payload,target,immutable=True)
        build_submission(template,target)
        baseline=Path(root)/"baselines"/f"{problem}.csv"
        if not baseline.exists():
            write_submission(payload,baseline,immutable=True)
        methods=sorted({r["device"]+" "+json.dumps(r["options"],sort_keys=True) for r in chosen})
        note=("Ran each published ID separately through BlueQubit from |0...0>, evaluating target Z with q0 rightmost. "
              "Selected a complete direct vector at one device and identical options for every ID, prioritizing exact CPU then the selected method's highest complete "
              "precision. Methods: "+"; ".join(methods)+". Partial refinements do not replace individual rows. No hidden-circuit reconstruction, score-derived labels, "
              "extrapolation or fusion. Per-ID job IDs and precision are in the manifest. "
              "Budget-limited approximations have no certified error bounds.")
        if problem in recovery:
            note += " The starting method produced a flat pilot vector; a complete, fixed-precision independent pilot resolved signal and supplied the replacement baseline. This does not certify accuracy."
        target.with_suffix(".txt").write_text(note+"\n",encoding="utf-8")
        resolved=max(r["value"] for r in chosen)-min(r["value"] for r in chosen)>settings["stopping"]["signal_floor"]
        exact=cohort["selected"]["family"]=="exact"
        recommended=bool(exact and resolved)
        if recommended:
            recommendation_reason="Complete resolved direct vector from exact simulation; no approximation truncation. This does not establish an official score."
        elif exact:
            recommendation_reason="The exact vector has unresolved signal and requires numerical review."
        else:
            recommendation_reason=("An approximate export establishes file validity and signal status only, not accuracy or a recommendation to upload. "
                                   "Further precision, independent evidence and known actual scores guide agent numerical review.")
        atomic_json(target.with_suffix(".json"),{"selection":chosen,"method_note":note,"submitted":False,
                    "policy_recovery":recovery.get(problem),
                    "eligibility_scope":"format_and_resolved_signal_only","format_valid":True,"signal_resolved":resolved,
                    "submission_recommended":recommended,
                    "review_status":"EXACT_COMPLETE_RESOLVED" if recommended else "NUMERICAL_REVIEW_REQUIRED",
                    "recommendation_reason":recommendation_reason,
                    "submission_eligible":resolved,"quality":"DIRECT_UNCERTIFIED" if resolved else "UNRESOLVED_SIGNAL_REVIEW_REQUIRED"})
        event("candidate_export",{"problem":problem,"csv_path":str(target),"selection":chosen})
        exports.append(str(target.resolve()))
    return exports
