# A teammate's submissions: methods and reasoning

All runs used BlueQubit, with each published ID `Duke_<problem>_<q>` run separately by ID from |0...0>, reporting ⟨Z⟩ on qubit q (q0 rightmost in the Pauli string). Values are raw expectation values: no fitting, extrapolation or fusion. Every row's BlueQubit job ID is in the matching `.json` receipt. Scores are as displayed on the website and reported by a teammate. **Total BlueQubit spend for all results below: $0.**

| Problem | File | Method | Score |
| --- | --- | --- | --- |
| G1 | [G1/submitted-v1](G1/) | Exact statevector (`cpu`) | 300/300 (100%) |
| G2 | [G2/submitted-v1](G2/submitted-v1.txt) | MPS, χ = 128 (`mps.cpu`) | 498/600 (corr² ≈ 0.83) |
| G3 | [G3/submitted-v2](G3/submitted-v2.txt) | Pauli-path, ε = 0.001, transpilation level 1 | 534/800 (corr² ≈ 0.67) |
| G3 | [G3/submitted-v3](G3/submitted-v3.txt) | Pauli-path, ε = 0.0003, transpilation level 1 | **773/800 (corr² ≈ 0.97)** |
| G4 | [G4/submitted-v1](G4/submitted-v1.txt) | Pauli-path, ε = 0.0001, transpilation level 3 | 133/1000 (corr² ≈ 0.13) |

## Approach

1. **Use exact simulation wherever it fits.** BlueQubit's `cpu` statevector backend handles up to 34 qubits, and its cost estimate for 30-qubit circuits was $0. G1 (30 qubits) was therefore computed exactly, for a perfect score. G2–G4 (36–38 qubits) exceed the limit and need approximate methods.
2. **Pick the method by circuit structure, and check it on circuits with known answers before spending credits.** We matched each hidden circuit to a solved one with the same structure (published in the problem descriptions):
   - G2 (1D Haar-random chain) ↔ sample S2 (1D Haar chain), plus a 24-qubit test chain with G2's depth whose exact values we computed locally. **MPS** wins on chains: corr² 1.00 at χ = 128 on the test chain, against 0.97 for Pauli-path.
   - G3 (mostly-Clifford grid) ↔ sample S3 (same structure, about 10% non-Clifford gates). **Pauli-path** wins: 100% on S3 locally, against at most corr² 0.51 for MPS.
3. **Tighten precision until consecutive runs agree.** Scoring is the squared Pearson correlation, so the ranking of values matters, not their absolute scale. On G3, agreement between consecutive thresholds rose from corr² 0.00 (ε 0.01 vs 0.001) to 0.80 (ε 0.001 vs 0.0003), and the score rose from 534 to 773 accordingly.
4. **Control cost.** The runner tests one qubit before a batch, cancels any job whose estimated cost exceeds a cap, and cancels any job that runs past a time limit. This is how we found which settings were free, and avoided an estimated ~$360 χ = 256 run on G2.

## Key finding: BlueQubit Pauli-path needs transpilation level 0 or 1 on these circuits

With the default `pauli_path_circuit_transpilation_level = 2`, BlueQubit's Pauli-path returned **exactly 0 for every G3 qubit and every S3 qubit tested**, even though S3's true values are about ±0.1 to 0.6. Testing one sample circuit (`Duke_S3_1`, exact value about −0.538) at ε = 0.01:

| Transpilation level | Result |
| --- | --- |
| 0 | −0.595 |
| 1 | −0.580 |
| 2 (default) | 0.0 |
| 3 | 0.0 |

Uploading the QASM instead of using the stored ID made no difference. Our interpretation: heavier transpilation rewrites the Clifford gates into generic rotations, so Pauli coefficients spread out and all fall below the truncation threshold. Levels 0 and 1 keep the Clifford structure. This single setting turned G3 from a constant-zero vector, which would score 0, into 773/800.

## Limitations

- **G2:** χ = 128 is not fully converged on the 36-qubit chain. A partial χ = 256 run moved values by up to 0.06. Completing it was estimated at about $10.88 and 7 hours per interior job, so we did not pursue it.
- **G3:** the values are converging but not certified. ε = 0.0001 would be the next check.
- Approximate methods carry no certified error bounds; our evidence is agreement on solved circuits and between consecutive precision settings.

## Reproducing

Code is on branch `teammate-1/experiment`: `scripts/run_jobs.py` (BlueQubit runner with cost and runtime limits), `scripts/pps_diagnose.py` (transpilation-level diagnostic), `scripts/calibrate.py`, `scripts/local_sweep.py` and `scripts/make_proxy.py` (local, free calibration on circuits with known answers). Example: `python scripts/run_jobs.py G3 --method pps --settings 0.0003 --transpile 1 --max-cost 25.5 --max-runtime 900 --yes`.

## Note on G2 attribution

The 498/600 G2 score belongs to the χ = 128 file here (sha256 `a92e6e44…`). The record at `../teammate_reported/G2/attempt-01` attributes 498/600 to the χ = 32 candidate (sha256 `4cb0c3c1…`), which is a different file; that χ = 32 file scored 342/600 on the original account (`../../G2/attempt-01`).
