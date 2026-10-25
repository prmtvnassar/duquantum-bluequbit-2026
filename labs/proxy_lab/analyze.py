"""Score every method/prior/combination against the exact proxy vectors and print markdown tables.
Usage: python analyze.py [--fit-seed=1]   (reads data/exact_*.json and data/methods_*.json, writes data/summary.json)"""
import json
import os
import sys
from collections import defaultdict

import numpy as np

from common import DATA, load_instances, pearson2, score, slack, contact_layer, g4_layers

CHIS = [8, 16, 32, 64, 128]
EPSS = ["0.01", "0.001", "0.0001"]


def zs(v):
    v = np.asarray(v, float)
    s = np.std(v)
    return (v - v.mean()) / s if s > 0 else np.zeros_like(v)


def front_prior(d, d0, w):
    return 1.0 / (1.0 + np.exp(-(np.asarray(d, float) - d0) / w))


def fit_front(d, exact):
    best = (-1, None)
    for d0 in np.arange(-1, d.max() + 2, 0.5):
        for w in (0.25, 0.5, 1.0, 2.0, 4.0):
            s = pearson2(front_prior(d, d0, w), exact)
            if s > best[0]:
                best = (s, (float(d0), w))
    return best[1]


def shrink(v_hi, v_lo, s):
    v_hi, v_lo = np.asarray(v_hi, float), np.asarray(v_lo, float)
    m = v_hi.mean()
    return m + (v_hi - m) * np.exp(-np.abs(v_hi - v_lo) / s)


def blend(v, prior, a):
    return (1 - a) * zs(v) + a * zs(prior)


def slack_table(inst, exclude=()):
    """Pooled signed mean / mean|v| of the exact value as a function of slack, over all instances not excluded."""
    pool = defaultdict(list)
    for nm, d in inst.items():
        if nm in exclude:
            continue
        s = slack(d["rows"], d["cols"], d["depth"], d["butterfly"])
        for q, v in enumerate(d["exact"]):
            pool[int(s[q])].append(v)
    return {s: (float(np.mean(v)), float(np.mean(np.abs(v))), float(np.std(v)), len(v)) for s, v in pool.items()}


def slack_prior(svec, table, signed=True):
    out = np.zeros(len(svec))
    for i, s in enumerate(svec):
        s = int(s)
        if s < 0:
            out[i] = 1.0
        elif s in table:
            out[i] = table[s][0] if signed else table[s][1]
        else:  # fall back to the nearest tabulated slack
            k = min(table, key=lambda t: abs(t - s) if t >= 0 else 99)
            out[i] = table[k][0] if signed else table[k][1]
    return out


def main():
    opts = dict(a[2:].split("=", 1) for a in sys.argv[1:] if a.startswith("--") and "=" in a)
    fit_seed = int(opts.get("fit-seed", "1"))
    inst = load_instances()
    methods = {}
    for name in inst:
        p = os.path.join(DATA, f"methods_{name}.json")
        methods[name] = json.load(open(p)) if os.path.exists(p) else {"mps": {}, "pps": {}}
    groups = defaultdict(list)
    for name, d in inst.items():
        groups[(d["rows"], d["cols"], d["depth"])].append(name)
    summary = {}
    lines = []
    # ---- 1. structure of the exact vectors by Manhattan distance
    lines.append("## Exact OTOC(2) vectors: structure by Manhattan distance from the corner butterfly\n")
    lines.append("| grid | depth | n_inst | noise floor 2^-n/2 | mean abs v (all) | mean abs v by distance d (max over inst) | rho(v,d) mean [min,max] | abs v at far corner (per inst) |")
    lines.append("|---|---|---|---|---|---|---|---|")
    for key in sorted(groups):
        R, C, depth = key
        names = groups[key]
        n = R * C
        dvec = np.array(inst[names[0]]["manhattan"])
        byd = {dd: max(np.abs(np.array(inst[nm]["exact"]))[dvec == dd].mean() for nm in names) for dd in sorted(set(dvec))}
        rhos = [np.corrcoef(inst[nm]["exact"], dvec)[0, 1] for nm in names]
        far = [abs(inst[nm]["exact"][n - 1]) for nm in names]
        allabs = np.mean([np.abs(inst[nm]["exact"]).mean() for nm in names])
        lines.append(f"| {R}x{C} | {depth} | {len(names)} | {2**(-n/2):.4f} | {allabs:.4f} | "
                     + " ".join(f"d{dd}:{v:.3f}" for dd, v in byd.items())
                     + f" | {np.mean(rhos):+.2f} [{min(rhos):+.2f},{max(rhos):+.2f}] | "
                     + " ".join(f"{f:.3f}" for f in far) + " |")
        summary[f"{R}x{C}_d{depth}"] = {"noise_floor": 2 ** (-n / 2), "mean_abs": allabs,
                                         "abs_by_distance_max": {int(k): float(v) for k, v in byd.items()},
                                         "rho_v_d": [float(r) for r in rhos], "far_corner_abs": far}
    # ---- 1b. structure by slack (layers since the qubit entered the support of W = U^dag X_0 U)
    lines.append("\n## Exact value versus slack = depth - contact layer (pooled over all instances and groups)\n")
    lines.append("slack -1 = never reached (value exactly +1). Contact is counted through the layers of U in reverse order, "
                 "because X_0 is conjugated by the last layer of U first.\n")
    lines.append("| slack | n values | mean v (signed) | std v | mean abs v | frac v<0 |")
    lines.append("|---|---|---|---|---|---|")
    pool = defaultdict(list)
    for nm, d in inst.items():
        s = slack(d["rows"], d["cols"], d["depth"], d["butterfly"])
        for q, v in enumerate(d["exact"]):
            pool[int(s[q])].append(v)
    tab = {}
    for s in sorted(pool):
        a = np.array(pool[s])
        lines.append(f"| {s} | {len(a)} | {a.mean():+.3f} | {a.std():.3f} | {np.abs(a).mean():.3f} | {(a < 0).mean():.2f} |")
        tab[s] = {"n": len(a), "mean": float(a.mean()), "std": float(a.std()), "mean_abs": float(np.abs(a).mean()), "frac_neg": float((a < 0).mean())}
    summary["by_slack_pooled"] = tab
    lines.append("\nPer group (mean v / mean abs v by slack):\n")
    for key in sorted(groups):
        R, C, depth = key
        g = defaultdict(list)
        for nm in groups[key]:
            s = slack(R, C, depth, inst[nm]["butterfly"])
            for q, v in enumerate(inst[nm]["exact"]):
                g[int(s[q])].append(v)
        lines.append(f"- {R}x{C} depth {depth}: " + ", ".join(f"s{s}: {np.mean(g[s]):+.3f}/{np.abs(g[s]).mean():.3f} (n{len(g[s])})" for s in sorted(g)))
    # ---- 1c. G4 geometry prediction from the pooled slack table
    tc = contact_layer(g4_layers(), 16, 0, 38)
    sg4 = (16 - tc).astype(int)
    full = slack_table(inst)
    pred_signed = slack_prior(sg4, full, signed=True)
    pred_abs = slack_prior(sg4, full, signed=False)
    lines.append("\n## G4 (6x6 + q36/q37, depth 16, butterfly q0): slack per qubit and the pooled-proxy prediction\n")
    lines.append("| q | row,col | Manhattan d | slack | predicted mean v | predicted abs v |")
    lines.append("|---|---|---|---|---|---|")
    for q in range(38):
        r, c = divmod(q, 6)
        lines.append(f"| {q} | {r},{c} | {r + c} | {sg4[q]} | {pred_signed[q]:+.3f} | {pred_abs[q]:.3f} |")
    summary["g4_prediction"] = {"slack": sg4.tolist(), "pred_signed": pred_signed.tolist(), "pred_abs": pred_abs.tolist()}
    # ---- 2. method scores per group
    lines.append("\n## Scores (agreement with the exact answer, 0-1000), mean over instances [min, max]\n")
    lines.append("Null baseline for an uncorrelated vector: E[score] = 1000/(n-1). 'LOO' = constants taken from all other instances (all groups).\n")
    for key in sorted(groups):
        R, C, depth = key
        names = groups[key]
        n = R * C
        dvec = np.array(inst[names[0]]["manhattan"])
        svec = slack(R, C, depth, inst[names[0]]["butterfly"])
        fit_name = next((nm for nm in names if nm.endswith(f"_s{fit_seed}")), names[0])
        test_names = [nm for nm in names if nm != fit_name] or names
        rows = defaultdict(dict)  # method -> instance -> score
        for nm in names:
            ex = np.array(inst[nm]["exact"])
            m = methods[nm]
            for chi in CHIS:
                if str(chi) in m["mps"]:
                    rows[f"MPS chi{chi}"][nm] = score(m["mps"][str(chi)], ex)
            avail = [c for c in CHIS if str(c) in m["mps"]]
            if len(avail) >= 2:
                rows["MPS mean over all chi"][nm] = score(np.mean([m["mps"][str(c)] for c in avail], axis=0), ex)
                rows["MPS mean top-2 chi"][nm] = score(np.mean([m["mps"][str(c)] for c in avail[-2:]], axis=0), ex)
                hi, lo = avail[-1], avail[-2]
                rows[f"MPS chi{hi} sign-agreement with exact (frac x1000)"][nm] = 1000 * np.mean(np.sign(m["mps"][str(hi)]) == np.sign(ex))
                rows[f"MPS chi{hi} vs chi{lo} self-consistency (agreement x1000)"][nm] = score(m["mps"][str(hi)], m["mps"][str(lo)])
                rows[f"MPS chi{hi} mean abs error x1000"][nm] = 1000 * np.mean(np.abs(np.array(m["mps"][str(hi)]) - ex))
            for eps in EPSS:
                if eps in m["pps"]:
                    vals = m["pps"][eps]
                    filled = np.array([0.0 if v is None else v for v in vals])
                    rows[f"PPS L3 eps {eps} (None->0)"][nm] = score(filled, ex)
                    rows[f"PPS L3 eps {eps} max abs value x1000"][nm] = 1000 * np.abs(filled).max()
            rows["prior: Manhattan distance"][nm] = score(dvec, ex)
            rows["prior: distance squared"][nm] = score(dvec ** 2, ex)
            rows["prior: exp(d)"][nm] = score(np.exp(dvec.astype(float)), ex)
            rows["prior: 1 outside support of W (slack<0)"][nm] = score((svec < 0).astype(float), ex)
            rows["prior: far-corner indicator"][nm] = score((dvec == dvec.max()).astype(float), ex)
            rows["prior: -slack"][nm] = score(-svec, ex)
            loo = slack_table(inst, exclude=(nm,))
            rows["prior: signed slack-mean table, LOO"][nm] = score(slack_prior(svec, loo, True), ex)
            rows["prior: abs slack-mean table, LOO"][nm] = score(slack_prior(svec, loo, False), ex)
            rng = np.random.default_rng(int(nm.split("_s")[-1]) + 1000)
            rows["random Gaussian vector (null)"][nm] = np.mean([score(rng.normal(size=n), ex) for _ in range(200)])
        # fitted priors / combos: fit on fit_name, test on the others
        ex_fit = np.array(inst[fit_name]["exact"])
        d0, w = fit_front(dvec, ex_fit)
        for nm in names:
            rows[f"prior: sigmoid front fitted on s{fit_seed} (d0={d0}, w={w})"][nm] = score(front_prior(dvec, d0, w), np.array(inst[nm]["exact"]))
        for nm in names:
            others = [o for o in names if o != nm] or [nm]
            params = [fit_front(dvec, np.array(inst[o]["exact"])) for o in others]
            d0l, wl = float(np.median([p[0] for p in params])), float(np.median([p[1] for p in params]))
            rows["prior: sigmoid front, LOO within group"][nm] = score(front_prior(dvec, d0l, wl), np.array(inst[nm]["exact"]))
        mfit = methods[fit_name]
        avail = [c for c in CHIS if all(str(c) in methods[nm]["mps"] for nm in names)]
        if len(avail) >= 2:
            hi, lo = avail[-1], avail[-2]
            best = max(((pearson2(shrink(mfit["mps"][str(hi)], mfit["mps"][str(lo)], s), ex_fit), s)
                        for s in (0.005, 0.01, 0.02, 0.05, 0.1, 0.2, 0.5, 1.0)))
            s_best = best[1]
            for nm in names:
                m = methods[nm]
                rows[f"combo: chi{hi} shrunk toward mean by exp(-abs(chi{hi}-chi{lo})/s), s={s_best} fitted on s{fit_seed}"][nm] = \
                    score(shrink(m["mps"][str(hi)], m["mps"][str(lo)], s_best), np.array(inst[nm]["exact"]))
            for label, prior_of in (("distance", lambda nm: dvec), ("front", lambda nm: front_prior(dvec, d0, w)),
                                    ("signed slack table LOO", lambda nm: slack_prior(svec, slack_table(inst, exclude=(nm,)), True))):
                best = max(((pearson2(blend(mfit["mps"][str(hi)], prior_of(fit_name), a), ex_fit), a) for a in np.linspace(0, 1, 21)))
                a_best = float(best[1])
                for nm in names:
                    m = methods[nm]
                    rows[f"combo: (1-a) z(chi{hi}) + a z({label}), a={a_best:.2f} fitted on s{fit_seed}"][nm] = \
                        score(blend(m["mps"][str(hi)], prior_of(nm), a_best), np.array(inst[nm]["exact"]))
            # MPS error by slack band (is the structured edge captured?)
            for nm in names:
                m = methods[nm]
                ex = np.array(inst[nm]["exact"])
                est = np.array(m["mps"][str(hi)])
                band = svec <= 6
                if band.sum() >= 3 and (~band).sum() >= 3:
                    rows[f"MPS chi{hi} score restricted to slack<=6 qubits"][nm] = score(est[band], ex[band])
        lines.append(f"\n### {R}x{C}, depth {depth} (n={n}, {len(names)} instances, null = {1000/(n-1):.0f}; fitted constants from s{fit_seed}, held-out = other instances)\n")
        lines.append("| method | mean | [min, max] | held-out mean | per instance |")
        lines.append("|---|---|---|---|---|")
        gsum = {}
        for meth, sc in rows.items():
            vals = [sc[nm] for nm in names if nm in sc]
            held = [sc[nm] for nm in test_names if nm in sc]
            hmean = np.mean(held) if held else float("nan")
            lines.append(f"| {meth} | {np.mean(vals):.0f} | [{min(vals):.0f}, {max(vals):.0f}] | {hmean:.0f} | "
                         + " ".join(f"{v:.0f}" for v in vals) + " |")
            gsum[meth] = {"mean": float(np.mean(vals)), "min": float(min(vals)), "max": float(max(vals)),
                          "held_out_mean": float(np.mean(held)) if held else None,
                          "per_instance": {nm: float(sc[nm]) for nm in names if nm in sc}}
        summary[f"{R}x{C}_d{depth}"]["scores"] = gsum
    text = "\n".join(lines)
    print(text)
    json.dump(summary, open(os.path.join(DATA, "summary.json"), "w"), indent=1)
    open(os.path.join(DATA, "tables.md"), "w").write(text)


if __name__ == "__main__":
    main()
