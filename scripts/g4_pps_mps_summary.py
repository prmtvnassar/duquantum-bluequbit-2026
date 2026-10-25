"""G4 summary: the PPS -> MPS refinement ladder, the known-answer check of the post-processing rule,
and the light-cone facts of all seven circuits (offline, $0, no API calls).

- Ladder: every uploaded G4 vector with its website score, in order.
- Known-answer check: PG4c (labs/pg4c/pg4c.csv) is a 32-qubit circuit built like G4 (5x6 + 2 grid, 16 Haar
  layers) with the exact BlueQubit statevector answer and native PPS / MPS runs. It is the only place the
  G4 post-processing rule (subtract PPS's projection on the MPS vector) can be scored against an exact answer.
- Light cone: rows never reached / reached late / reached early by the butterfly, per circuit.

    python scripts/g4_pps_mps_summary.py     # prints tables, writes reports/g4_pps_mps_summary.json
"""
import csv, json
from pathlib import Path
import numpy as np

REPO = Path(__file__).resolve().parents[1]; C4 = REPO / "submissions/candidates/G4"

def load(p):
    rows = list(csv.DictReader(open(p, encoding="utf-8-sig")))
    return np.array([float(r["value"]) for r in sorted(rows, key=lambda r: int(r["circuit_id"].split("_")[-1]))])
def rho(a, b): return float(np.corrcoef(a, b)[0, 1])
def score(a, ref): return round(1000 * max(0.0, rho(a, ref)) ** 2)
def resid(y, X):
    X = np.column_stack([np.ones(len(y))] + X); b, *_ = np.linalg.lstsq(X, y, rcond=None); return y - X @ b

# light-cone geometry: brickwork sub-layers H0 (even-column pairs), V0 (even-row pairs), H1, V1, as read from sample S3
def layer_sets(pos):
    inv = {v: k for k, v in pos.items()}; L = {"H0": [], "H1": [], "V0": [], "V1": []}
    for q, (r, c) in pos.items():
        if (r, c + 1) in inv: L["H0" if c % 2 == 0 else "H1"].append((q, inv[(r, c + 1)]))
        if (r + 1, c) in inv: L["V0" if r % 2 == 0 else "V1"].append((q, inv[(r + 1, c)]))
    return L
def slack(pos, order, depth, b):
    """depth minus the layer (counted through U in reverse) at which q enters the support of U^dag X_b U; -1 = never."""
    L = layer_sets(pos); S = {b}; tc = {b: 0}
    for k in range(depth):
        for a, c in L[order[(depth - 1 - k) % len(order)]]:
            if a in S or c in S:
                for q in (a, c):
                    if q not in S: tc[q] = k + 1
                S |= {a, c}
    return np.array([depth - tc[q] if q in tc else -1 for q in sorted(pos)])
def grid(R, Cc, extra=None):
    p = {r * Cc + c: (r, c) for r in range(R) for c in range(Cc)}
    if extra: p.update(extra)
    return p
G4POS = grid(6, 6, {36: (6, 0), 37: (6, 1)})

LADDER = [("MPS chi32, all rows", C4 / "direct-930f7e5b7d14.csv", 0, "null"),
          ("PPS eps 1e-4, level 3 (baseline)", REPO / "submissions/teammates/teammate-1/G4/submitted-v1.csv", 133, "pps"),
          ("+ MPS chi256 on q0", C4 / "pps-mps256-q0-score139.csv", 139, "refine"),
          ("+ MPS chi256 on q0-q1", C4 / "pps-mps256-q0q1-score145.csv", 145, "refine"),
          ("+ MPS chi256 on q0-q3, q6-q9", C4 / "pps-mps256-8rows-score165.csv", 165, "refine"),
          ("MPS chi64, all rows", C4 / "direct-8f66fe538349-score0.csv", 0, "null"),
          ("geometry prior from proxies", C4 / "geo-c9cd356165e4-score2.csv", 2, "null"),
          ("PPS minus null directions", C4 / "resid-pps-a35b4b7d167f-score199.csv", 199, "refine"),
          ("165 vector minus null directions", C4 / "resid-v165-96e3fec30972-score195.csv", 195, "refine"),
          ("final ensemble", C4 / "G4_final_ensemble_2.csv", 284, "final")]

def main():
    out = {"ladder": [], "pg4c_known_answer": {}, "circuits": {}}
    for name, p, s, kind in LADDER:
        out["ladder"].append({"step": name, "website": s, "kind": kind, "file": str(p.relative_to(REPO)).replace("\\", "/")})

    pg = list(csv.DictReader(open(REPO / "labs/pg4c/pg4c.csv"))); f = lambda k: np.array([float(x[k]) if x[k] else np.nan for x in pg])
    ex, pps4, pps3, m128 = f("exact"), f("pps1e4L3"), f("pps1e3L3"), f("mps128")
    out["pg4c_known_answer"] = {"PPS eps 1e-4, level 3": score(pps4, ex), "PPS eps 1e-3, level 3": score(pps3, ex),
                                "MPS chi128": score(m128, ex), "PPS 1e-4 minus its projection on MPS chi128": score(resid(pps4, [m128]), ex)}

    probs = {"S1": (REPO / "submissions/S1/attempt-01.csv", grid(1, 4), ("H0", "H1"), 4, 0),
             "S2": (REPO / "submissions/S2/attempt-01.csv", grid(1, 16), ("H0", "H1"), 12, 0),
             "S3": (REPO / "submissions/S3/attempt-01.csv", grid(5, 6), ("H0", "V0", "H1", "V1"), 16, 14),
             "G1": (REPO / "submissions/teammates/teammate-1/G1/submitted-v1.csv", grid(1, 30), ("H0", "H1"), 32, 0),
             "G2": (REPO / "submissions/candidates/G2/G2_1_mps2048_22_mps512_13_mps128.csv", grid(1, 36), ("H0", "H1"), 18, 18),
             "G3": (REPO / "submissions/teammates/teammate-1/G3/submitted-v3.csv", grid(6, 6), ("H0", "V0", "H1", "V1"), 24, 14),
             "G4": (C4 / "G4_final_ensemble_2.csv", G4POS, ("H0", "V0", "H1", "V1"), 16, 0)}
    for k, (p, pos, order, depth, b) in probs.items():
        v = load(p); s = slack(pos, order, depth, b)
        out["circuits"][k] = {"qubits": len(v), "layers": depth, "butterfly": b, "never_reached": int((s < 0).sum()),
                              "late_contact": int(((s >= 0) & (s <= 7)).sum()), "early_contact": int((s >= 8).sum()), "values": [float(x) for x in v]}

    (REPO / "reports").mkdir(exist_ok=True)
    json.dump(out, open(REPO / "reports/g4_pps_mps_summary.json", "w"), indent=1)
    print("G4 ladder (website score /1000):")
    for c in out["ladder"]: print(f"  {c['step']:36s} {c['website']:>5}")
    print("\nPG4c known answer (32 qubits, built like G4), 1000 x Pearson^2 vs exact:")
    for k, v in out["pg4c_known_answer"].items(): print(f"  {k:48s} {v:>5}")
    print("\nLight cone (rows never reached / late / early):", {k: (v["never_reached"], v["late_contact"], v["early_contact"]) for k, v in out["circuits"].items()})

if __name__ == "__main__":
    main()
