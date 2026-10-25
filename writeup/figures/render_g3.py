"""Reproduce the G3 comparison from saved submissions; no simulator or API calls."""
import csv
import hashlib
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


def main():
    directory = Path(__file__).resolve().parent
    repo = directory.parents[1]
    source = json.loads((directory / "g3_precision_source.json").read_text(encoding="utf-8"))
    vectors = []
    for series in source["series"]:
        path = repo / series["csv_path"]
        if hashlib.sha256(path.read_bytes()).hexdigest() != series["csv_sha256"]:
            raise ValueError(f"CSV checksum changed: {path.name}")
        receipt = repo / series["receipt_path"]
        if hashlib.sha256(receipt.read_bytes()).hexdigest() != series["receipt_sha256"]:
            raise ValueError(f"Receipt checksum changed: {receipt.name}")
        with path.open(encoding="utf-8-sig", newline="") as stream:
            rows = {row["circuit_id"]:float(row["value"]) for row in csv.DictReader(stream)}
        values = np.array([rows[key] for key in series["circuit_ids"]])
        if not np.array_equal(values, np.array(series["values"])):
            raise ValueError("Saved figure values differ from submission")
        vectors.append(values)
    normalized = [(v-v.mean())/np.linalg.norm(v-v.mean()) for v in vectors]
    rho = float(normalized[0] @ normalized[1])
    if not np.isclose(rho, source["comparison"]["pearson_correlation"], atol=1e-12):
        raise ValueError("Saved correlation differs from recomputed value")
    plt.rcParams.update({"font.size":9, "axes.spines.top":False, "axes.spines.right":False})
    fig, axes = plt.subplots(2, 1, figsize=(7.15, 5.65), layout="constrained")
    colors = ["#D57828", "#166A91"]
    for v, series, color in zip(vectors, source["series"], colors):
        label = f"epsilon {series['epsilon']:g}; teammate-reported {series['reported_displayed_score']}/800"
        axes[0].plot(np.arange(len(v)), v, marker="o", markersize=3, lw=1.1, color=color, label=label)
        zero = np.flatnonzero(v == 0)
        axes[0].scatter(zero, v[zero], facecolors="white", edgecolors=color, s=22, zorder=4)
    axes[0].axhline(0, color="#aaaaaa", lw=.7)
    axes[0].set(xlabel="Target qubit q", ylabel="Submitted expectation", title="(a) G3 at native PPS level 1: direct submitted values")
    axes[0].legend(fontsize=8)
    lo, hi = min(np.min(v) for v in normalized), max(np.max(v) for v in normalized)
    reference = np.array([lo-.03, hi+.03])
    axes[1].plot(reference, reference, "--", color="#888888", lw=1, label="Identical normalized shape")
    axes[1].plot(reference, rho*reference, color=colors[1], lw=1, label="Least-squares relation")
    axes[1].scatter(*normalized, s=22, color=colors[1], alpha=.8)
    axes[1].set(xlabel="Centered, unit-norm profile: epsilon 0.001", ylabel="Profile: epsilon 0.0003",
                title=f"(b) Shape comparison: r = {rho:.5f}; exact zeros 9 to 3")
    axes[1].legend(fontsize=8, loc="upper left")
    for axis in axes:
        axis.grid(alpha=.15)
    fig.savefig(directory / "g3_precision.png", dpi=300)
    plt.close(fig)
    print(f"Rebuilt G3 figure from verified CSVs: r={rho:.12f}; no hidden reference used.")


if __name__ == "__main__":
    main()
