# sample-lab: can MPS-feature post-processing beat raw <Z_q> in the unconverged regime?

Session 2026-10-24/25, $0: no BlueQubit calls, no writes to `runs/`, `results/workflow/`,
`submissions/` or `problems/*/selected.csv`. Code `labs/sample_lab/{mps_features.py,
exact_features.py, estimators.py, write_report.py}`; data `features_S2.json`, `features_S3.json`
(+`_part2`), `exact_features_S2.json`; full tables `labs/sample_lab/results.md` / `results.json`.
Deterministic (quimb SVD, no sampling).

## 1. Setup

* Engine: copy of `engines.py::run_mps` (quimb `CircuitMPS`, `swap+split`, `cutoff=0`, complex128)
  returning from the final MPS of each ID all single-site <Z_j>, <X_j>, <Y_j>, the un-normalised
  norm^2 (quimb `fidelity_estimate`), the entropy at every cut and the actual max bond.
* S2 (16-qubit Haar chain, butterfly q0, 16 IDs): chi 2, 4, 8, 16, 32, 64, 128 (1-15 s per ID).
  S3 (30-qubit mostly-Clifford 5x6 grid, butterfly q14, 30 IDs): chi 4, 8, 16, 32 (3-30 s per ID);
  chi64 took 650-890 s per ID here (one ID done, norm^2 still ~1e-17), so it was not swept.
* References: `submissions/S2|S3/attempt-01.csv` (both scored 100/100). Metric 100*Pearson^2 on the
  whole sample vector; max abs error of the unscaled estimator values in parentheses.
* Row features per (ID, chi): `zq=<Z_q>`, `meanZ`, `meanZ_far` = mean over the `max(3, n//4)` sites
  with the largest `min(dist(j,butterfly), dist(j,q))` (Manhattan; chain for S2, 5x6 grid for S3),
  `zb=<Z_butterfly>`, `dist_qb`, `instab=|zq(chi)-zq(chi/2)|`, sign flip, `xq`, max entropy, log norm^2.
* Held-out protocol: shrinkage thresholds and ridge weights are fitted on one family and scored
  on the other; closed-form estimators have no fitted parameters (far-set size n//4 fixed a priori).

## 2. Scores, estimator x chi x sample (100*rho^2; max abs err)

S2 (unconverged analogue of G4 = chi 4-16; raw 95.8 at chi32, 99.9 at chi64):

| estimator | chi2 | chi4 | chi8 | chi16 | chi32 | chi64 | chi128 |
|---|---|---|---|---|---|---|---|
| (a) raw zq | 26.9 (0.91) | 49.4 (0.68) | 81.4 (0.45) | 84.4 (0.54) | 95.8 (0.28) | 99.9 (0.04) | 100.0 |
| (b) zq/meanZ | 25.3 | 46.7 | 77.1 | 78.8 | 89.0 | 96.6 | 97.5 |
| (b) zq-meanZ | 28.0 | 43.0 | 80.8 | 87.0 | 96.8 | 96.1 | 94.5 |
| (b) zq/meanZ_far | 24.7 (4.96) | **72.1** (2.97) | **92.7** (3.44) | **90.3** (0.92) | 93.5 | 98.5 | 99.0 |
| (b) zq/max(meanZ_far,0.2) | 37.8 | 67.9 | 92.4 | 90.3 | 93.5 | 98.5 | 99.0 |
| (b) zq-meanZ_far | 45.7 | 70.5 | 88.7 | 85.8 | 90.6 | 95.3 | 96.1 |
| (b) zq-zb | 1.5 | 18.9 | 36.5 | 44.3 | 28.4 | 13.0 | 10.9 |
| (b) (zq-(1-meanZ_far))/meanZ_far | 19.1 | 7.8 | 7.1 | 87.8 | 98.9 | 98.0 | 96.5 |
| meanZ alone / zb alone | 0.2 / 30.8 | 39.6 / 22.9 | 64.1 / 55.0 | 75.0 / 68.6 | 89.8 / 80.8 | 95.0 / 87.0 | 95.6 / 88.2 |
| -distance prior alone | 73.8 | 73.8 | 73.8 | 73.8 | 73.8 | 73.8 | 73.8 |
| mean(zq(chi), zq(chi/2)) | 26.9 | 50.0 | 73.0 | 86.1 | 90.8 | 98.5 | 100.0 |
| (c) shrink hard / soft, tau fitted on S3 | 26.9 / 26.9 | 49.4 / 49.4 | 81.4 / 79.6 | 84.4 / 85.4 | 95.8 / 95.9 | 99.9 / 99.8 | 100 / 100 |
| (d) ridge5 (zq, meanZ, zb, dist, instab), trained on S3 | 34-38 | 18-24 | 49-55 | 64-68 | 75-79 | 81-85 | 83-86 |
| (d) ridge10 (+meanZ_far, flip, xq, entropy, zq_prev), trained on S3 | 30-40 | 8-27 | 38-58 | 67-69 | 75-79 | 81-84 | 84-86 |

S3 (held-out grid family): raw 7.2 / 1.0 / 2.1 / 1.4 at chi 4 / 8 / 16 / 32. At every affordable
chi the mostly-Clifford grid state collapses to a stabiliser-like MPS: norm^2 1e-47..1e-17, and
26 of 30 rows read exactly 0 with a few +-1 (chi8: q18=+0.914, q22=-1.000, q28=-1.000 vs exact
0, -0.679, +1.000). No estimator extracts shape from this: the best values are 19.6 (zq/meanZ_far,
chi16) and 19.7 ((zq-(1-F))/F, chi16), both with denominators ~1e-9 and max abs errors 1e4-1e9,
i.e. noise; zq-meanZ_far 8.0/1.1/0.7/1.9; shrinkage 7.2/6.6/11.0/0.3; ridge trained on S2 0-8.4.
S3 therefore neither confirms nor refutes any estimator; it only shows that un-floored ratios explode.

Fitted quantities: the shrinkage threshold chosen on either family is tau=1.0 (= never shrink; even
in-sample on S2 the best tau leaves raw unchanged at chi4/8 and gains +2.3 at chi16). Ridge weights
trained on S3 (standardised): zq -0.04, meanZ -0.04, zb +0.02, dist +0.01, instab +0.04, i.e. no
transferable signal; trained on S2 they load on dist (+0.27) and zq (+0.23), which is the S2 chain
profile and does not exist on S3 (exact S3 vs distance: 0.3).

## 3. Where the only gain comes from (S2 per-row mechanism)

The far-site ratio helps on S2 by re-ordering the large rows: at chi4 the out-of-cone rows q12-15
(exact 1.000) read 0.47/0.43/0.83/0.71 and the cone-edge rows q10/q11 (exact 0.58/0.61) read
0.03/-0.03, while their far-site means are 0.13-0.36 (sites that are exactly 1 or ~0.8 in the exact
state); dividing lifts q12-15 to 2.6-4.0 and restores the ordering q12-15 > q10/11 > scrambled rows.
Scores restricted to row subsets (features unchanged; ratio = zq/max(meanZ_far,0.2), diff = zq-meanZ_far):

| S2 rows (raw / ratio / diff) | chi4 | chi8 | chi16 | chi32 | chi64 |
|---|---|---|---|---|---|
| all 16 | 49.4 / 67.9 / 70.5 | 81.4 / 92.4 / 88.7 | 84.4 / 90.3 / 85.8 | 95.8 / 93.5 / 90.6 | 99.9 / 98.5 / 95.3 |
| in-cone q0-11 | 0.5 / 0.2 / 12.5 | 38.5 / 74.2 / 61.9 | 75.8 / 82.7 / 77.6 | 91.9 / 91.6 / 86.2 | 99.7 / 99.3 / 93.1 |
| scrambled q0-9 (exact magnitude <= 0.14) | 10.9 / 9.1 / 15.7 | 21.0 / 24.7 / 18.3 | 50.0 / 46.0 / 41.8 | 69.6 / 62.6 / 55.0 | 97.5 / 93.3 / 68.0 |

On the scrambled rows, the regime the G4 ledger indicates (native chi256 scores 139; q0/q1/q4/q19
move by 0.1-0.3 between chi16/32/64; PPS ~0), the normaliser is neutral to harmful. The low-chi
error there is not a per-circuit fidelity factor: cone-edge rows are biased upward (q8/q9, exact
0.105/0.063, read 0.51/0.60 at chi16; G4 q0 falls 0.56 -> 0.27 -> 0.10 from chi16 to chi64), and
far sites (0.85-0.9 at chi16) cannot measure that. Across-chi features do not help either: instab
is as large for the correct big rows (q10-15: 0.35-0.54 at chi4) as for noisy ones, and
mean(zq, zq_prev) sits within +/-8 points of raw with either sign.

## 4. Verdict

Nothing beats raw <Z_q> robustly on held-out data in the unconverged regime. One pre-registered
closed-form estimator, `<Z_q> / mean of <Z_j> over the far sites`, beats raw on S2 by +22.7 / +11.2
/ +5.9 points at chi 4 / 8 / 16 and loses 1-2 points at chi >= 32, but (i) the gain comes entirely
from rows that are exactly or nearly +1 in the exact vector (outside or at the edge of the light
cone), (ii) on the scrambled rows that resemble G4 it is neutral-to-negative at every chi, (iii) the
only second family, S3, has no MPS signal at any affordable chi, so the gain was never confirmed
out-of-family, and (iv) un-floored ratios explode when far-site means are ~0. Shrinkage by
chi-instability (c) selects "never shrink" on both families; cross-family ridge (d) is far below raw
at every chi (S2 scored with S3 weights: 18-27 vs 49 at chi4, 49-58 vs 81 at chi8, 64-69 vs 84 at
chi16). Recommendation: submit raw MPS <Z_q> at the highest chi available per row (unchanged policy).

## 5. The single estimator worth plumbing (conditional; not the default)

Only if the G4 all-Z vectors show far-site means well below 1 (as S2 does at chi <= 16: 0.13-0.6 for
the large rows) is there a candidate:

    est_q = <Z_q> / max( mean_{j in Far(q)} <Z_j> , 0.2 )
    Far(q) = the 9 (= 38//4) sites j with the largest min( d(j, q0), d(j, q) ),
             d = Manhattan distance on the G4 layout (qubit = row*6+col for q0-35; q36=(6,0), q37=(6,1))

Features per G4 row (one job per ID, same price as one observable): all 38 single-site <Z_j> from
the same MPS run at the same chi; nothing else. Pre-registered constants: far-set size n//4 (k=4-6
on S2 gave +15 to +23 / +9 to +13 / +6 at chi 4/8/16; k=2 and k=8 are worse and unstable), floor
0.2 (costs <= 4 points at chi4 on S2, nothing elsewhere; essential on S3-like degeneracy). Decision
rule before using it: if every G4 far-site mean is > 0.8, the ratio changes rows by < 25% and cannot
help; keep raw. The chi32 G4 pilots (0.64-0.96 at distance >= 5) point to exactly that situation.

## 6. Risks for transfer to 38 qubits

* G4 has no sites outside the geometric cone (16 layers, 6x6) and its exact vector is probably
  scrambled everywhere; the mechanism of Section 3 then does not exist, and dividing by far-site
  noise lowers the score (S2 scrambled rows: -2 to -7 points at chi 8-32).
* The native kernel is not quimb: truncation order, swap network and normalisation differ, so the
  sign and size of the low-chi bias measured here need not carry over (the G4 ledger already shows
  the opposite bias sign from the S2 out-of-cone rows).
* S3 shows that a grid with distance-6 couplings can leave the single-site Z vector with zero
  information at chi <= 64; any estimator applied to such a vector returns noise with a misleadingly
  nonzero score (up to ~20 here by chance on 30 rows).
* 16 and 30 rows give coarse score estimates; +/-5 points on S2 is within row-to-row scatter.
* Fitted estimators (ridge, shrinkage) carry no transferable signal between the two families; what
  they learn is the geometry profile of the training family, not truncation error.

## 7. Reproduce

    PYTHONPATH=src .venv312/Scripts/python.exe labs/sample_lab/mps_features.py --sample S2 --chis 2 4 8 16 32 64 128
    PYTHONPATH=src .venv312/Scripts/python.exe labs/sample_lab/mps_features.py --sample S3 --chis 4 8 16 32
    PYTHONPATH=src .venv312/Scripts/python.exe labs/sample_lab/exact_features.py
    PYTHONPATH=src .venv312/Scripts/python.exe labs/sample_lab/estimators.py   # writes results.md / results.json
    .venv312/Scripts/python.exe labs/sample_lab/write_report.py
