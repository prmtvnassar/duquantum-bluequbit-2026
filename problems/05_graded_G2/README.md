# Problem 5: G2

- Type: graded
- Qubits / circuit IDs: 36
- Maximum points: 600
- Structure: 1D Haar-random chain; 18 two-qubit layers; butterfly q18
- Source: https://app.bluequbit.io/hackathons/2GMaAenu3iSsIC6Z?tab=problems

The QASM files are not published. Run each circuit by ID through BlueQubit.

`circuit_ids.csv` lists the published IDs in qubit order. `local_submission_template.csv` follows the released per-problem `circuit_id,value` format; it is a local template derived from the published IDs, not an organizer download. Values are intentionally blank.

## Result: MPS χ=128, scored 498/600 (corr² ≈ 0.83)

[`mps_chi128_values.csv`](mps_chi128_values.csv) is the submitted file (`circuit_id,value`, 36 IDs), uploaded as `G2_v1.csv`.

- **Method:** MPS on BlueQubit (`mps.cpu`, bond dimension χ = 128), each `Duke_G2_q` run by ID, measuring ⟨Z_q⟩. Raw values, no fitting. Cost: 0 credits.
- **Why MPS and χ = 128:** G2 is a 1D Haar-random chain, which suits MPS. On sample S2 (a 1D Haar chain, exact values known) MPS reached corr² = 1.00 at χ = 32; on a 24-qubit local test chain with G2's depth (18 layers, butterfly at one end, exact values computed locally) MPS reached corr² = 1.00 at χ = 128, while Pauli-path only reached 0.97 at ε = 0.001.
- **Profile:** about 1 at both ends (q0–3, q32–35), about 0 around the butterfly (q18), as expected for a mid-chain butterfly.
- **Why not 100%:** χ = 128 is not converged on the real 36-qubit chain. A partial χ = 256 run moved values by up to 0.06 (q2: 0.916 → 0.854). Finishing χ = 256 was not pursued: interior-qubit jobs are estimated at about $10.88 and 7 hours each (about $360 for the rest), too much for the expected gain.
