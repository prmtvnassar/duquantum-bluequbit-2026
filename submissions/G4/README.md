# G4: PPS baseline, MPS refinement, ensemble (284/1000)

Final vector: [G4_final_ensemble_2.csv](../candidates/G4/G4_final_ensemble_2.csv), **284/1000**, with its
[method note](../candidates/G4/G4_final_ensemble_2.txt). All scored G4 vectors are listed in
[candidates/G4/README.md](../candidates/G4/README.md); the reasoning is in
[research_notes/G4_PPS_MPS.md](../../research_notes/G4_PPS_MPS.md).

| Step | Vector | Website score |
| --- | --- | ---: |
| 1 | MPS χ32, all rows | 0 |
| 2 | **Baseline**: PPS ε 1e-4, level 3, all rows (a teammate) | 133 |
| 3–5 | **MPS refinement**: χ256 on q0 / q0–q1 / q0–q3, q6–q9 (a teammate) | 139 / 145 / 165 |
| 6 | MPS χ64, all rows | 0 |
| 7 | Geometry prior from exact proxies | 2 |
| 8–9 | PPS / 165 vector minus the null directions χ32, χ64, geo | 199 / 195 |
| 10 | **Final ensemble** of refined vectors (a teammate) | **284** |

The ensemble's dominant ingredient was fitted to the website scores of earlier whole-vector uploads; the
method note says so.

## The MPS χ32 zero

The complete CPU MPS χ32 candidate received a user-reported accepted 0/1000 ([CSV](../candidates/G4/direct-930f7e5b7d14.csv),
[explanation](../candidates/G4/direct-930f7e5b7d14.txt), [row manifest](../candidates/G4/direct-930f7e5b7d14.json),
[feedback](../candidates/G4/direct-930f7e5b7d14.feedback.json)). Selected χ64 checks then showed rows still
moving substantially from χ32, and q1 reversing direction; a PPS check at q4 returned zero at two thresholds
while compute time grew sharply ([G4 trend review](../../reports/G4_PARTIAL_TREND_REVIEW.md)). This is what moved
G4 from MPS to a PPS baseline.

## The PPS baseline: 133/1000

A teammate reports **133/1000** for a complete Pauli-path vector: threshold 0.0001, native transpilation
level 3, the same options for all 38 IDs, 0 credits ([CSV](../teammates/teammate-1/G4/submitted-v1.csv),
[explanation](../teammates/teammate-1/G4/submitted-v1.txt), [receipt](../teammates/teammate-1/G4/submitted-v1.json)
with every row's job ID). The values were not converged: q37 moved from 0.020 at threshold 0.0003 to 0.099
at 0.0001. Level 3 differs from the level 1 used for [G3](../G3/README.md), because on G4 native levels 1 and 2
returned zeros.
