"""Post-processing estimators built from local MPS features, scored against the exact
sample references. $0, no BlueQubit client, deterministic.

Inputs : scratch/sample_lab/features_S2.json, features_S3.json (from mps_features.py)
         submissions/S2/attempt-01.csv, submissions/S3/attempt-01.csv (exact references)
Outputs: scratch/sample_lab/results.json and results.md (tables consumed by the report)

    .venv312/Scripts/python.exe scratch/sample_lab/estimators.py

Metric: score = 100 * Pearson(est, exact)^2 over the full vector of one sample; also
max abs error of the estimator values themselves (not affine-rescaled).

Held-out protocol: every data-driven choice (shrinkage threshold, ridge weights) is
fitted on one sample family and evaluated on the other; nothing is fitted and
evaluated on the same family.
"""

import csv
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]

GEOMETRY = {
    # sample: (butterfly, coordinates function)
    "S2": (0, lambda j: (0, j)),          # 16-site chain
    "S3": (14, lambda j: divmod(j, 6)),   # 5x6 grid, qubit = row*6 + col
}
CHIS = {"S2": [2, 4, 8, 16, 32, 64, 128], "S3": [4, 8, 16, 32, 64]}
# chi levels regarded as the "unconverged" analogue of G4 (raw score well below 100)
UNCONVERGED = {"S2": [4, 8, 16], "S3": [8, 16]}


def manhattan(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def load_exact(sample):
    path = ROOT / "submissions" / sample / "attempt-01.csv"
    with path.open() as fh:
        return {row["circuit_id"]: float(row["value"]) for row in csv.DictReader(fh)}


def load_features(sample):
    """Main sweep file plus any *_partN.json produced by parallel workers (same IDs/chis merge by union)."""
    data = json.loads((HERE / f"features_{sample}.json").read_text())
    for part in sorted(HERE.glob(f"features_{sample}_part*.json")):
        for key, entry in json.loads(part.read_text()).items():
            data.setdefault(key, {"qubit": entry["qubit"], "num_qubits": entry["num_qubits"], "chi": {}})
            for chi, feats in entry["chi"].items():
                data[key]["chi"].setdefault(chi, feats)
    return data


def score(est, exact):
    est, exact = np.asarray(est, float), np.asarray(exact, float)
    if np.std(est) < 1e-12 or np.std(exact) < 1e-12:
        return 0.0
    r = np.corrcoef(est, exact)[0, 1]
    return float(100 * r * r)


def row_features(sample, feats, chi, chis_available):
    """Per-row scalar features for one ID at bond cap chi (and the next-lower chi)."""
    b, coord = GEOMETRY[sample]
    q, n = feats["qubit"], feats["num_qubits"]
    f = feats["chi"][str(chi)]
    Z, X, Y = np.array(f["Z"]), np.array(f["X"]), np.array(f["Y"])
    dist_b = np.array([manhattan(coord(j), coord(b)) for j in range(n)])
    dist_q = np.array([manhattan(coord(j), coord(q)) for j in range(n)])
    min_dist = np.minimum(dist_b, dist_q)
    far_k = max(3, n // 4)
    far = np.argsort(-min_dist, kind="stable")[:far_k]
    lower = [c for c in chis_available if c < chi]
    prev = feats["chi"][str(max(lower))]["Z"][q] if lower else None
    out = {
        "zq": Z[q], "meanZ": Z.mean(), "meanZ_far": Z[far].mean(), "zb": Z[b],
        "meanZ_notq": np.delete(Z, q).mean(),
        "min_far_Z": Z[far].min(),
        "xq": X[q], "yq": Y[q], "mean_absX": np.abs(X).mean(), "mean_absY": np.abs(Y).mean(),
        "dist_qb": manhattan(coord(q), coord(b)), "dist_norm": manhattan(coord(q), coord(b)) / max(dist_b.max(), 1),
        "log_norm2": np.log10(max(f["norm_squared"], 1e-300)),
        "max_entropy": max(f["entropy"]), "mean_entropy": float(np.mean(f["entropy"])),
        "zq_prev": prev,
        "instab": abs(Z[q] - prev) if prev is not None else np.nan,
        "signflip": float(prev is not None and np.sign(prev) != np.sign(Z[q]) and abs(Z[q]) > 1e-9),
    }
    return out


def build_table(sample):
    feats, exact = load_features(sample), load_exact(sample)
    ids = sorted(feats, key=lambda k: feats[k]["qubit"])
    if len(ids) != {"S2": 16, "S3": 30}[sample]:
        return {}
    chis = [c for c in CHIS[sample] if all(str(c) in feats[k]["chi"] for k in ids)]
    table = {}
    for chi in chis:
        rows = [row_features(sample, feats[k], chi, chis) for k in ids]
        table[chi] = {"ids": ids, "exact": np.array([exact[k] for k in ids]),
                      "rows": {key: np.array([r[key] for r in rows], float) for key in rows[0]}}
    return table


# ---------------------------------------------------------------- estimators (b)

def closed_form_estimators(R):
    """Estimators needing no fitted parameters; each returns a vector."""
    eps = 1e-9
    zq, mZ, mF, zb, mNq = R["zq"], R["meanZ"], R["meanZ_far"], R["zb"], R["meanZ_notq"]
    return {
        "raw": zq,
        "zq/meanZ": zq / np.where(np.abs(mZ) < eps, eps, mZ),
        "zq-meanZ": zq - mZ,
        "zq/meanZ_far": zq / np.where(np.abs(mF) < eps, eps, mF),
        "zq-meanZ_far": zq - mF,
        "zq/meanZ_notq": zq / np.where(np.abs(mNq) < eps, eps, mNq),
        "zq-zb": zq - zb,
        "(zq-(1-mF))/mF": (zq - (1 - mF)) / np.where(np.abs(mF) < eps, eps, mF),
        "zq*(1-dist_norm)": zq * (1 - R["dist_norm"]),
        "-dist_norm(prior only)": -R["dist_norm"],
        "meanZ(alone)": mZ,
        "meanZ_notq(alone)": mNq,
        "zb(alone)": zb,
        "0.5*(zq+meanZ_notq)": 0.5 * (zq + mNq),
        "mean(zq,zq_prev)": 0.5 * (zq + np.nan_to_num(R["zq_prev"], nan=0.0)) if not np.isnan(R["zq_prev"]).all() else zq,
    }


# ---------------------------------------------------------------- estimators (c)

def shrink(R, tau, mode):
    zq, inst = R["zq"], R["instab"]
    if np.isnan(inst).all():
        return zq.copy()
    inst = np.nan_to_num(inst, nan=0.0)
    if mode == "hard":
        w = (inst > tau).astype(float)
    else:  # soft: linear ramp up to full shrinkage at 2*tau
        w = np.clip(inst / (2 * tau), 0, 1)
    stable_mean = zq[w < 1].mean() if (w < 1).any() else zq.mean()
    return (1 - w) * zq + w * stable_mean


def fit_tau(R, exact, mode, grid):
    best = max(grid, key=lambda t: score(shrink(R, t, mode), exact))
    return best


# ---------------------------------------------------------------- estimators (d)

RIDGE_FEATURES = ["zq", "meanZ", "zb", "dist_norm", "instab"]
RIDGE_FEATURES_EXT = RIDGE_FEATURES + ["meanZ_far", "signflip", "xq", "max_entropy", "zq_prev"]


def design(R, names):
    cols = [np.nan_to_num(R[k], nan=0.0) for k in names]
    return np.column_stack(cols)


def ridge_fit(Xtr, ytr, lam):
    mu, sd = Xtr.mean(0), Xtr.std(0) + 1e-12
    Xs = (Xtr - mu) / sd
    A = Xs.T @ Xs + lam * np.eye(Xs.shape[1])
    w = np.linalg.solve(A, Xs.T @ (ytr - ytr.mean()))
    return {"mu": mu, "sd": sd, "w": w, "b": ytr.mean()}


def ridge_predict(model, X):
    return ((X - model["mu"]) / model["sd"]) @ model["w"] + model["b"]


# ---------------------------------------------------------------- evaluation

def evaluate():
    tables = {s: build_table(s) for s in CHIS if (HERE / f"features_{s}.json").exists()}
    tables = {s: T for s, T in tables.items() if T}
    results = {s: {} for s in tables}
    pairs = [(a, b) for a, b in (("S2", "S3"), ("S3", "S2")) if a in tables and b in tables]
    lines = []

    # (a)+(b): closed-form, every chi, every sample
    for s, T in tables.items():
        for chi, D in T.items():
            res = {}
            for name, est in closed_form_estimators(D["rows"]).items():
                res[name] = {"score": score(est, D["exact"]), "maxerr": float(np.max(np.abs(est - D["exact"])))}
            results[s][chi] = res

    # (c): shrinkage, threshold fitted on the other sample at every chi (pooled over its chis)
    grid = [0.01, 0.02, 0.03, 0.05, 0.075, 0.1, 0.15, 0.2, 0.3, 0.5, 1.0]
    taus = {}
    for test, train in pairs:
        Ttr = tables[train]
        for mode in ("hard", "soft"):
            # pooled fit: choose tau maximising mean score over the training family's unconverged chis
            def pooled(t):
                vals = [score(shrink(Ttr[c]["rows"], t, mode), Ttr[c]["exact"])
                        for c in UNCONVERGED[train] if c in Ttr and not np.isnan(Ttr[c]["rows"]["instab"]).all()]
                return np.mean(vals) if vals else 0.0
            tau = max(grid, key=pooled)
            taus[(test, mode)] = tau
            for chi, D in tables[test].items():
                est = shrink(D["rows"], tau, mode)
                results[test][chi][f"shrink_{mode}(tau={tau} from {train})"] = {
                    "score": score(est, D["exact"]), "maxerr": float(np.max(np.abs(est - D["exact"])))}

    # (d): ridge, train on one family (per-chi and pooled over chis), test on the other at every chi
    for test, train in pairs:
        Ttr, Tte = tables[train], tables[test]
        for fname, names in (("ridge5", RIDGE_FEATURES), ("ridge10", RIDGE_FEATURES_EXT)):
            for lam in (1.0, 10.0):
                # pooled over all training chis (with instab defined)
                tr_chis = [c for c in Ttr if not np.isnan(Ttr[c]["rows"]["instab"]).all()]
                Xtr = np.vstack([design(Ttr[c]["rows"], names) for c in tr_chis])
                ytr = np.concatenate([Ttr[c]["exact"] for c in tr_chis])
                model = ridge_fit(Xtr, ytr, lam)
                for chi, D in Tte.items():
                    est = ridge_predict(model, design(D["rows"], names))
                    results[test][chi][f"{fname}_pooled(lam={lam:g}, from {train})"] = {
                        "score": score(est, D["exact"]), "maxerr": float(np.max(np.abs(est - D["exact"])))}
                # unconverged-only training (closest analogue of G4)
                tr_chis_u = [c for c in UNCONVERGED[train] if c in tr_chis]
                Xtr = np.vstack([design(Ttr[c]["rows"], names) for c in tr_chis_u])
                ytr = np.concatenate([Ttr[c]["exact"] for c in tr_chis_u])
                model = ridge_fit(Xtr, ytr, lam)
                for chi, D in Tte.items():
                    est = ridge_predict(model, design(D["rows"], names))
                    results[test][chi][f"{fname}_unconv(lam={lam:g}, from {train})"] = {
                        "score": score(est, D["exact"]), "maxerr": float(np.max(np.abs(est - D["exact"])))}
                if fname == "ridge5" and lam == 1.0:
                    results[test][f"ridge5_unconv_weights_from_{train}"] = {
                        "features": names, "w_standardised": model["w"].round(4).tolist(), "b": round(float(model["b"]), 4)}

    # ----- markdown tables
    for s in tables:
        chis = [c for c in tables[s]]
        names = [k for k in results[s][chis[0]] if isinstance(results[s][chis[0]][k], dict)]
        lines.append(f"\n### {s} (held-out family for fitted estimators), score = 100*rho^2 (max abs err)\n")
        lines.append("| estimator | " + " | ".join(f"chi{c}" for c in chis) + " |")
        lines.append("|---|" + "---|" * len(chis))
        for name in names:
            cells = []
            for c in chis:
                r = results[s][c].get(name)
                cells.append(f"{r['score']:.1f} ({r['maxerr']:.2f})" if r else "-")
            lines.append(f"| {name} | " + " | ".join(cells) + " |")
        # raw vs best-nonraw summary on unconverged chis
        lines.append("")
        for c in UNCONVERGED[s]:
            if c not in results[s]:
                continue
            raw = results[s][c]["raw"]["score"]
            best = max(((k, v["score"]) for k, v in results[s][c].items() if isinstance(v, dict) and k != "raw"), key=lambda kv: kv[1])
            lines.append(f"- chi{c}: raw {raw:.1f}; best other = {best[0]} at {best[1]:.1f} ({best[1]-raw:+.1f})")
    lines.append("\nFitted shrinkage thresholds: " + ", ".join(f"{k[0]}/{k[1]}: tau={v}" for k, v in taus.items()))
    for s in tables:
        for k, v in results[s].items():
            if isinstance(k, str) and k.startswith("ridge5_unconv_weights"):
                lines.append(f"{s} {k}: {v}")

    # ----- per-row dump at unconverged chis (for the report's diagnostics)
    lines.append("\n### Per-row raw vs exact at unconverged chis\n")
    for s in tables:
        for c in UNCONVERGED[s]:
            D = tables[s][c]
            lines.append(f"{s} chi{c}: " + ", ".join(
                f"q{int(D['rows']['dist_qb'][i]) if False else D['ids'][i].split('_')[-1]}={D['rows']['zq'][i]:+.3f}/{D['exact'][i]:+.3f}"
                for i in range(len(D["ids"]))))

    out_md = "\n".join(lines)
    (HERE / "results.md").write_text(out_md)
    (HERE / "results.json").write_text(json.dumps(
        {s: {str(c): v for c, v in results[s].items()} for s in results}, indent=1, default=float))
    print(out_md)


if __name__ == "__main__":
    evaluate()
