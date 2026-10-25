"""Analyse the local PPS eps ladders against exact vectors (4x6 seeds + PG4c with native references).
Usage: python analyze.py  -> prints tables, writes data/summary.json.   $0, local."""
import csv, json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "labs", "proxy_lab")); sys.path.insert(0, HERE)
import numpy as np
from common import pearson2
DATA = os.path.join(HERE, "data")
sc = lambda a, b: 1000 * pearson2(a, b)
rho = lambda a, b: float(np.corrcoef(a, b)[0, 1]) if np.std(a) > 0 and np.std(b) > 0 else 0.0


def load_instance(name):
    if name == "pg4c":
        rows = list(csv.DictReader(open(os.path.join(ROOT, "labs", "pg4c", "pg4c.csv"))))
        f = lambda k: np.array([float(r[k]) if r[k] else np.nan for r in rows])
        from run_ladder import pg4c_slack
        inst = {"exact": f("exact"), "slack": pg4c_slack(), "n": 32,
                "native": {"pps1e-4": f("pps1e4L3"), "pps1e-3": f("pps1e3L3"), "mps128": f("mps128")}}
    else:
        p = os.path.join(DATA, f"exact_{name}.json")
        if not os.path.exists(p):
            return None
        d = json.load(open(p))
        inst = {"exact": np.array(d["exact"]), "slack": np.array(d["slack"], float), "n": d["num_qubits"], "native": {}}
    lp = os.path.join(DATA, f"ladder_{name}.json")
    inst["ladder"], inst["diag"], inst["sec"] = {}, {}, {}
    if os.path.exists(lp):
        L = json.load(open(lp))
        for e, vals in L["pps"].items():
            if len(vals) < inst["n"]:
                continue  # incomplete eps level
            v = np.array([vals[str(q)] if vals[str(q)] is not None else np.nan for q in range(inst["n"])])
            inst["ladder"][float(e)] = v
            inst["diag"][float(e)] = L["diag"][e]; inst["sec"][float(e)] = L["seconds"][e]
    mp = os.path.join(DATA, f"mps_{name}.json")
    inst["mps"] = {}
    if os.path.exists(mp):
        M = json.load(open(mp))
        for c, vals in M["mps"].items():
            if len(vals) == inst["n"]:
                inst["mps"][int(c)] = np.array([vals[str(q)] for q in range(inst["n"])], float)
    return inst


def z0(v):  # NaN (term cap hit) -> 0, as a service refusal would leave the row empty
    return np.where(np.isfinite(v), v, 0.0)


def stable_rule(epss, ladder, thr=0.5):
    """Per row: finest eps k such that v_k and v_{k-1} (next coarser) are both nonzero and
    |v_k - v_{k-1}| < thr * max(|v_k|, |v_{k-1}|); else 0."""
    n = len(ladder[epss[0]]); out = np.zeros(n); used = np.full(n, -1)
    for k in range(len(epss) - 1, 0, -1):  # finest first
        a, b = z0(ladder[epss[k]]), z0(ladder[epss[k - 1]])
        ok = (a != 0) & (b != 0) & (np.abs(a - b) < thr * np.maximum(np.abs(a), np.abs(b))) & (used < 0)
        out[ok] = a[ok]; used[ok] = k
    return out, used


def residual(y, cols):
    X = np.column_stack([np.ones(len(y))] + list(cols))
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    return y - X @ beta


def analyze(name, inst, summary):
    ex, sl, n = inst["exact"], inst["slack"], inst["n"]
    rim = (sl >= 3) & (sl <= 7)
    epss = sorted(inst["ladder"], reverse=True)  # coarse -> fine
    S = summary.setdefault(name, {"n": n, "rim_rows": [int(q) for q in np.flatnonzero(rim)], "per_eps": {}})
    print(f"\n=== {name} (n={n}) exact: mean|v| {np.abs(ex).mean():.4f}, rim mean|v| {np.abs(ex[rim]).mean():.4f}, "
          f"frac rim<0 {np.mean(ex[rim] < 0):.2f}, max|v| {np.abs(ex).max():.3f}")
    print("rim rows (slack):", " ".join(f"q{q}({int(sl[q])})" for q in np.flatnonzero(rim)))
    for e in epss:
        v = inst["ladder"][e]; d = inst["diag"][e]; sec = inst["sec"][e]
        vz = z0(v)
        nz = np.flatnonzero(vz != 0); capped = np.flatnonzero(~np.isfinite(v))
        peaks = [d[str(q)]["peak_num_paulis"] or 0 for q in range(n)]
        rec = {"score": sc(ex, vz), "rho": rho(ex, vz), "score_rim": sc(ex[rim], vz[rim]),
               "nonzero_rows": [int(q) for q in nz], "nonzero_rim": int((vz[rim] != 0).sum()),
               "capped_rows": [int(q) for q in capped], "peak_terms_max": int(max(peaks)),
               "peak_terms_median": int(np.median(peaks)), "sec_max": max(sec.values()), "sec_sum": sum(sec.values()),
               "sign_agree_rim": float(np.mean(np.sign(vz[rim]) == np.sign(ex[rim]))) if (vz[rim] != 0).any() else 0.0,
               "rim_values": {int(q): float(vz[q]) for q in np.flatnonzero(rim)}}
        S["per_eps"][f"{e:g}"] = rec
        print(f"eps {e:7.0e}: score {rec['score']:6.1f} rho {rec['rho']:+.2f} | rim-only {rec['score_rim']:6.1f} | "
              f"nonzero {len(nz)}/{n} (rim {rec['nonzero_rim']}/{rim.sum()}) capped {len(capped)} | "
              f"peak terms max {rec['peak_terms_max']:.2e} med {rec['peak_terms_median']:.2e} | "
              f"max {rec['sec_max']:.0f}s sum {rec['sec_sum'] / 60:.0f}min | rim sign agree {rec['sign_agree_rim']:.2f}")
    for k, v in inst["native"].items():
        if np.isfinite(v).all():
            print(f"native {k:8s}: score {sc(ex, v):6.1f} rho {rho(ex, v):+.2f} | rim-only {sc(ex[rim], v[rim]):6.1f}")
            S[f"native_{k}"] = sc(ex, v)
    hdr = "   q sl   exact " + " ".join(f"{e:>8.0e}" for e in epss) + ("  nat1e-4  nat1e-3" if inst["native"] else "")
    print(hdr)
    for q in np.flatnonzero(rim):
        cells = []
        for e in epss:
            x = inst["ladder"][e][q]
            cells.append("   cap  " if not np.isfinite(x) else f"{x:+8.4f}")
        line = f"  q{q:2d} {int(sl[q]):2d} {ex[q]:+.4f} " + " ".join(cells)
        if inst["native"]:
            line += f" {inst['native']['pps1e-4'][q]:+8.4f} {inst['native']['pps1e-3'][q]:+8.4f}"
        print(line)
    if len(epss) < 2:
        return
    flips, pairs, improving = 0, 0, 0
    for k in range(1, len(epss)):
        a, b = z0(inst["ladder"][epss[k - 1]]), z0(inst["ladder"][epss[k]])
        both = (a != 0) & (b != 0) & rim
        flips += int((np.sign(a[both]) != np.sign(b[both])).sum()); pairs += int(both.sum())
        improving += int((np.abs(b[both] - ex[both]) < np.abs(a[both] - ex[both])).sum())
    S["rim_adjacent_pairs_both_nonzero"] = pairs; S["rim_sign_flips"] = flips; S["rim_error_improves"] = improving
    print(f"rim rows, adjacent-eps pairs with both nonzero: {pairs}; sign flips {flips}; "
          f"|error| decreases at finer eps in {improving}/{pairs}")
    finest = z0(inst["ladder"][epss[-1]])
    st, used = stable_rule(epss, inst["ladder"])
    S["finest_score"] = sc(ex, finest); S["stable_rule_score"] = sc(ex, st); S["stable_rule_nonzero"] = int((st != 0).sum())
    print(f"finest eps {epss[-1]:g}: {sc(ex, finest):.1f} | stable rule (|change|<50% across adjacent eps, else 0): "
          f"{sc(ex, st):.1f} with {(st != 0).sum()} nonzero rows")
    for thr in (0.25, 1.0):
        st2, _ = stable_rule(epss, inst["ladder"], thr)
        print(f"   stable rule thr {thr}: {sc(ex, st2):.1f}")
    for k in range(1, len(epss)):
        base, fine = z0(inst["ladder"][epss[k - 1]]), z0(inst["ladder"][epss[k]])
        spl = base.copy(); spl[rim] = fine[rim]
        S[f"splice_{epss[k - 1]:g}_to_{epss[k]:g}"] = {"base": sc(ex, base), "splice_rim": sc(ex, spl), "fine_all": sc(ex, fine)}
        print(f"splice: base {epss[k - 1]:g} ({sc(ex, base):.1f}) with rim rows from {epss[k]:g} -> {sc(ex, spl):.1f} "
              f"(fine everywhere {sc(ex, fine):.1f})")
    stack = np.array([z0(inst["ladder"][e]) for e in epss])
    print(f"median over eps: {sc(ex, np.median(stack, 0)):.1f}; mean over eps: {sc(ex, stack.mean(0)):.1f}")
    nulls = {f"chi{c}": v for c, v in inst["mps"].items()}
    if "mps128" in inst["native"] and np.isfinite(inst["native"]["mps128"]).all():
        nulls["native_mps128"] = inst["native"]["mps128"]
    if nulls:
        for c, v in nulls.items():
            print(f"MPS {c}: score {sc(ex, v):.1f} rho {rho(ex, v):+.2f}")
        for e in epss:
            base = z0(inst["ladder"][e]); r_all = residual(base, nulls.values())
            parts = " ".join(f"{c}:{sc(ex, residual(base, [v])):.1f}" for c, v in nulls.items())
            S["per_eps"][f"{e:g}"]["residual_all_nulls"] = sc(ex, r_all)
            print(f"residual of eps {e:g} ({sc(ex, base):.1f}) -> all nulls {sc(ex, r_all):.1f} | single: {parts}")
        if inst["native"]:
            base = inst["native"]["pps1e-4"]
            print(f"residual of NATIVE 1e-4 ({sc(ex, base):.1f}) -> "
                  + " ".join(f"{c}:{sc(ex, residual(base, [v])):.1f}" for c, v in nulls.items()))


def main():
    summary = {}
    for name in ["4x6_d16_s1", "4x6_d16_s2", "4x6_d16_s3", "pg4c"]:
        inst = load_instance(name)
        if inst is None or not inst["ladder"]:
            print(f"\n=== {name}: no data"); continue
        analyze(name, inst, summary)
    json.dump(summary, open(os.path.join(DATA, "summary.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
