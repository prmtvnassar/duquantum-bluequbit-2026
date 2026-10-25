"""Compare two complete G4 native cohorts with the repo's shape diagnostic and export a candidate.

Usage:
  python scripts/compare_g4_cohorts.py --older mps.cpu '{"mps_bond_dimension": 32}' \
      --newer mps.cpu '{"mps_bond_dimension": 64}' [--export]

Shape diagnostic (workflow_final.md): centre both vectors, a = (x.y)/(x.x), r = y - a x,
row influence r_i^2/(y.y); sum = 1 - rho^2. Export writes problems/G4/selected.csv from
the newer cohort and runs the repo exporter in check mode; it never uploads.
"""
import argparse
import csv
import json
import subprocess
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[1]
N = 38


def cohort(device, options):
    want = json.dumps(options, sort_keys=True)
    out = {}
    for r in csv.DictReader(open(REPO / "runs/estimates.csv", encoding="utf-8")):
        if r["problem"] != "G4" or r["status"] != "COMPLETED" or r["origin"] != "bluequbit":
            continue
        if r["backend"] == device and json.dumps(json.loads(r["parameters_json"]), sort_keys=True) == want:
            out[int(r["qubit"])] = (float(r["estimate"]), r["job_id"])
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--older", nargs=2, required=True)
    ap.add_argument("--newer", nargs=2, required=True)
    ap.add_argument("--export", action="store_true")
    a = ap.parse_args()
    old = cohort(a.older[0], json.loads(a.older[1]))
    new = cohort(a.newer[0], json.loads(a.newer[1]))
    common = sorted(set(old) & set(new))
    print(f"older rows {len(old)}/{N}, newer rows {len(new)}/{N}, common {len(common)}")
    x = np.array([old[q][0] for q in common]); y = np.array([new[q][0] for q in common])
    xc, yc = x - x.mean(), y - y.mean()
    rho = float(np.dot(xc, yc) / (np.linalg.norm(xc) * np.linalg.norm(yc)))
    slope = float(np.dot(xc, yc) / np.dot(xc, xc))
    resid = yc - slope * xc
    infl = resid ** 2 / np.dot(yc, yc)
    print(f"rho = {rho:.4f}   1-rho = {1-rho:.4f}   1-rho^2 = {1-rho*rho:.4f}   affine slope = {slope:.3f}{'  NEGATIVE SLOPE' if slope < 0 else ''}")
    print(f"max |delta| = {np.max(np.abs(y-x)):.4f}   mean |delta| = {np.mean(np.abs(y-x)):.4f}")
    order = np.argsort(-infl)
    print("top shape-influence rows (q: older -> newer, influence):")
    for i in order[:8]:
        print(f"  q{common[i]:>2}: {x[i]:+.4f} -> {y[i]:+.4f}   {infl[i]:.4f}")
    if a.export:
        if len(new) != N:
            sys.exit("newer cohort incomplete; not exporting")
        sel = REPO / "problems/07_graded_G4/selected.csv"
        with open(sel, "w", newline="") as f:
            w = csv.writer(f); w.writerow(["circuit_id", "value"])
            for q in range(N):
                w.writerow([f"Duke_G4_{q}", repr(new[q][0])])
        manifest = {f"Duke_G4_{q}": {"value": new[q][0], "job_id": new[q][1], "device": a.newer[0], "options": json.loads(a.newer[1])} for q in range(N)}
        (REPO / "problems/07_graded_G4/selected_manifest.json").write_text(json.dumps(manifest, indent=2))
        print("wrote", sel, "and selected_manifest.json")
        subprocess.run([sys.executable, str(REPO / "scripts/export_problem_submission.py"), "--problem", "G4", "--check-only"], check=False)


if __name__ == "__main__":
    main()
