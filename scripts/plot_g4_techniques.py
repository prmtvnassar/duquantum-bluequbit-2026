"""Figures for the G4 alternative-technique campaign, read from the run ledger ($0, offline).

Outputs under reports/figures/g4_techniques/:
  g4_vectors.png        per-row estimates for every complete or partial G4 cohort
  g4_method_agreement.png  Pearson rho between G4 cohorts on their common rows
  delta_sensitivity.png native level-3 PPS value vs truncation threshold on check rows
  chi_sensitivity.png   MPS CPU value vs bond dimension on check rows
"""
import csv
import json
from collections import defaultdict
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

REPO = Path(__file__).resolve().parents[1]
OUT = REPO / "reports/figures/g4_techniques"
# dataviz reference palette, light mode, fixed slot order (never cycled past 6)
CAT = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300"]
INK, MUTED, GRID = "#1f2933", "#52606d", "#e4e7eb"

EXACT = {}
for prob in ("S2", "S3"):
    path = REPO / f"submissions/{prob}/attempt-01.csv"
    if path.exists():
        EXACT.update({r["circuit_id"]: float(r["value"]) for r in csv.DictReader(open(path))})


def label(device, params):
    p = json.loads(params) if params else {}
    if device.startswith("mps"):
        return f"MPS {device.split('.')[1].upper()} chi{p.get('mps_bond_dimension')}"
    lvl, thr = p.get("pauli_path_circuit_transpilation_level", 2), p.get("pauli_path_truncation_threshold")
    return f"PPS L{lvl} delta {thr if thr is None else format(thr, 'g')}"


def load():
    rows = defaultdict(dict)  # (problem, label) -> {qubit: value}
    meta = {}
    for r in csv.DictReader(open(REPO / "runs/estimates.csv", encoding="utf-8")):
        if r["origin"] != "bluequbit" or r["status"] != "COMPLETED" or not r["estimate"]:
            continue
        key = (r["problem"], label(r["backend"], r["parameters_json"]))
        rows[key][int(r["qubit"])] = float(r["estimate"])
        meta[key] = (r["backend"], json.loads(r["parameters_json"] or "{}"))
    return rows, meta


def style(ax):
    ax.set_facecolor("white")
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(GRID)
    ax.tick_params(colors=MUTED, labelsize=9)
    ax.grid(True, axis="y", color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)


def g4_vectors(rows):
    series = [(k, v) for k, v in rows.items() if k[0] == "G4"]
    series.sort(key=lambda kv: (-len(kv[1]), kv[0][1]))
    fig, ax = plt.subplots(figsize=(11, 4.6), dpi=150)
    style(ax)
    for i, (k, v) in enumerate(series[:6]):
        q = sorted(v)
        full = len(v) == 38
        ax.plot(q, [v[x] for x in q], marker="o", ms=4 if full else 7, lw=2 if full else 0,
                color=CAT[i], label=f"{k[1]} ({len(v)}/38 rows)", alpha=0.95)
    ax.axhline(0, color=GRID, lw=1)
    ax.set_xlabel("target qubit (Duke_G4_q)", color=MUTED)
    ax.set_ylabel("<Z_q> estimate", color=INK)
    ax.set_title("G4: direct native estimates by cohort", color=INK, loc="left", fontsize=12)
    ax.legend(frameon=False, fontsize=8, ncol=2)
    fig.tight_layout()
    fig.savefig(OUT / "g4_vectors.png")
    plt.close(fig)


def agreement(rows):
    keys = [k for k in rows if k[0] == "G4" and len(rows[k]) >= 8]
    keys.sort(key=lambda k: k[1])
    n = len(keys)
    mat = np.full((n, n), np.nan)
    for i, a in enumerate(keys):
        for j, b in enumerate(keys):
            common = sorted(set(rows[a]) & set(rows[b]))
            if len(common) >= 4:
                x, y = np.array([rows[a][q] for q in common]), np.array([rows[b][q] for q in common])
                if x.std() > 1e-9 and y.std() > 1e-9:
                    mat[i, j] = np.corrcoef(x, y)[0, 1]
    fig, ax = plt.subplots(figsize=(1.2 * n + 3, 1.0 * n + 2), dpi=150)
    im = ax.imshow(mat, cmap="RdBu", vmin=-1, vmax=1)
    for i in range(n):
        for j in range(n):
            if np.isfinite(mat[i, j]):
                common = len(set(rows[keys[i]]) & set(rows[keys[j]]))
                ax.text(j, i, f"{mat[i, j]:.2f}\n(n={common})", ha="center", va="center", fontsize=7, color=INK)
    ax.set_xticks(range(n)); ax.set_yticks(range(n))
    ax.set_xticklabels([k[1] for k in keys], rotation=35, ha="right", fontsize=8)
    ax.set_yticklabels([k[1] for k in keys], fontsize=8)
    ax.set_title("G4 cross-cohort Pearson rho on common rows (diverging, 0 = gray)", loc="left", fontsize=10, color=INK)
    fig.colorbar(im, ax=ax, shrink=0.7)
    fig.tight_layout()
    fig.savefig(OUT / "g4_method_agreement.png")
    plt.close(fig)


def sensitivity(rows, meta, which):
    fig, ax = plt.subplots(figsize=(7, 4.2), dpi=150)
    style(ax)
    checks = defaultdict(dict)  # circuit -> {param: value}
    for k, v in rows.items():
        dev, p = meta[k]
        if which == "delta" and dev.startswith("pauli") and p.get("pauli_path_circuit_transpilation_level") == 3:
            for q, val in v.items():
                checks[f"{k[0]}_{q}"][p["pauli_path_truncation_threshold"]] = val
        if which == "chi" and dev == "mps.cpu":
            for q, val in v.items():
                checks[f"{k[0]}_{q}"][p["mps_bond_dimension"]] = val
    multi = [(c, d) for c, d in checks.items() if len(d) >= 2]
    multi.sort(key=lambda cd: cd[0])
    for i, (c, d) in enumerate(multi[:6]):
        xs = sorted(d)
        ax.plot(xs, [d[x] for x in xs], marker="o", ms=6, lw=2, color=CAT[i], label=f"Duke_{c}")
        ref = EXACT.get(f"Duke_{c}")
        if ref is not None:
            ax.axhline(ref, color=CAT[i], lw=1, ls="--", alpha=0.6)
            ax.text(xs[-1], ref, " exact", color=CAT[i], fontsize=7, va="bottom")
    ax.set_xscale("log")
    ax.set_xlabel("PPS truncation threshold delta (native level 3)" if which == "delta" else "MPS bond dimension chi (CPU)", color=MUTED)
    ax.set_ylabel("<Z_q> estimate", color=INK)
    ax.set_title("Precision sensitivity on check rows (dashed = exact reference where known)", loc="left", fontsize=10, color=INK)
    ax.legend(frameon=False, fontsize=8)
    fig.tight_layout()
    fig.savefig(OUT / f"{which}_sensitivity.png")
    plt.close(fig)


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    rows, meta = load()
    g4_vectors(rows)
    agreement(rows)
    sensitivity(rows, meta, "delta")
    sensitivity(rows, meta, "chi")
    print("wrote", sorted(p.name for p in OUT.glob("*.png")))
