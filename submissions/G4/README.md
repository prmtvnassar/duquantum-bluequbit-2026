# G4: a scored failure and targeted checks

The complete CPU MPS $\chi=32$ candidate received a user-reported accepted **0/1000**. Its [CSV](../candidates/G4/direct-930f7e5b7d14.csv), [prepared explanation](../candidates/G4/direct-930f7e5b7d14.txt), [row manifest](../candidates/G4/direct-930f7e5b7d14.json), and [feedback](../candidates/G4/direct-930f7e5b7d14.feedback.json) remain available. The submitting account and attempt number were not recorded.

The zero score led to selected $\chi=64$ checks. Some rows continued to move substantially from $\chi=32$, and q1 reversed direction across the tested precisions. A PPS check at q4 returned zero at two thresholds while compute time grew sharply. [The G4 trend review](../../reports/G4_PARTIAL_TREND_REVIEW.md) records those values. These checks did not produce a complete replacement submission or establish convergence.

This CSV remains in the repository because the failed result changed the workflow's stopping and diagnostic rules. It is not a recommended upload.

## Kevin's Pauli-path vector: 133/1000

Kevin reports **133/1000** (corr² ≈ 0.13) for a complete Pauli-path vector: threshold 0.0001, native transpilation level 3, the same options for all 38 IDs, 0 credits. See the [CSV](../teammates/kevin/G4/submitted-v1.csv), [explanation](../teammates/kevin/G4/submitted-v1.txt) and [receipt](../teammates/kevin/G4/submitted-v1.json) with every row's job ID.

The values were not converged. On the test qubits, q37 moved from 0.020 at threshold 0.0003 to 0.099 at 0.0001. Level 3 also differs from the level 1 used for [G3](../G3/README.md), where levels 2 and 3 had erased sample signal. The planned next check scores finer GPU thresholds and transpilation levels against exact values on a 32-qubit stand-in built like G4, before using another attempt.
