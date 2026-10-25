"""Figures for the proxy lab report (static PNG, matplotlib).
Usage: python plot.py   -> research_notes/proxy_lab/fig_exact_profile.png, fig_method_scores.png"""
import json
import os
from collections import defaultdict

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from common import DATA, load_instances

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                   "research_notes", "proxy_lab")
os.makedirs(OUT, exist_ok=True)
SURFACE, INK, INK2 = "#fcfcfb", "#0b0b0b", "#52514e"
CAT = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#6250d6"]  # fixed categorical order
SEQ = {4: "#9ec5f4", 8: "#5598e7", 12: "#2a78d6", 16: "#104281"}           # one-hue ramp for depth


def style(ax):
    ax.set_facecolor(SURFACE)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(INK2)
    ax.tick_params(colors=INK2, labelsize=8)
    ax.grid(True, axis="y", color="#e6e5e1", linewidth=0.6)
    ax.set_axisbelow(True)


def main():
    inst = load_instances()
    groups = defaultdict(list)
    for name, d in inst.items():
        groups[(d["rows"], d["cols"], d["depth"])].append(name)
    # --- figure 1: mean |exact| by distance, one panel per grid, one line per depth
    grids = sorted({(k[0], k[1]) for k in groups})
    fig, axes = plt.subplots(1, len(grids), figsize=(4.2 * len(grids), 3.4), sharey=True, facecolor=SURFACE)
    axes = np.atleast_1d(axes)
    for ax, (R, C) in zip(axes, grids):
        style(ax)
        n = R * C
        for depth in sorted({k[2] for k in groups if k[:2] == (R, C)}):
            names = groups[(R, C, depth)]
            dvec = np.array(inst[names[0]]["manhattan"])
            prof = np.array([[np.abs(np.array(inst[nm]["exact"]))[dvec == dd].mean() for dd in sorted(set(dvec))] for nm in names])
            ds = sorted(set(dvec))
            ax.plot(ds, prof.mean(0), color=SEQ[depth], linewidth=2, marker="o", markersize=4, label=f"depth {depth} ({len(names)} inst.)")
            ax.fill_between(ds, prof.min(0), prof.max(0), color=SEQ[depth], alpha=0.12, linewidth=0)
        ax.axhline(2 ** (-n / 2), color=INK2, linestyle=":", linewidth=1)
        ax.text(0.02, 2 ** (-n / 2) * 0.55, "noise floor 2^(-n/2)", color=INK2, fontsize=7, transform=ax.get_yaxis_transform())
        ax.set_yscale("log"); ax.set_ylim(1e-4, 1.5)
        ax.set_title(f"{R}x{C} grid (n={n}), butterfly q0", color=INK, fontsize=10)
        ax.set_xlabel("Manhattan distance from q0", color=INK2, fontsize=9)
        ax.legend(fontsize=7, frameon=True, framealpha=0.85, facecolor=SURFACE, edgecolor="#e6e5e1", loc="lower right")
    axes[0].set_ylabel("mean |exact OTOC(2)| (band = min..max over instances)", color=INK2, fontsize=8)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "fig_exact_profile.png"), dpi=150, facecolor=SURFACE)
    # --- figure 2: method scores at depth 16 per grid
    summ = json.load(open(os.path.join(DATA, "summary.json")))
    keys = [k for k in summ if k.endswith("_d16")]
    fig, ax = plt.subplots(figsize=(9, 3.8), facecolor=SURFACE)
    style(ax)
    meths = ["MPS chi8", "MPS chi16", "MPS chi32", "MPS chi64", "MPS chi128", "PPS L3 eps 0.001 (None->0)",
             "prior: Manhattan distance", "prior: exp(d)", "prior: sigmoid front, LOO within group", "prior: signed slack-mean table, LOO", "random Gaussian vector (null)"]
    labels = ["chi8", "chi16", "chi32", "chi64", "chi128", "PPS 1e-3", "dist d", "exp(d)", "front LOO", "slack table LOO", "null"]
    width = 0.8 / max(1, len(keys))
    for i, k in enumerate(keys):
        sc = summ[k]["scores"]
        means = [sc[m]["mean"] if m in sc else np.nan for m in meths]
        lo = [sc[m]["min"] if m in sc else np.nan for m in meths]
        hi = [sc[m]["max"] if m in sc else np.nan for m in meths]
        x = np.arange(len(meths)) + (i - (len(keys) - 1) / 2) * width
        ax.bar(x, means, width * 0.9, color=CAT[i], label=k.replace("_d16", ", depth 16"), linewidth=0)
        ax.vlines(x, lo, hi, color=INK2, linewidth=0.8)
    ax.set_xticks(np.arange(len(meths))); ax.set_xticklabels(labels, fontsize=8)
    ax.set_ylabel("score (bar = mean, line = min..max)", color=INK2, fontsize=8)
    ax.legend(fontsize=8, frameon=False)
    ax.set_title("What local methods and priors score on exact depth-16 corner-butterfly proxies", color=INK, fontsize=10)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "fig_method_scores.png"), dpi=150, facecolor=SURFACE)
    print("wrote figures to", OUT)


if __name__ == "__main__":
    main()
