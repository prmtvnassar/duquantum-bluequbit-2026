# G4: PPS baseline, MPS refinement, ensemble

G4 is a 38-qubit OTOC(2) echo (`U, X_b, U†, Z_q, U, X_b, U†`) on a 6×6 grid plus q36/q37 under q30/q31,
16 Haar-random layers, butterfly q0 in the corner. Circuits run only by ID: `cpu` refuses more than 34 qubits,
`gpu` refuses 38, `tensor-network` is not authorised, so every G4 value comes from native MPS (`mps.cpu`,
`mps.gpu`) or Pauli-path propagation (PPS; `pauli-path`), plus post-processing.

The workflow that worked: **PPS as the baseline → refine rows with high-χ MPS → remove the directions MPS
showed to be null → mix the refined vectors.** Numbers below are website scores unless marked as
known-answer (exact proxy) scores; `python scripts/g4_pps_mps_summary.py` prints them offline.

## 1. Score ladder

| Vector | File | Score |
| --- | --- | ---: |
| MPS χ32, all rows | `submissions/candidates/G4/direct-930f7e5b7d14.csv` | 0 |
| **PPS ε 1e-4, level 3 (baseline)** | `submissions/teammates/teammate-1/G4/submitted-v1.csv` | **133** |
| + MPS χ256 on q0 | `submissions/candidates/G4/pps-mps256-q0-score139.csv` | 139 |
| + MPS χ256 on q0–q1 | `submissions/candidates/G4/pps-mps256-q0q1-score145.csv` | 145 |
| + MPS χ256 on q0–q3, q6–q9 | `submissions/candidates/G4/pps-mps256-8rows-score165.csv` | 165 |
| MPS χ64, all rows | `submissions/candidates/G4/direct-8f66fe538349-score0.csv` | 0 |
| Geometry prior from exact proxies | `submissions/candidates/G4/geo-c9cd356165e4-score2.csv` | 2 |
| PPS baseline minus null directions | `submissions/candidates/G4/resid-pps-a35b4b7d167f-score199.csv` | 199 |
| 165 vector minus null directions | `submissions/candidates/G4/resid-v165-96e3fec30972-score195.csv` | 195 |
| **Final ensemble** | `submissions/candidates/G4/G4_final_ensemble_2.csv` | **284** |

## 2. Why MPS alone scores 0

- Not converged: on q0 / q1 / q4 / q19, χ16 → χ32 → χ64 gave 0.559/0.270/0.098, 0.136/−0.054/0.007,
  −0.006/0.332/0.493 and 0.362/0.288/0.084: values move by O(0.1–0.5) and change order.
- Agreement is not accuracy: the χ32 and χ64 vectors agree in shape (ρ ≈ 0.96) and both score 0. Two
  unconverged cohorts share their error.
- Echo bias: a truncated MPS loses entanglement, so U† undoes U too well and far rows drift toward +1 (G4 χ32:
  q30–q37 at 0.64–0.96). On exact 4×5 depth-16 proxies MPS χ8–64 scores 113–227 and is biased by about +0.22
  where the truth is −0.02…0; on the 32-qubit known-answer circuit PG4c, MPS χ128 scores 0 (ρ −0.49).
- Raising χ further was not affordable as a full-vector strategy: GPU χ1024 quotes $72 per row.

MPS is therefore used for two things only: high-χ values on selected rows (refinement), and the χ32/χ64
vectors as **measured-null directions** to subtract.

## 3. Why PPS is the baseline

- The circuits are echoes: blocks U and U† are exact inverses (checked on the samples). Transpilation level 3
  cancels `g·g†` pairs outside the light cone; locally, level 3 cut S3 from 1568 CZs to ~300–414.
- Native levels 1 and 2 returned exact zeros on G4 (q0, q19, q37 at ε 1e-3; q4 at ε 1e-3 and 1e-4).
  Level 3 returned signal: q37 = −0.018 at ε 1e-3 and +0.099 at ε 1e-4.
- Native calibration on sample rows with exact answers (level 3): S3_17 ε 1e-3 error 0.008; S2_10 ε 1e-3
  error 0.077, ε 1e-4 error 0.098. Accuracy is not monotonic in ε (as reported by Mazumder et al. and
  Gharibyan et al., `papers/`), so "lower ε until it looks converged" is not a safe stopping rule.
- At ε ≥ 1e-3 every early-contact row on G4 reads ~0 (the true values there are at the `2^(-n/2)` floor);
  the complete ε 1e-4, level-3 vector scored **133**. On PG4c, PPS scores 224 (ε 1e-3) and 301 (ε 1e-4)
  against the exact answer.
- The finest CPU-quotable ε at 38 qubits is ~3e-5; 2e-5 and below are rejected by the service.

## 4. MPS refinement of the PPS baseline (133 → 165)

A teammate replaced PPS values by native MPS χ256 values on rows near the butterfly: q0 → 139, q0–q1 → 145, q0–q3 and q6–q9 → 165. Each step was a
complete 38-row vector; the remaining rows keep their PPS values.

## 5. Removing null directions (133 → 199, 165 → 195)

The χ32, χ64 and geometry-prior vectors scored 0, 0 and 2, so each has |ρ| ≲ 0.045 with the reference.
Regressing a signal-carrying vector on `[1, χ32, χ64, geo]` and keeping the residual removes variance that
cannot correlate with the reference while keeping the vector's own signal.

- PPS baseline: R² on the nulls 0.48, scored **199**.
- 165 vector: R² 0.35, scored **195**.
- Known-answer check on PG4c: PPS ε 1e-4 minus its projection on MPS χ128 goes from 301 to **424** against
  the exact answer. Adding a prior that is *not* null there (it correlates with the exact answer, ρ −0.61)
  lowers it to 297. Rule: project out only directions whose scores show them to be null.
- `python scripts/build_residual_candidate.py` rebuilds both vectors byte for byte.

## 6. Final ensemble (284)

`submissions/candidates/G4/G4_final_ensemble_2.csv`, uploaded by a teammate, scored **284**. It mixes refined
G4 vectors. Its correlation with the PPS+MPS 165 vector is 0.80 and with the 199 residual 0.83. Its dominant
ingredient (correlation 0.98) is a refinement vector that was fitted to the website scores of earlier
whole-vector uploads rather than produced by a simulator. That is stated in its method note
(`G4_final_ensemble_2.txt`). There is no build script for this file in the repository.

## 7. What did not help

| Tried | Result |
| --- | --- |
| Raising MPS χ (χ16 → χ64 CPU, χ128 GPU on all 38 rows) | Values unconverged; χ32 and χ64 vectors both 0 |
| PPS at ε ≥ 1e-3, or levels 1/2 | Zeros on G4 |
| Geometry prior (proxy class means by light-cone arrival time) | 400–700 on held-out proxies, 2 on G4 |
| Geometry prior + PPS blend | 50 |
| Averaging or extrapolating across χ or ε (tested on S2 with exact answers) | Never beat the best single input (cross-χ mean 98.5 vs 99.9 raw; Richardson unreliable) |
| Correcting MPS with multi-observable features (sample lab) | Nothing beat raw MPS ⟨Z_q⟩ on scrambled rows |

## 8. Workflow improvements made on G4

- **All-Z observable lists**: one MPS job returns ⟨Z_j⟩ for all 38 qubits at the same quote as a single
  observable (`observables="all_z"`, `scripts/run_feature_jobs.py`; `research_notes/plumbing_all_z.md`).
- **GPU cost model**: `mps.gpu` χ128 quotes $2.73 per row but billed $0.20 per ~1-minute job; the rolling-hour
  GPU gate now uses twice the median observed compute time once at least three receipts exist (the quote
  still bounds each job's timeout).
- **Adapter fixes**: SDK cost estimates are in cents (the in-flight guard compared them with dollars and
  canceled two jobs at $0); `--attempt N` gives a deliberate relaunch its own key and ledger row.
- **Known-answer testbeds at $0**: exact proxies of the G4 generator (`labs/proxy_lab`, 28 instances,
  16–25 qubits), PG4c (`labs/pg4c`, 32 qubits, native PPS/MPS + exact), and a local PPS ε ladder
  (`labs/pps_ladder_lab`). Every post-processing rule was scored on these before use.
- Recorded G4 spend: $7.80 (GPU), after which the account balance was exhausted.

## 9. The remaining simulator lever

PPS at level 3 and ε 3e-5 on the 22 late-contact rows (the rows the butterfly reaches in the last
3–7 layers). On a 24-qubit G4-construction testbed, one ε decade on those rows lifted the known-answer
score from 213 to 327 (`research_notes/pps_ladder_lab/REPORT.md`). It was not run: the account had no
funds left.

Sources: `research_notes/proxy_lab/REPORT.md`, `research_notes/sample_lab/REPORT.md`,
`research_notes/pps_ladder_lab/REPORT.md`, `research_notes/plumbing_all_z.md`, the job ledger in `runs/`,
and the figures in `reports/figures/g4_techniques/`.
