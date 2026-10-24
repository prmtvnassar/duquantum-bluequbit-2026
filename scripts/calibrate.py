"""Score every method/setting against exact values: corr² (the leaderboard metric) and cost.

Sources of estimates: local sweep CSVs (scripts/local_sweep.py) and the runner ledger
(runs/ledger.csv, BlueQubit jobs). Exact values: any circuit_id,value CSV, plus exact
rows in the ledger.

    python scripts/calibrate.py --sweeps scratch/calib/*_sweep.csv \
        --exact problems/04_graded_G1/exact_values.csv scratch/calib/S3_exact.csv
"""

from __future__ import annotations

import argparse
import csv
import math
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def corr2(pred: list[float], truth: list[float]) -> float:
    """Leaderboard score: squared Pearson correlation, 0 if negative or constant."""
    n = len(pred)
    mp, mt = sum(pred) / n, sum(truth) / n
    sp = math.sqrt(sum((p - mp) ** 2 for p in pred))
    st = math.sqrt(sum((t - mt) ** 2 for t in truth))
    if sp == 0 or st == 0:
        return 0.0
    r = sum((p - mp) * (t - mt) for p, t in zip(pred, truth)) / (sp * st)
    return max(r, 0.0) ** 2


def problem_of(circuit_id: str) -> str:
    return circuit_id.split("_")[1]


def load_exact(paths: list[Path], ledger: Path | None) -> dict[str, float]:
    exact: dict[str, float] = {}
    for p in paths:
        for r in csv.DictReader(p.open()):
            if r.get("method", "exact") != "exact" or r.get("status", "ok") != "ok":
                continue  # sweep files also hold approximate rows
            if r.get("value") not in (None, ""):
                exact[r["circuit_id"]] = float(r["value"])
    if ledger and ledger.exists():
        for r in csv.DictReader(ledger.open()):
            if r["method"] == "exact" and r["status"] == "succeeded":
                exact.setdefault(f"Duke_{r['circuit']}_{r['qubit']}", float(r["estimate"]))
    return exact


def load_estimates(sweeps: list[Path], ledger: Path | None) -> dict[tuple, dict]:
    """(source, problem, method, setting) -> {circuit_id: (value, seconds, credits)}"""
    groups: dict[tuple, dict] = defaultdict(dict)
    for p in sweeps:
        for r in csv.DictReader(p.open()):
            if r["status"] != "ok" or r["method"] == "exact":
                continue
            key = ("local", problem_of(r["circuit_id"]), r["method"], float(r["setting"]))
            groups[key][r["circuit_id"]] = (float(r["value"]), float(r["seconds"]), 0.0)
    if ledger and ledger.exists():
        latest = {}
        for r in csv.DictReader(ledger.open()):
            latest[r["job_id"]] = r
        for r in latest.values():
            if r["status"] != "succeeded" or r["method"] == "exact" or r["mode"] != "cloud":
                continue
            key = ("cloud", r["circuit"], r["method"], float(r["setting"]))
            cid = f"Duke_{r['circuit']}_{r['qubit']}"
            groups[key][cid] = (float(r["estimate"]), float(r["wall_s"] or 0), float(r["credits"] or 0))
    return groups


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sweeps", type=Path, nargs="*", default=[])
    ap.add_argument("--exact", type=Path, nargs="*", default=[])
    ap.add_argument("--ledger", type=Path, default=ROOT / "runs" / "ledger.csv")
    args = ap.parse_args()

    exact = load_exact(args.exact, args.ledger)
    groups = load_estimates(args.sweeps, args.ledger)
    print(f"{'problem':7} {'source':6} {'method':6} {'setting':>9} {'qubits':>7} {'corr²':>7} {'max|err|':>9} "
          f"{'s/qubit':>8} {'credits':>8}")
    for key in sorted(groups, key=lambda k: (k[1], k[2], k[0], -k[3] if k[2] == "pps" else k[3])):
        source, problem, method, setting = key
        rows = groups[key]
        ids = [c for c in rows if c in exact]
        total = sum(1 for c in exact if problem_of(c) == problem)
        if len(ids) < 3:
            continue
        pred, truth = [rows[c][0] for c in ids], [exact[c] for c in ids]
        err = max(abs(p - t) for p, t in zip(pred, truth))
        secs = sum(rows[c][1] for c in ids) / len(ids)
        credits = sum(rows[c][2] for c in ids)
        cover = f"{len(ids)}/{total}"
        shown = f"{int(setting)}" if method == "mps" else f"{setting:g}"
        print(f"{problem:7} {source:6} {method:6} {shown:>9} {cover:>7} {corr2(pred, truth):7.4f} {err:9.4f} "
              f"{secs:8.2f} {credits:8.3g}")


if __name__ == "__main__":
    main()
