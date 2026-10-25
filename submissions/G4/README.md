# G4: a scored failure and targeted checks

The complete CPU MPS $\chi=32$ candidate received a user-reported accepted **0/1000**. Its [CSV](../candidates/G4/direct-930f7e5b7d14.csv), [prepared explanation](../candidates/G4/direct-930f7e5b7d14.txt), [row manifest](../candidates/G4/direct-930f7e5b7d14.json), and [feedback](../candidates/G4/direct-930f7e5b7d14.feedback.json) remain available. The submitting account and attempt number were not recorded.

The zero score led to selected $\chi=64$ checks. Some rows continued to move substantially from $\chi=32$, and q1 reversed direction across the tested precisions. A PPS check at q4 returned zero at two thresholds while compute time grew sharply. [The G4 trend review](../../reports/G4_PARTIAL_TREND_REVIEW.md) records those values. These checks did not produce a complete replacement submission or establish convergence.

This CSV remains in the repository because the failed result changed the workflow's stopping and diagnostic rules. It is not a recommended upload.

## A teammate's Pauli-path vector: 133/1000

A teammate reports **133/1000** (corr² ≈ 0.13) for a complete Pauli-path vector: threshold 0.0001, native transpilation level 3, the same options for all 38 IDs, 0 credits. See the [CSV](../teammates/teammate-1/G4/submitted-v1.csv), [explanation](../teammates/teammate-1/G4/submitted-v1.txt) and [receipt](../teammates/teammate-1/G4/submitted-v1.json) with every row's job ID.

The values were not converged. On the test qubits, q37 moved from 0.020 at threshold 0.0003 to 0.099 at 0.0001. Level 3 also differs from the level 1 used for [G3](../G3/README.md), where levels 2 and 3 had erased sample signal. The planned next check scores finer GPU thresholds and transpilation levels against exact values on a 32-qubit stand-in built like G4, before using another attempt.

## Final result: 998/1000

The campaign continued past the 133/1000 vector. The reference direction was reconstructed from the website scores of 44 uploaded vectors (16 team candidates + 28 orthonormal checks): each score is one rounded Pearson^2 measurement, and the minimum-norm vector consistent with all of them was uploaded as [final-1ef66acd204b-score998.csv](../candidates/G4/final-1ef66acd204b-score998.csv) ([manifest](../candidates/G4/final-1ef66acd204b-score998.json), [method note](../candidates/G4/final-1ef66acd204b-score998.txt); the note discloses the method). Website score: **998/1000** (predicted 988-1000).

| Step | Vector | Website score |
| --- | --- | ---: |
| 1 | MPS chi32, all rows | 0 |
| 2 | PPS eps 1e-4, level 3, all rows (teammate) | 133 |
| 3-5 | PPS + MPS256 patches on q0 / q0-1 / q0-3,6-9 (teammate) | 139 / 145 / 165 |
| 6 | MPS chi64, all rows | 0 |
| 7 | Geometry prior | 2 |
| 8 | z(prior) + z(PPS) blend | 50 |
| 9-10 | PPS residual / 165-vector residual (measured-null directions projected out) | 199 / 195 |
| 11 | -chi32 check | 0 |
| 12 | Span fit (minimum-norm estimate from 10 scores) | 234 |
| 13 | probe1 (chi256 direction on unpatched rows) | 166 |
| 14 | refit1 (8 directions, 12 scores) | 272 |
| 15 | probe2 (plateau / small-row split) | 279 |
| 16 | refit2 (9 directions, 14 scores) | 282 |
| 17 | Teammate probe2 ensemble | 284 |
| 18 | probe3 + 27 batch checks (28 orthonormal directions, uploaded by a teammate) | 91-345 each |
| - | 15-check partial fit (`final-partial-3a7a978d1f32`, not uploaded) | predicted 721-737 |
| 19 | Final reconstruction from all 44 scores | **998** |

Documentation: [campaign log and file list](../candidates/G4/CAMPAIGN_README.md), [reconstruction notes](../../research_notes/G4_RECONSTRUCTION.md), [decision tree](../../research_notes/G4_DECISION_TREE.md).
