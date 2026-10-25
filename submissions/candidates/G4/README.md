# G4 vectors

Every G4 vector that was scored on the website, with its score in the filename where known. The method and
reasoning are in [research_notes/G4_PPS_MPS.md](../../../research_notes/G4_PPS_MPS.md).

| File | Method | Score |
| --- | --- | ---: |
| `direct-930f7e5b7d14.csv` (+ `.json` row manifest, `.feedback.json`) | MPS χ32 (CPU), all 38 rows | 0 |
| PPS baseline: [`../../teammates/teammate-1/G4/submitted-v1.csv`](../../teammates/teammate-1/G4/submitted-v1.csv) | Pauli-path ε 1e-4, transpilation level 3, all 38 rows | 133 |
| `pps-mps256-q0-score139.csv` | PPS baseline with MPS χ256 on q0 | 139 |
| `pps-mps256-q0q1-score145.csv` | PPS baseline with MPS χ256 on q0–q1 | 145 |
| `pps-mps256-8rows-score165.csv` | PPS baseline with MPS χ256 on q0–q3, q6–q9 | 165 |
| `direct-8f66fe538349-score0.*` | MPS χ64 (CPU), all 38 rows | 0 |
| `geo-c9cd356165e4-score2.*` | Geometry prior from exact proxies (used only as a null direction) | 2 |
| `resid-pps-a35b4b7d167f-score199.*` | PPS baseline minus its projection on [χ32, χ64, geo] | 199 |
| `resid-v165-96e3fec30972-score195.*` | 165 vector minus its projection on [χ32, χ64, geo] | 195 |
| **`G4_final_ensemble_2.csv`** (+ `.txt` method note) | Ensemble of refined vectors; dominant ingredient fitted to earlier whole-vector scores (see the note) | **284** |

`.txt` files hold the method note for the submission form; `.json` files hold the per-row job manifest or the
build parameters. The residual vectors are rebuilt by `python scripts/build_residual_candidate.py`.
