"""Replay one conservative MPS extrapolator using saved sample outputs only.

This script imports no simulator or service client and submits no jobs. It tests
the equal-ratio geometric/Aitken model on two S2 precision windows. Its failure
does not establish that every possible extrapolator must fail.
"""

import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import statistics


REPO = Path(__file__).resolve().parents[1]
RATIO_CEILING = 0.9
DENOMINATOR_FLOOR = 1e-12
WINDOWS = ((8, 16, 32, 64), (16, 32, 64, 128))


def score(values, truth):
    """Local correlation-score replica; no official scoring service is called."""
    x = [v - statistics.mean(values) for v in values]
    y = [v - statistics.mean(truth) for v in truth]
    nx = math.sqrt(sum(v * v for v in x))
    ny = math.sqrt(sum(v * v for v in y))
    if nx <= 1e-14:
        return 0.0
    if ny <= 1e-14:
        raise ValueError("Cannot score a constant reference vector")
    rho = max(-1.0, min(1.0, sum(a * b for a, b in zip(x, y)) / (nx * ny)))
    return 100 * max(0.0, rho) ** 2


def errors(values, truth):
    delta = [abs(a - b) for a, b in zip(values, truth)]
    return {
        "mae": statistics.mean(delta),
        "rmse": math.sqrt(statistics.mean(d * d for d in delta)),
        "max_absolute_error": max(delta),
    }


def relative(path):
    try:
        return path.resolve().relative_to(REPO).as_posix()
    except ValueError:
        return str(path.resolve())


def read_records(directory):
    """Match calibration.histories' latest-successful-per-parameter selection."""
    items = []
    for path in sorted(directory.glob("*.json")):
        payload = path.read_bytes()
        item = json.loads(payload)
        items.append((item, path, hashlib.sha256(payload).hexdigest()))
    latest = {}
    for item, path, sha256 in sorted(items, key=lambda entry: entry[0]["saved_at"]):
        r = item["record"]
        value = r.get("estimate")
        if r["status"] != "SUCCEEDED" or value is None:
            continue
        if not math.isfinite(value):
            raise ValueError(f"Nonfinite successful output: {path}")
        key = (r["circuit_id"], r["method"], json.dumps(r["parameters"], sort_keys=True))
        latest[key] = {
            "record": r,
            "key": item["key"],
            "saved_at": item["saved_at"],
            "path": relative(path),
            "sha256": sha256,
            "action_input_sha256": item["action"].get("input_sha256"),
            "engine_source": item["action"].get("engine_source"),
        }
    return list(latest.values()), len(items)


def evaluate(entries):
    refs, mps = {}, {}
    coverage = defaultdict(lambda: defaultdict(set))
    for entry in entries:
        r = entry["record"]
        problem = r.get("sample")
        if problem not in {"S1", "S2", "S3"}:
            continue
        parameter = r["parameters"].get("chi", r["parameters"].get("epsilon"))
        if parameter is not None:
            coverage[problem][r["method"]].add((r["circuit_id"], parameter))
        if problem != "S2":
            continue
        if r["method"] == "exact":
            if r["circuit_id"] in refs:
                raise ValueError("Ambiguous exact reference parameters for S2")
            refs[r["circuit_id"]] = entry
        if r["method"] == "mps":
            if r["parameters"].get("svd_cutoff", 0.0) != 0.0:
                continue
            key = (r["circuit_id"], r["parameters"]["chi"])
            if key in mps:
                raise ValueError("Ambiguous MPS parameters for an S2 chi")
            mps[key] = entry

    cids = [f"Duke_S2_{q}" for q in range(16)]
    if set(refs) != set(cids):
        raise ValueError("Complete S2 exact references are required")
    truth = [refs[c]["record"]["estimate"] for c in cids]
    provenance = {}
    result = []
    for levels in WINDOWS:
        if any(levels[i + 1] != 2 * levels[i] for i in range(3)):
            raise ValueError("Geometric test requires equally spaced log precision")
        rows, direct, held_out, next_estimates, limits = [], [], [], [], []
        for cid in cids:
            sources = [mps[(cid, chi)] for chi in levels]
            reference = refs[cid]
            for source in sources + [reference]:
                r = source["record"]
                if r["qasm_sha256"] != reference["record"]["qasm_sha256"]:
                    raise ValueError(f"Input hash mismatch for {cid}")
                if source["action_input_sha256"] != r["qasm_sha256"]:
                    raise ValueError(f"Action/record input hash mismatch for {cid}")
                provenance[source["key"]] = {
                    key: value for key, value in source.items() if key != "record"
                }
                provenance[source["key"]].update(
                    circuit_id=cid, method=r["method"], parameters=r["parameters"],
                    input_sha256=r["qasm_sha256"], backend=r["backend"],
                    estimate=r["estimate"],
                )
            a, b, c, d = [source["record"]["estimate"] for source in sources]
            delta1, delta2 = b - a, c - b
            ratio = delta2 / delta1 if abs(delta1) > DENOMINATOR_FLOOR else None
            if ratio is None:
                rejection = "FIRST_DIFFERENCE_TOO_SMALL"
            elif not 0 < ratio < RATIO_CEILING:
                rejection = "NOT_SAME_SIGN_STRICT_CONTRACTION"
            else:
                rejection = None
            eligible = rejection is None
            forecast = c + delta2 * ratio if eligible else c
            limit = c + delta2 * ratio / (1 - ratio) if eligible else c
            exact = reference["record"]["estimate"]
            rows.append({
                "circuit_id": cid, "precision_values": [a, b, c, d],
                "exact_reference": exact, "fit_record_keys": [s["key"] for s in sources[:3]],
                "held_out_record_key": sources[3]["key"],
                "reference_record_key": reference["key"],
                "consecutive_difference_ratio": ratio, "eligible": eligible,
                "fallback_reason": rejection, "predicted_next_value": forecast,
                "extrapolated_limit_or_direct_fallback": limit,
                "held_out_forecast_abs_error": abs(forecast - d),
                "held_out_direct_abs_error": abs(c - d),
                "limit_exact_abs_error": abs(limit - exact),
                "direct_exact_abs_error": abs(c - exact),
            })
            direct.append(c)
            held_out.append(d)
            next_estimates.append(forecast)
            limits.append(limit)
        forecast_metrics, direct_metrics = errors(next_estimates, held_out), errors(direct, held_out)
        direct_score, limit_score = score(direct, truth), score(limits, truth)
        result.append({
            "fit_chis": list(levels[:3]), "held_out_chi": levels[3],
            "row_count": len(rows), "extrapolated_rows": sum(r["eligible"] for r in rows),
            "fallback_counts": dict(Counter(r["fallback_reason"] for r in rows if not r["eligible"])),
            "forecast_better_rows": sum(r["held_out_forecast_abs_error"] < r["held_out_direct_abs_error"] for r in rows),
            "forecast_worse_rows": sum(r["held_out_forecast_abs_error"] > r["held_out_direct_abs_error"] for r in rows),
            "held_out_finer_level": {"forecast": forecast_metrics, "direct": direct_metrics},
            "against_exact": {
                "direct": {"local_score": direct_score, **errors(direct, truth)},
                "extrapolated_with_fallback": {"local_score": limit_score, **errors(limits, truth)},
                "held_out_finer_direct": {"local_score": score(held_out, truth), **errors(held_out, truth)},
                "extrapolated_score_gain": limit_score - direct_score,
            },
            "held_out_mae_improved": forecast_metrics["mae"] < direct_metrics["mae"],
            "exact_score_not_degraded": limit_score >= direct_score - 1e-10,
            "rows": rows,
        })
    inventory = {}
    for problem, methods in sorted(coverage.items()):
        inventory[problem] = {}
        for method, pairs in sorted(methods.items()):
            counts = Counter(parameter for _, parameter in pairs)
            inventory[problem][method] = [
                {"parameter": parameter, "successful_rows": count}
                for parameter, count in sorted(counts.items())
            ]
    return result, provenance, inventory


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--records", type=Path, default=REPO / "runs" / "experiments")
    parser.add_argument("--output", type=Path, default=REPO / "reports" / "extrapolation_rejection.json")
    args = parser.parse_args()
    entries, record_count = read_records(args.records)
    windows, provenance, inventory = evaluate(entries)
    passed = all(w["held_out_mae_improved"] and w["exact_score_not_degraded"] for w in windows)
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "scope": "Offline S2 MPS replay of saved local sample outputs; no new simulations or submissions",
        "status": "CANDIDATE_PASSED_LOCAL_TEST" if passed else "THIS_CANDIDATE_REJECTED",
        "model": {
            "name": "Same-sign contracting geometric differences / Aitken limit",
            "fit": "For a=F(chi), b=F(2chi), c=F(4chi): r=(c-b)/(b-a)",
            "next_prediction": "F(8chi)=c+(c-b)*r",
            "limit": "F(infinity)=c+(c-b)*r/(1-r)",
            "eligibility": f"abs(b-a)>{DENOMINATOR_FLOOR} and 0<r<{RATIO_CEILING}",
            "fallback": "Use c directly whenever eligibility fails; no clipping or fitted correction",
            "selection": "Fixed illustrative candidate; no gate or coefficient optimization against labels",
            "acceptance": "Both windows must improve held-out next-level MAE and avoid exact-score degradation",
        },
        "record_selection": {
            "directory": relative(args.records), "files_read": record_count,
            "policy": "Latest saved successful finite estimate for each circuit/method/full parameter signature; S2 MPS cutoff=0",
            "input_hashes_verified": True, "script_path": relative(Path(__file__)),
            "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        },
        "precision_coverage": inventory,
        "windows": windows,
        "provenance": provenance,
        "limitations": [
            "This rejects the stated candidate on these windows, not all extrapolation models.",
            "A held-out finer estimate is a trend target; only exact sample labels measure actual error.",
            "The two windows overlap and the 16 observables come from one problem family; they are not independent circuit-level folds.",
            "Local MPS and native BlueQubit kernels can behave differently; no native or graded convergence claim follows.",
            "S1 is a small saturated sample; S3 lacks three complete MPS precision levels; neither supplies a comparable independent extrapolation test.",
            "Scores use the local 100*max(0,Pearson rho)^2 replica, not an official scoring call.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(f"{report['status']}: {relative(args.output)}")
    for w in windows:
        held = w["held_out_finer_level"]
        exact = w["against_exact"]
        print(f"chi {w['fit_chis']} -> {w['held_out_chi']}: held-out MAE "
              f"{held['forecast']['mae']:.8f} vs direct {held['direct']['mae']:.8f}; "
              f"exact score {exact['extrapolated_with_fallback']['local_score']:.8f} "
              f"vs direct {exact['direct']['local_score']:.8f}")


if __name__ == "__main__":
    main()
