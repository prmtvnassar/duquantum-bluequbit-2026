"""Evidence-based recovery and score-shape diagnostics; no hidden-label fitting."""

from copy import deepcopy
from datetime import datetime
import json
import numpy as np


def method(device):
    return "mps" if device.startswith("mps") else "pps" if device.startswith("pauli-path") else "exact"


def completed(record):
    v = record.get("estimate")
    return (record.get("status") == "COMPLETED" and v is not None
            and np.isfinite(v) and abs(v) <= 1 + 1e-8 and record.get("cost_usd") is not None)


def recover_flat_policy(settings, records):
    """Switch a flat primary only after a complete, nonflat independent pilot.

    Each pilot vector must use one identical configuration. This recovers signal,
    not accuracy; selection remains direct and explicitly uncertified.
    """
    result = deepcopy(settings)
    evidence = {}
    for problem, policy in result["graded_policy"].items():
        if policy["primary"] == "cpu":
            continue
        ids = [f"Duke_{problem}_{q}" for q in settings["pilot_qubits"][problem]]
        groups = {}
        for r in records:
            a = r["action"]
            if completed(r) and a["circuit_id"] in ids and method(a["device"]) != "exact":
                key = (method(a["device"]), json.dumps(a["options"], sort_keys=True))
                groups.setdefault(key, {})[a["circuit_id"]] = r
        vectors = []
        for (family, options), rows in groups.items():
            if all(cid in rows for cid in ids):
                vals = [rows[cid]["estimate"] for cid in ids]
                vectors.append((family, json.loads(options), float(np.ptp(vals)), rows))
        primary = method(policy["primary"])
        own = [v for v in vectors if v[0] == primary]
        alternate = [v for v in vectors if v[0] != primary and v[2] > settings["stopping"]["signal_floor"]]
        if own and all(v[2] <= settings["stopping"]["signal_floor"] for v in own) and alternate:
            # Deterministic highest completed precision, never largest amplitude.
            alternate.sort(key=lambda v: v[1].get("mps_bond_dimension", 0)
                           if v[0] == "mps" else -v[1]["pauli_path_truncation_threshold"])
            family, options, spread, rows = alternate[-1]
            policy["primary"] = "mps.cpu" if family == "mps" else "pauli-path"
            if family == "mps":
                policy["chi"] = options["mps_bond_dimension"]
            else:
                policy["epsilon"] = options["pauli_path_truncation_threshold"]
            policy["reason"] = "Flat primary pilot replaced by a complete nonconstant independent-method pilot; signal recovery only, accuracy uncertified"
            evidence[problem] = {"previous_primary": primary, "selected_primary": family,
                                 "pilot_spread": spread, "options": options,
                                 "job_ids": [rows[cid]["job_id"] for cid in ids],
                                 "interpretation": policy["reason"]}
    return result, evidence


def empirical_seconds(action, records, quoted_seconds):
    """Use measured upper-quartile wall time as a floor, never discount a quote."""
    durations = []
    for r in records:
        a = r["action"]
        if (a["circuit_id"].split("_")[1] != action["problem"]
                or a["device"] != action["device"] or not completed(r)):
            continue
        try:
            duration = (datetime.fromisoformat(r["updated_at"]) - datetime.fromisoformat(r["requested_at"])).total_seconds()
        except (KeyError, TypeError, ValueError):
            continue
        if duration >= 0:
            durations.append(duration)
    observed = float(np.quantile(durations, .75)) if durations else None
    return {"seconds": max(quoted_seconds or 0, observed or 0),
            "observed_upper_quartile_seconds": observed, "observations": len(durations),
            "interpretation": "Empirical wall-time floor, not a runtime guarantee or a cost discount"}


def shape_influence(previous, current, signal_floor=1e-4):
    """Residual shape change after affine alignment, independent of hidden truth.

    Pearson score ignores positive affine shifts. The residual projects change
    off the constant and previous centered vector; its squared components rank
    where a refinement changed shape rather than merely offset or scale.
    """
    a, b = np.asarray(previous, float), np.asarray(current, float)
    if a.ndim != 1 or a.shape != b.shape or a.size < 3 or not np.isfinite(a).all() or not np.isfinite(b).all():
        raise ValueError("Need aligned finite vectors of at least three rows")
    ac, bc = a-a.mean(), b-b.mean()
    energy = float(ac @ ac)
    if min(np.std(a), np.std(b)) < signal_floor:
        return {"status": "NEAR_CONSTANT_VECTOR", "row_influence": None, "shape_change": None}
    slope = float(ac @ bc / energy)
    residual = bc - slope*ac
    influence = residual**2 / float(bc @ bc)
    correlation = float(np.clip(ac @ bc / np.sqrt(energy * (bc @ bc)), -1, 1))
    return {"status": "RESOLVED" if slope > 0 else "SIGN_REVERSAL",
            "affine_slope": slope, "shape_change": 1-correlation,
            "row_influence": influence.tolist(),
            "relative_shape_residual": float(influence.sum()),
            "interpretation": "Precision-sensitivity ranking only; not expected score gain or an error bound"}


def complete_vector_trends(records, sizes, signal_floor=1e-4):
    """Compare only complete vectors at fixed device/transpilation, never sparse pilots."""
    groups = {}
    for r in records:
        if not completed(r):
            continue
        a=r['action']; problem=a['circuit_id'].split('_')[1]
        if problem not in sizes or method(a['device']) == 'exact':
            continue
        options=a['options']
        key=(problem,a['device'],options.get('pauli_path_circuit_transpilation_level'))
        precision=options.get('mps_bond_dimension') if method(a['device'])=='mps' else -options['pauli_path_truncation_threshold']
        groups.setdefault(key,{}).setdefault(precision,{})[a['circuit_id']]=r['estimate']
    result={}
    for (problem,device,level),levels in groups.items():
        ids=[f'Duke_{problem}_{q}' for q in range(sizes[problem])]
        complete=sorted(p for p,rows in levels.items() if all(cid in rows for cid in ids))
        if len(complete)<2:
            continue
        old,new=complete[-2:]
        diagnostic=shape_influence([levels[old][cid] for cid in ids],[levels[new][cid] for cid in ids],signal_floor)
        diagnostic.update(circuit_ids=ids,precision_pair=[old,new],transpilation_level=level)
        result[f'{problem}/{device}/{level}']=diagnostic
    return result
