# Problem 6: G3

- Type: graded
- Qubits / circuit IDs: 36
- Maximum points: 800
- Structure: 6x6 mostly-Clifford grid; 24 two-qubit layers; butterfly q14
- Source: https://app.bluequbit.io/hackathons/2GMaAenu3iSsIC6Z?tab=problems

The QASM files are not published. Run each circuit by ID through BlueQubit.

`circuit_ids.csv` lists the published IDs in qubit order. `local_submission_template.csv` follows the released per-problem `circuit_id,value` format; it is a local template derived from the published IDs, not an organizer download. Values are intentionally blank.

## Result: Pauli-path ε=0.001, transpilation level 1, scored 534/800 (corr² ≈ 0.67)

[`pps_eps0.001_level1_values.csv`](pps_eps0.001_level1_values.csv) is the submitted file (`circuit_id,value`, 36 IDs), uploaded as `G3_v2.csv`.

- **Method:** BlueQubit `pauli-path`, `pauli_path_truncation_threshold = 0.001`, **`pauli_path_circuit_transpilation_level = 1`**, each `Duke_G3_q` run by ID, measuring ⟨Z_q⟩. Raw values, no fitting. Cost: 0 credits (about 40 s per job).
- **Important: BlueQubit's default transpilation level (2) returns exactly 0 on these circuits.** All 36 G3 qubits came back 0 at level 2 for ε = 0.01 and 0.001, and so did S3 (whose real values are about ±0.1–0.6). A diagnostic on `Duke_S3_1` (exact ≈ -0.538), run with `scripts/pps_diagnose.py` on branch `kevin/experiment`, gave: level 2 → 0.0, level 3 → 0.0, **level 0 → -0.595, level 1 → -0.580** (all at ε = 0.01). Uploading the QASM instead of using the stored ID made no difference. Use level 0 or 1 for Pauli-path on the challenge circuits.
- **Why Pauli-path:** G3 is a mostly-Clifford grid like S3. Local Pauli-path at ε = 0.01 scored 100% on S3, while local MPS on S3 reached at most corr² 0.51 (χ = 16–64).
- **History:** ε = 0.01 at level 1 (`G3_v1`) left 33 of 36 values at exactly 0. ε = 0.001 left 9 of 36 at 0 and scored 534/800. The two runs are uncorrelated (corr² = 0.00), so G3's small values (mostly within ±0.1) are not yet converged; finer ε is the next step.
