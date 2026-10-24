"""Select complete direct vectors without mixing simulation configurations.

This module only reads supplied receipts.  It does not write artifacts, launch
jobs, infer hidden labels, or certify that higher precision improves accuracy.
Returned candidates are detached snapshots suitable for immutable export.
"""

from copy import deepcopy
import json
import math


def _family(device):
    if device in {"cpu", "gpu"}:
        return "exact"
    if device in {"mps.cpu", "mps.gpu"}:
        return "mps"
    if device in {"pauli-path", "pauli-path.cpu", "pauli-path.gpu"}:
        return "pps"
    return None


def _precision(device, options):
    family = _family(device)
    if family == "exact":
        return 0.0
    name = "mps_bond_dimension" if family == "mps" else "pauli_path_truncation_threshold"
    value = options.get(name)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("Missing numeric simulation precision")
    if not math.isfinite(value) or value <= 0:
        raise ValueError("Simulation precision must be finite and positive")
    if family == "mps" and int(value) != value:
        raise ValueError("MPS bond dimension must be an integer")
    return float(value) if family == "mps" else -float(value)


def _valid(record):
    try:
        value, cost = record["estimate"], record["cost_usd"]
        action = record["action"]
        return (record["status"] == "COMPLETED"
                and not isinstance(value, bool) and not isinstance(cost, bool)
                and math.isfinite(value) and abs(value) <= 1 + 1e-8
                and math.isfinite(cost) and cost >= 0
                and _family(action["device"]) is not None
                and isinstance(action["options"], dict))
    except (KeyError, TypeError, ValueError):
        return False


def select_coherent_vector(records, circuit_ids, primary_device, *, primary_options=None,
                           fallback_device=None):
    """Choose one complete device/options cohort in authoritative ID order.

    Complete exact cohorts take priority.  Otherwise choose the highest
    completed precision in the primary method family, then in the fallback
    family.  CPU/GPU and *all* options always define separate cohorts, including
    PPS transpilation level.  ``primary_options`` restricts eligible primary
    cohorts by a subset of options, for example an explicitly chosen PPS level;
    excluded primary variants never silently become fallback candidates.

    ``fallback_device`` can name the intended fallback family.  If omitted,
    other approximate families are eligible (MPS before PPS when the primary
    is exact).  Precision ties prefer the requested device, then canonical
    configuration order; these are deterministic tie-breaks, not accuracy
    claims.  Per-ID duplicates within one configuration use the latest receipt
    by timestamp, with input order breaking ties, as in the action ledger.

    The return contains ``selected`` (or None), every ``complete_candidate``,
    and per-configuration missing-ID diagnostics.  A collection covering all
    IDs across incompatible configurations still returns INCOMPLETE.
    """
    ids = tuple(circuit_ids)
    if not ids or any(not isinstance(cid, str) or not cid for cid in ids) or len(set(ids)) != len(ids):
        raise ValueError("Need a nonempty authoritative manifest of distinct circuit IDs")
    primary_family = _family(primary_device)
    if primary_family is None or (fallback_device is not None and _family(fallback_device) is None):
        raise ValueError("Unknown primary or fallback device")
    if primary_options is not None and not isinstance(primary_options, dict):
        raise ValueError("primary_options must be an option dictionary")
    constraints = primary_options or {}
    wanted, groups = set(ids), {}
    invalid_count = 0
    for index, record in enumerate(records):
        if not _valid(record):
            invalid_count += 1
            continue
        action = record["action"]
        if action.get("circuit_id") not in wanted:
            continue
        try:
            precision = _precision(action["device"], action["options"])
            serialized = json.dumps(action["options"], sort_keys=True, separators=(",", ":"), allow_nan=False)
        except (TypeError, ValueError):
            invalid_count += 1
            continue
        key = (action["device"], serialized)
        group = groups.setdefault(key, {"device": action["device"],
                                       "options": deepcopy(action["options"]),
                                       "family": _family(action["device"]),
                                       "precision": precision, "rows": {}})
        cid = action["circuit_id"]
        timestamp = str(record.get("updated_at") or record.get("requested_at") or "")
        rank = (timestamp, index)
        if cid not in group["rows"] or rank > group["rows"][cid][0]:
            group["rows"][cid] = (rank, deepcopy(record))

    complete, incomplete = [], []
    for key in sorted(groups):
        group = groups[key]
        summary = {name: deepcopy(group[name]) for name in ("device", "options", "family", "precision")}
        missing = [cid for cid in ids if cid not in group["rows"]]
        if missing:
            summary.update(missing_ids=missing, present_ids=[cid for cid in ids if cid in group["rows"]],
                           completed_count=len(group["rows"]), required_count=len(ids))
            incomplete.append(summary)
        else:
            rows = [group["rows"][cid][1] for cid in ids]
            summary.update(records=rows, values=[float(row["estimate"]) for row in rows],
                           circuit_ids=list(ids), completed_count=len(ids), required_count=len(ids))
            complete.append(summary)

    exact = [candidate for candidate in complete if candidate["family"] == "exact"]
    primary = [candidate for candidate in complete if candidate["family"] == primary_family
               and all(candidate["options"].get(key) == value for key, value in constraints.items())]
    fallback_family = _family(fallback_device) if fallback_device is not None else None
    fallback = [candidate for candidate in complete
                if candidate["family"] not in {"exact", primary_family}
                and (fallback_family is None or candidate["family"] == fallback_family)]

    def preferred(candidates, device):
        # Family ordering matters only for an exact primary with no named fallback.
        return min(candidates, key=lambda candidate: (
            {"exact": 0, "mps": 1, "pps": 2}[candidate["family"]],
            -candidate["precision"], candidate["device"] != device,
            candidate["device"], json.dumps(candidate["options"], sort_keys=True)))

    if exact:
        selected = preferred(exact, primary_device if primary_family == "exact" else "cpu")
        reason = "Complete exact vector takes precedence"
    elif primary:
        selected = preferred(primary, primary_device)
        reason = "Highest completed precision in a coherent primary-method vector; accuracy unverified"
    elif fallback:
        selected = preferred(fallback, fallback_device)
        reason = "Complete coherent fallback; no complete eligible primary vector, accuracy unverified"
    else:
        selected = None
        reason = "No complete eligible single-device, single-configuration vector; mixed rows were not substituted"
    selected = deepcopy(selected)
    if selected is not None:
        selected["selection_reason"] = reason
    return {"status": "COMPLETE" if selected is not None else "INCOMPLETE", "selected": selected,
            "complete_candidates": complete, "incomplete_candidates": incomplete,
            "circuit_ids": list(ids), "invalid_record_count": invalid_count, "reason": reason}
