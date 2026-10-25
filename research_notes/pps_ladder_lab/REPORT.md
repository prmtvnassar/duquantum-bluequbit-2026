# PPS delta-ladder lab: local known-answer testbed (INTERIM, background jobs still running)

2026-10-25, $0, no BlueQubit calls. Code `scratch/pps_ladder_lab/{make_proxies,run_ladder,run_mps,pg4c_reconstruct,analyze,check}.py`
(seeded, incremental, re-runnable); data `scratch/pps_ladder_lab/data/` (exact_*.json, ladder_*.json, mps_*.json, *.log, summary.json).
Handed back early: the eps 1e-4 levels, seed 3 and chi64 were still computing when this was written.
Re-run `PYTHONPATH=src .venv312/Scripts/python.exe scratch/pps_ladder_lab/analyze.py` once the logs stop to refresh every table.

## 1. Testbed

- 4x6 depth-16 Haar u3+cz proxies (24 q, common.py rule H0,V0,H1,V1, corner butterfly, same echo), seeds 1,2 exact (Aer
  statevector, 48 s/row at 12 threads, 20 min/instance; seed 3 running). 4x7 (28 q) rejected: 4.3 GB state, x16 per gate and
  1.2x gates => ~12 h for 28 rows. Slack map: col 5 = 4, col 4 = 6, rest >= 8, so the rim (slack 3-7) is
  q4,q5,q10,q11,q16,q17,q22,q23 (8 of 24). Exact rims are 100 % negative, |v| 0.015-0.069 (s1) / 0.001-0.049 (s2); bulk |v| <= 0.009.
- PG4c (32 q, Kevin's 5x6+2 G4-construction proxy; native exact, native PPS 1e-4/1e-3 L3, MPS128 in `scratch/pg4c.csv`)
  reconstructed locally from the historical `scripts/make_proxy.py` (commit e6707fa; colour order H0,H1,V0,V1; qiskit
  `random_unitary(4, seed)` from `default_rng(5)`; `--extra 2` guessed as the 6x6 colour lists filtered to q<30 or q in {30,31}).
  Validation: local coefficient PPS L3 eps 1e-3 gives q5 -0.0267 / q10 -0.0192 / q11 +0.0060 vs native 1e-3 -0.0270 / -0.0149 /
  +0.0079 (native 1e-4: -0.0289 / -0.0266 / +0.0082). The reconstruction is right and the local kernel reproduces native
  behaviour: same non-zero rows, same signs, magnitudes within ~30 %. PG4c rim = 16 rows (q4,5,10,11,16,17,22,23,24-31), 100 %
  negative, |v| 0.001-0.10.

## 2. Ladder feasibility with the local kernel (`coefficient_pps.propagate`, level 3, cap 2e7 terms, 16 GB RAM)

| eps | peak terms (24 q rim row) | wall/row | RSS | status |
|---|---|---|---|---|
| 1e-3 | ~1e5 | 8-16 s | <0.3 GB | complete |
| 3e-4 | 0.8-1.2e6 | 120-220 s | ~0.5 GB | complete (s1 all rows; PG4c 17/32 at hand-back) |
| 1e-4 | 4.2e6 (q23) | 464 s | 1.4 GB | check complete; all rows running (3 workers) |
| 3e-5 | > 2.2e7 at gate 522 of 2577 | 1420 s to the cap | 4.9 GB | cap hit: not computable here (extrapolates to 5e7-1e8 terms) |
| 1e-5 .. 1e-6 | not attempted | | | out of reach (x10 terms per 3.3x finer eps) |

The local ladder is therefore 1e-3 / 3e-4 / 1e-4; 3e-5 and finer are a feasibility negative on this machine, not a numerical one.

## 3. Results at hand-back (1000 x Pearson^2 vs exact; `analyze.py`)

4x6 s1 (n=24): eps 1e-3 213 (rho +0.46; 8 nonzero rows, 5 of 8 rim; rim sign agreement 0.25) -> eps 3e-4 327 (rho +0.57;
16 nonzero, all 8 rim rows nonzero, rim sign agreement 0.75). Rim-only score 605 -> 612. Rim rows:

| q (slack) | exact | 1e-3 | 3e-4 |
|---|---|---|---|
| q4 (6) | -0.050 | +0.0016 | -0.0006 |
| q5 (4) | -0.015 | 0 | +0.0002 |
| q10 (6) | -0.037 | +0.0006 | -0.0007 |
| q11 (4) | -0.026 | 0 | -0.0029 |
| q16 (6) | -0.034 | 0 | -0.0017 |
| q17 (4) | -0.023 | -0.0020 | -0.0025 |
| q22 (6) | -0.003 | +0.0129 | +0.0129 |
| q23 (4) | -0.069 | -0.0103 | -0.0093 |

Magnitudes stay 5-30x below exact at 3e-4 (q23 -0.009 vs -0.069); the gain from 1e-3 to 3e-4 comes from more rim rows turning
non-zero with the right sign, not from convergence. Check at 1e-4: q23 = -0.0027 (3e-4 -0.0093, 1e-3 -0.0103): non-monotone in
magnitude, sign held.

- Monotonicity (rim rows, adjacent eps both nonzero): 5 pairs, 2 sign flips (q4, q10), |error| decreased at finer eps in 3/5.
- Stability rule (finest eps where |change| < 50 % across adjacent eps, else 0): 247 (6 rows) vs finest-eps 327: loses.
  Thresholds 25 % / 100 %: 203 / 247. Median over eps 273, mean 273: both lose to the finest eps.
- Splice: base 1e-3 (213) with rim rows replaced by 3e-4 -> 297; 3e-4 everywhere 327. Rim splice captures ~75 % of the gain.
- Residual trick (regress on [1, local chi32]): 1e-3 213 -> 214; 3e-4 327 -> 318. Local chi32 scores 18 (rho -0.13) here, so
  there is nothing to project out; the G4 +66 depended on MPS being a sizeable null direction. chi64 pending.

PG4c (n=32): local 1e-3 314 (rho +0.56; 15 nonzero rows, 11/16 rim; rim sign agreement 0.38) vs native 1e-3 224 and native
1e-4 301 (rim-only 348). Native MPS128 238 but rho -0.49 (anti-correlated; the clipped grader gives 0). Native 1e-4 resolves
only q5/q10 (-0.029/-0.027 vs exact -0.100/-0.079) and gives ~0 or the wrong sign on the other 9 rim rows with |exact| > 0.03
(q16, q17, q23-q31); local 1e-3 shows exactly the same pattern. Local 3e-4 / 1e-4 rows pending.

## 4. Verdict on native eps 3e-5 on G4's 16 rim rows

1. The local kernel is a credible proxy for native (PG4c: same non-zero rows, signs and magnitudes at 1e-3).
2. Each 3.3x step in eps raised the proxy score (213 -> 327 on s1; native 224 -> 301 on PG4c) by turning more rim rows non-zero
   with the right sign; values remain 3-30x too small and are not monotone (q23: -0.010, -0.009, -0.003). Expect 3e-5 on G4's rim
   to behave like 3e-4 vs 1e-3 here: a few more rim rows (q30-35, q24-27, col 5) at ~1e-3..1e-2, sign mostly right (75 % on s1)
   with ~25 % flips. Plausible G4 gain +50..+120 over 133, with a real risk that a flipped sign on a large row (q36/q37) costs more.
3. Do not post-process the ladder: stability rule, median and mean all lost to the finest eps. Splice finer rim rows into the
   coarse base only when the finer run is incomplete (recovers ~75 % of the full gain).
4. The residual trick helps only where MPS is a strong null direction (G4 chi32/64 = 0; PG4c MPS128 rho -0.49 -> +123); on the
   24-q proxy with chi32 rho -0.13 it is neutral. Keep it for G4 (null measured there); expect +60-120 at most.
5. Nothing in the ladder approaches the exact rim magnitudes; 800 is unreachable by PPS at any admissible eps.

Pending (background, complete without intervention; then re-run analyze.py): s1/PG4c eps 1e-4 all rows, seeds 2/3 ladders
(`run_ladder.py 4 6 2 --eps=1e-3,3e-4,1e-4 --cap=2e7 --workers=3`, same for 3), chi64 on s1, seed 3 exact.
