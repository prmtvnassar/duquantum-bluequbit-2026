# Problem 4: G1

- Type: graded
- Qubits / circuit IDs: 30
- Maximum points: 300
- Structure: 1D Haar-random chain; 32 two-qubit layers; butterfly q0
- Source: https://app.bluequbit.io/hackathons/2GMaAenu3iSsIC6Z?tab=problems

The QASM files are not published. Run each circuit by ID through BlueQubit.

`circuit_ids.csv` lists the published IDs in qubit order. `local_submission_template.csv` follows the released per-problem `circuit_id,value` format; it is a local template derived from the published IDs, not an organizer download. Values are intentionally blank.

## Result: exact, scored 100%

[`exact_values.csv`](exact_values.csv) holds numerical exact `<Z_q>` values for all 30 IDs, in `circuit_id,value` format. Each `Duke_G1_q` was run on BlueQubit's `cpu` device for 0 credits. Kevin reports a 100% official score. All values match his source job ledger and submitted CSV; provenance is in [runs/imports/kevin](../../runs/imports/kevin/).

The workflow reuses this complete exact anchor and schedules no duplicate G1 simulations. These values are ground truth for **G1 only**. They can assess genuine approximate G1 runs and inform method selection for related Haar-chain problems; they are not labels for G2–G4. The retained [submission receipt](../../submissions/teammates/kevin/G1/submitted-v1.json) distinguishes the teammate-reported score from an independently observed website score.
