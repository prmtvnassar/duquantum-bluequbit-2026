# Problem 4: G1

- Type: graded
- Qubits / circuit IDs: 30
- Maximum points: 300
- Structure: 1D Haar-random chain; 32 two-qubit layers; butterfly q0
- Source: https://app.bluequbit.io/hackathons/2GMaAenu3iSsIC6Z?tab=problems

The QASM files are not published. Run each circuit by ID through BlueQubit.

`circuit_ids.csv` lists the published IDs in qubit order. `local_submission_template.csv` follows the released per-problem `circuit_id,value` format; it is a local template derived from the published IDs, not an organizer download. Values are intentionally blank.

## Result: exact, scored 100%

[`exact_values.csv`](exact_values.csv) holds the exact `<Z_q>` for all 30 IDs, in `circuit_id,value` format. Each `Duke_G1_q` was run on BlueQubit's `cpu` device (exact statevector, 30 qubits, under the 34-qubit CPU limit) for 0 credits. Uploaded to the G1 problem, it scored 100% (corr² = 1). Because these are true values, they also serve as ground truth for tuning MPS/PPS settings for G2–G4.
