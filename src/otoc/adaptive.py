"""Observable diagnostics and an explicit, conservative stopping decision."""

import math
import numpy as np


def trend_diagnostic(values, precisions=None, tolerance=.001):
    """Describe within-method trends; a geometric tail is a heuristic, not a bound."""
    values=np.asarray(values,float)
    if values.size<2 or not np.isfinite(values).all():
        return {"classification":"INSUFFICIENT_HISTORY","levels":len(values),"priority_uncertainty":1.}
    steps=np.diff(values)
    if precisions is None:
        spacings=np.ones(len(steps))
    else:
        spacings=np.abs(np.diff(np.log(np.asarray(precisions,float))))
        if np.any(spacings<=0) or not np.isfinite(spacings).all():
            raise ValueError("Trend levels need distinct positive precision parameters")
    slopes=steps/spacings
    recent=steps[-3:]
    significant=recent[np.abs(recent)>tolerance*.1]
    flips=int(np.sum(significant[1:]*significant[:-1]<0))
    ratio=float(abs(slopes[-1]/slopes[-2])) if len(slopes)>=2 and abs(slopes[-2])>1e-14 else None
    flat=bool(len(steps)>=2 and max(abs(steps[-2:]))<=tolerance)
    contracting=bool(len(steps)>=3 and flips==0 and ratio is not None and ratio<.8)
    state="OSCILLATING" if flips else "FLAT_UNVERIFIED" if flat else "CONTRACTING" if contracting else "GROWING" if ratio is not None and ratio>1.2 else "UNRESOLVED"
    tail=float(abs(steps[-1])*ratio/(1-ratio)) if contracting else None
    uncertainty=float(max(abs(recent)))
    if tail is not None: uncertainty=max(uncertainty,tail)
    if state in {"OSCILLATING","GROWING"}: uncertainty*=1.5
    return {"classification":state,"levels":len(values),"signed_steps":steps.tolist(),
            "slopes_per_log_precision":slopes.tolist(),"last_contraction_ratio":ratio,"sign_flips":flips,
            "geometric_tail_proxy":tail,"priority_uncertainty":uncertainty,
            "interpretation":"Used for scheduling, never an error certificate or extrapolated submission value"}


def vector_comparison(current, previous, signal_floor=1e-4):
    a, b = np.asarray(current, float), np.asarray(previous, float)
    if a.shape != b.shape or a.size == 0 or not np.isfinite(a).all() or not np.isfinite(b).all():
        return {"shape_change": None, "rms_change": None, "signal_resolved": False}
    ac, bc = a - a.mean(), b - b.mean()
    rms_signal = min(float(np.sqrt(np.mean(ac**2))), float(np.sqrt(np.mean(bc**2))))
    correlation = None
    if rms_signal >= signal_floor:
        correlation = float(np.clip(np.dot(ac, bc) / (np.linalg.norm(ac) * np.linalg.norm(bc)), -1, 1))
    return {"shape_change": None if correlation is None else 1 - correlation,
            "rms_change": float(np.sqrt(np.mean((a-b)**2))), "signal_resolved": correlation is not None}


def stopping_diagnostic(mps, pps, scale, settings, shape_change=None, signal_resolved=True):
    """Histories are ordered from coarse to fine; agreement alone never stops."""
    minimum = settings["minimum_levels_per_method"]
    count = settings["consecutive_steps"]
    if min(len(mps), len(pps)) < max(minimum, count + 1):
        return {"stop": False, "quality": "LOW", "reason": "insufficient_refinements", "uncertainty": 1.0}
    changes_m = np.abs(np.diff(mps[-(count+1):]))
    changes_p = np.abs(np.diff(pps[-(count+1):]))
    disagreement = abs(mps[-1] - pps[-1])
    proxy = float(max(changes_m.max(), changes_p.max(), disagreement))
    scale = max(float(scale), settings["scale_floor"])
    threshold = min(settings["absolute_tolerance"], settings["scaled_tolerance"] * scale)
    stable_shape = shape_change is not None and shape_change <= settings["shape_tolerance"]
    stop = bool(proxy <= threshold and signal_resolved and stable_shape)
    return {"stop": stop, "quality": "HIGH" if stop else "UNSTABLE" if disagreement > 10*threshold else "MEDIUM",
            "reason": "stable_both_methods_and_shape" if stop else "refinement_or_independent_check_needed",
            "uncertainty": proxy, "scaled_uncertainty": proxy/scale,
            "cross_disagreement": disagreement, "mps_step": float(changes_m.max()),
            "pps_step": float(changes_p.max()), "effective_tolerance": threshold,
            "shape_change": shape_change, "signal_resolved": bool(signal_resolved),
            "interpretation": "Engineering diagnostic, not a confidence interval or accuracy guarantee"}


def priority(weight, uncertainty, seconds, *, uncovered=False, missing_branch=False):
    if not all(math.isfinite(v) for v in (weight, uncertainty, seconds)):
        return 0.0
    coverage = 1e6 if uncovered else 1e5 if missing_branch else 1.0
    return coverage * weight * max(uncertainty, 1e-3) / max(seconds, 1.0)
