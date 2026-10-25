"""Rebuild slide figures from saved evidence, without service or simulator calls."""

import argparse
import csv
import hashlib
import json
from pathlib import Path

import numpy as np


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
G3_FILES = (
    ("submissions/teammates/teammate-1/G3/submitted-v2.csv",
     "33c9a6ac4d0e1b06ce9a79607c20a7ea4dd707e571061aeea7f031715075f7ef",
     534, 0.001),
    ("submissions/teammates/teammate-1/G3/submitted-v3.csv",
     "44fdbe227f1fede6b7abe04934dd375420c86a9427c69b760bb70c00e338d691",
     773, 0.0003),
)
G2_FILES = (
    ("submissions/candidates/G2/G2_23_512_and_13_128.csv",
     "bd0c968b03684723187653becaa2615f5b453f36c7baf9ca01d210fa24ab0459"),
    ("submissions/candidates/G2/G2_1_mps2048_22_mps512_13_mps128.csv",
     "5706f503ee2ef9dd629531a0c1089a44a21099970f56cbe9785f5dfa583d66e4"),
)


def g2_change():
    vectors = []
    for name, expected_hash in G2_FILES:
        path = REPO / name
        if hashlib.sha256(path.read_bytes()).hexdigest() != expected_hash:
            raise ValueError(f"G2 candidate bytes changed: {name}")
        with path.open(encoding="utf-8-sig", newline="") as stream:
            rows = {row["circuit_id"]: float(row["value"])
                    for row in csv.DictReader(stream)}
        if set(rows) != {f"Duke_G2_{q}" for q in range(36)}:
            raise ValueError(f"G2 ID coverage changed: {name}")
        vectors.append(rows)
    changed = [key for key in vectors[0] if vectors[0][key] != vectors[1][key]]
    feedback = json.loads((REPO / G2_FILES[1][0].replace(".csv", ".feedback.json")).read_text())
    if changed != ["Duke_G2_30"] or feedback["score"] != 581:
        raise ValueError("G2 q30 comparison or score report changed")
    return vectors[0][changed[0]], vectors[1][changed[0]]


def g3_values():
    vectors = []
    for name, expected_hash, score, threshold in G3_FILES:
        path = REPO / name
        if hashlib.sha256(path.read_bytes()).hexdigest() != expected_hash:
            raise ValueError(f"Submission bytes changed: {name}")
        receipt = json.loads(path.with_suffix(".json").read_text(encoding="utf-8"))
        if (receipt["sha256"] != expected_hash
                or receipt["reported_displayed_score"] != score
                or len(receipt["row_provenance"]) != 36
                or any(row["options"] != {
                    "pauli_path_truncation_threshold": threshold,
                    "pauli_path_circuit_transpilation_level": 1,
                } for row in receipt["row_provenance"])):
            raise ValueError(f"G3 receipt does not support the plot label: {name}")
        with path.open(encoding="utf-8-sig", newline="") as stream:
            rows = {row["circuit_id"]: float(row["value"])
                    for row in csv.DictReader(stream)}
        expected_ids = {f"Duke_G3_{q}" for q in range(36)}
        if set(rows) != expected_ids:
            raise ValueError(f"G3 ID coverage changed: {name}")
        vectors.append(np.array([rows[f"Duke_G3_{q}"] for q in range(36)]))
    return vectors


def g4_values():
    feedback = json.loads((REPO / "submissions/candidates/G4/"
                           "direct-930f7e5b7d14.feedback.json").read_text())
    if feedback["reported_displayed_score"] != 0 or not feedback["accepted_grading"]:
        raise ValueError("Saved G4 score report changed")
    pps_path = REPO / "submissions/teammates/teammate-1/G4/submitted-v1.csv"
    pps_receipt = json.loads(pps_path.with_suffix(".json").read_text())
    if (hashlib.sha256(pps_path.read_bytes()).hexdigest() != pps_receipt["sha256"]
            or pps_receipt["reported_displayed_score"] != 133
            or len(pps_receipt["row_provenance"]) != 38):
        raise ValueError("Saved G4 PPS score or vector changed")
    with pps_path.open(encoding="utf-8-sig", newline="") as stream:
        pps = {row["circuit_id"]: float(row["value"])
               for row in csv.DictReader(stream)}
    if (set(pps) != {f"Duke_G4_{q}" for q in range(38)}
            or sum(value == 0 for value in pps.values()) != 4):
        raise ValueError("Saved G4 PPS zero count changed")
    review = json.loads((REPO / "reports/g4_partial_trend_review.json").read_text())
    early = {row["qubit"]: row for row in review["matched_rows"]}
    late = {}
    with (REPO / "runs/jobs.csv").open(encoding="utf-8-sig", newline="") as stream:
        for row in csv.DictReader(stream):
            if (row["status"] == "COMPLETED" and row["backend"] == "mps.cpu"
                    and row["problem"] == "G4"
                    and json.loads(row["parameters_json"]).get("mps_bond_dimension") == 64):
                q = int(row["qubit"])
                if q in late and late[q] != float(row["estimate"]):
                    raise ValueError(f"Conflicting chi64 values for G4 q{q}")
                late[q] = float(row["estimate"])
    selected = (0, 4, 1, 19)
    if not all(q in early and q in late for q in selected):
        raise ValueError("A G4 trend point is missing")
    return {q: (early[q]["chi16"], early[q]["chi32"], late[q])
            for q in selected}


def extrapolation_windows():
    report = json.loads((REPO / "reports/extrapolation_rejection.json").read_text())
    if report["status"] != "THIS_CANDIDATE_REJECTED":
        raise ValueError("Extrapolation evaluation status changed")
    result = []
    for window in report["windows"]:
        pair = window["held_out_finer_level"]
        result.append((window["fit_chis"], window["held_out_chi"],
                       pair["direct"]["mae"], pair["forecast"]["mae"]))
    if len(result) != 2 or not all(forecast > direct for _, _, direct, forecast in result):
        raise ValueError("Held-out extrapolation result changed")
    return result


def verify():
    old_q30, new_q30 = g2_change()
    first, second = g3_values()
    rho = float(np.corrcoef(first, second)[0, 1])
    zeros = (int(np.count_nonzero(first == 0)), int(np.count_nonzero(second == 0)))
    if zeros != (9, 3) or not np.isclose(rho, 0.89169, atol=1e-5):
        raise ValueError("G3 profile comparison changed")
    trends = g4_values()
    windows = extrapolation_windows()
    print(f"G2: only q30 changed, {old_q30:.5f} -> {new_q30:.5f}; 581/600 is a commit-message report.")
    print(f"G3: zero rows {zeros[0]} -> {zeros[1]}; profile correlation {rho:.5f}.")
    for fit, held_out, direct, forecast in windows:
        print(f"S2 extrapolation fit {fit}, held out chi{held_out}: "
              f"direct MAE {direct:.5f}; forecast MAE {forecast:.5f}.")
    print("G4 chi16/32/64: " + "; ".join(
        f"q{q} " + "/".join(f"{value:.3f}" for value in values)
        for q, values in trends.items()))
    print("G4: saved MPS feedback reports 0/1000; a teammate's complete PPS receipt reports 133/1000 with four zero rows.")
    return first, second, trends


def render(first, second, trends):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 13,
                         "axes.spines.top": False, "axes.spines.right": False,
                         "axes.edgecolor": "#8da2ae", "axes.labelcolor": "#123047",
                         "xtick.color": "#123047", "ytick.color": "#123047"})
    teal, orange, navy, gray = "#087f8c", "#c56536", "#123047", "#8297a4"

    fig, ax = plt.subplots(figsize=(10, 3.5), layout="constrained")
    x = np.arange(36)
    ax.plot(x, first, color=orange, linewidth=2, marker="o", markersize=3.2,
            label=r"PPS $\varepsilon=0.001$ (534/800 reported)")
    ax.plot(x, second, color=teal, linewidth=2, marker="o", markersize=3.2,
            label=r"PPS $\varepsilon=0.0003$ (773/800 reported)")
    ax.axhline(0, color=gray, linewidth=0.9)
    ax.set(xlabel="Circuit ID suffix q", ylabel=r"Direct $\langle Z_q\rangle$", xlim=(-0.5, 35.5))
    ax.set_xticks(range(0, 36, 5))
    ax.legend(loc="lower left", fontsize=11, frameon=False)
    ax.grid(axis="y", alpha=0.15)
    fig.savefig(HERE / "g3_values.png", dpi=180, facecolor="white")
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(10, 3.5), layout="constrained")
    for q, color in zip((0, 4, 1, 19), (teal, orange, navy, gray)):
        ax.plot((16, 32, 64), trends[q], color=color, linewidth=2.5,
                marker="o", markersize=7, label=f"q{q}")
    ax.axhline(0, color=gray, linewidth=0.9)
    ax.set(xlabel=r"MPS bond dimension $\chi$", ylabel=r"Direct $\langle Z_q\rangle$",
           xticks=(16, 32, 64), xlim=(13, 67))
    ax.legend(ncol=4, loc="upper right", frameon=False)
    ax.grid(axis="y", alpha=0.15)
    fig.savefig(HERE / "g4_trends.png", dpi=180, facecolor="white")
    plt.close(fig)
    print("Rebuilt two slide figures from saved evidence.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify-only", action="store_true",
                        help="check and summarize evidence without writing figures")
    args = parser.parse_args()
    values = verify()
    if not args.verify_only:
        render(*values)
