# Proxy lab: what approximate methods can score on exact G4-like OTOC(2) proxies

2026-10-24 21:00-23:30 local, $0, no BlueQubit calls. Code `labs/proxy_lab/{common,make_proxies,run_methods,analyze,plot}.py`
(seeded, re-runnable: `make_proxies.py R C depth seeds...`, `run_methods.py <pattern> --chi=.. --eps=..`, `analyze.py`, `plot.py`).
Data `labs/proxy_lab/data/exact_*.json` (U-block QASM + exact vector), `methods_*.json`, `summary.json`, `tables.md` (every table,
all methods, per instance). Figures in this directory: `fig_exact_profile.png`, `fig_method_scores.png`.

## 1. Geometry and echo (step 1), verified on the public samples

- `Duke_S3_0.qasm` (5x6, qubit = row*6+col): block 0 has 196 distinct two-qubit gates = 16 layers of the period
  **[H0, V0, H1, V1]** (H0: (r,c)-(r,c+1) even c; V0: (r,c)-(r+1,c) even r; H1: odd c; V1: odd r). The per-qubit partner sequence of
  the file equals the rule exactly (`common.grid_layers`). S3 uses 2 CZ per gate (mostly Clifford); `Duke_S2_0` (chain) is 12 layers of
  [even pairs, odd pairs] with 3 CZ per Haar gate. Proxies use Haar `unitary_group(4)` gates decomposed to u3+cz (3 CZ, fidelity 1.0).
- Echo: blocks are U, X_b, U^dag, Z_q, U, X_b, U^dag then measure Z_q; block 2 == block 0 and block 3 == block 1 textually, block 1 is
  the gate-reversed inverse of block 0 (S2 and S3). Value = <0|(Z_q W)^4|0> with W = U^dag X_b U (second-order OTOC).
- Consequence used throughout: W is grown by conjugating X_b with the layers of U in **reverse** order, so the contact layer of a qubit is
  counted from the last layer of U. Define **slack = depth - contact layer** (layers a qubit has spent inside the support of W; -1 = never
  reached, value exactly +1). G4 slack map (6x6 + q36/q37): q36,q37 = 3; col 5 (q5,11,17,23,29,35) = 4; row 5 (q30-34) = 5; col 4
  (q4,10,16,22,28) = 6; row 4 (q24-27) = 7; the other 16 qubits >= 8 (q0 = 16) (corrected; an earlier version of this report said 22). Nothing in G4 is outside the geometric cone.

## 2. Exact proxies (step 2): 28 instances, Aer statevector, corner butterfly q0

4x4 d8/d12/d16 (3/3/6 inst.), 4x5 d4/d8/d12/d16 (2/3/3/6), 5x5 d16 (2 inst., 36 min each at 25 qubits). Noise floor of a fully
scrambled echo = 2^(-n/2) (0.0039 / 0.0010 / 0.0002 for 16 / 20 / 25 qubits), confirmed by the 4x4 depth-16 bulk.

| grid | depth | mean abs v | mean abs v by Manhattan d (max over inst.) | rho(v,d) mean [min,max] | abs v at far corner per inst. |
|---|---|---|---|---|---|
| 4x4 | 8 | 0.168 | d0 .15 d2 .20 d4 .32 d6 .61 | +0.34 [-0.02,+0.59] | .48 .08 .61 |
| 4x4 | 12 | 0.025 | d0 .012 d3 .025 d4 .056 d5 .118 d6 .081 | -0.61 [-0.74,-0.45] | .081 .007 .019 |
| 4x4 | 16 | 0.0037 | flat .004-.009 at every d (= noise floor) | -0.20 [-0.59,+0.03] | .005 .001 .002 .002 .000 .002 |
| 4x5 | 4 | 0.914 | d>=3 exactly 1 (32/40 qubits never reached) | +0.66 | 1 1 |
| 4x5 | 8 | 0.362 | d0 .15 d3 .29 d4 .47 d5 .71 d6 .79 d7 1.00 (col 4 never reached) | +0.63 [+0.59,+0.70] | 1 1 1 |
| 4x5 | 12 | 0.042 | d0 .006 d3 .045 d5 .086 d6 .100 d7 .238 | -0.15 [-0.81,+0.29] | .039 .238 .065 |
| 4x5 | 16 | 0.0063 | d0-3 .002-.004, d4 .022 d5 .015 d6 .035 d7 .029 | -0.36 [-0.57,-0.14] | .004 .019 .029 .026 .006 .011 |
| 5x5 | 16 | 0.028 / 0.005 | s1: d5 .039 d6 .059 d7 .079 d8 .090; s2: d>=5 .005-.027 | -0.78 / +0.12 | .090 / .0003 |

Pooled exact value versus slack (all 28 instances, n = number of qubit values):

| slack | -1 | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | >=11 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| n | 44 | 28 | 20 | 30 | 12 | 38 | 24 | 52 | 20 | 74 | 48 | 42 | 90 |
| mean v (signed) | +1 | +.043 | -.163 | +.001 | -.097 | -.059 | -.020 | -.027 | -.013 | -.003 | .000 | -.001 | +.001 |
| mean abs v | 1 | .302 | .283 | .156 | .150 | .074 | .046 | .028 | .021 | .012 | .005 | .004 | .003 |
| frac v<0 | 0 | .46 | .80 | .57 | .75 | .76 | .62 | .79 | .55 | .50 | .40 | .48 | ~.4 |

**Verdict on (i)/(ii).** At depth 16 with a corner butterfly the vector is **(ii) scrambled everywhere that has slack >= 8**: values
are pseudo-random at the 2^(-n/2) floor with no distance structure (4x4 d16: rho(v,d) = -0.20 +- 0.3, every method at the null).
The only structure is a **rim at slack 3-7** (the last row/column to be reached) whose magnitude decays from ~0.15 (slack 3) to ~0.02
(slack 7) and whose sign is predominantly negative (62-80 %): the OTOC(2) undershoots below zero just behind the front before it
decays to noise. Depth moves the rim: d4/d8 leave whole columns at exactly +1 (slack -1) and give 0.3-0.8 at the front; d12 puts
the whole 4x5 grid inside with a rim of 0.04-0.24; d16 leaves a rim of 0.02-0.09. Grid size at fixed depth 16: 4x4 has no rim (all
slack >= 8), 4x5 has one column at slack 6, 5x5 has a row at 7 and a column at 6. The rim strength varies strongly between Haar
instances: 5x5 s1 has a clean negative rim (-0.04..-0.11, rho(v,d) = -0.78) while 5x5 s2 is nearly flat (|v| <= 0.027, mixed signs).

**Extrapolation to 6x6+2 (G4).** The 16 bulk qubits (slack >= 8; corrected from 22) are noise at ~2^(-19) ~ 2e-6: effectively zero and unreproducible by
any method. The 22 rim qubits (corrected from 16; q36, q37 at slack 3; col 5 at 4; row 5 at 5; col 4 at 6; row 4 at 7) carry |v| ~ 0.02-0.15 with a
probable negative sign; the score of any submission is decided by its shape on those 22 rows (corrected). This is consistent with native PPS giving
~0 everywhere and with MPS chi256 scoring 139 (a 2 % tail event under the null for 38 rows, so some rim structure is being tracked).

## 3. What methods score on the proxies (step 3), agreement with the exact answer, 0-1000, mean [min, max] over instances

Null (uncorrelated vector) = 1000/(n-1): 67 / 53 / 42 for n = 16 / 20 / 25 (38 rows: 27; 95th percentile 103, 99th 170).

| method | 4x4 d16 (6) | 4x5 d12 (3) | 4x5 d16 (6) | 5x5 d16 (2: strong rim / flat) |
|---|---|---|---|---|
| MPS chi8 | 36 [2,115] | 212 [53,512] | 113 [30,419] | 17 / 128 |
| MPS chi16 | 21 [1,53] | 226 [24,343] | 149 [2,391] | 1 / 5 |
| MPS chi32 | 54 [6,157] | 322 [4,625] | 172 [8,459] | 244 / 10 |
| MPS chi64 | 50 [0,192] | 286 [0,571] (2 inst.) | 227 [63,515] (4 inst.) | 433 / - |
| MPS chi128 | 57 [0,210] | - | - | - |
| MPS mean of top-2 chi | 57 | 292 | 185 | 371 / - |
| local PPS L3 eps 1e-2 | 0 (all values exactly 0) | 274 [4,770] | 0 (exactly 0) | 0 / 0 |
| local PPS L3 eps 1e-3 | 11 (max abs 0.002) | 383 [144,787] | 320 [9,638] (max abs 0.005, sparse) | - |
| local PPS L3 eps 1e-4 | 0 (200k-term limit hit, incomplete) | - | - | - |
| prior: Manhattan distance | 81 [1,343] | 249 [7,657] | 153 [18,323] | 608 / 16 |
| prior: exp(d) | 47 [0,211] | 253 [61,523] | 186 [2,383] | 407 / 12 |
| prior: -slack | 104 [0,303] | 195 [2,538] | 226 [121,372] | 479 / 4 |
| prior: sigmoid front in d, LOO within group | 82 [0,159] | 145 [15,383] | 110 [5,275] | 572 / 42 |
| **prior: signed slack-mean table, LOO** | 40 [1,118] | 81 [8,200] | **405 [232,530]** (held-out 436) | 309 / 12 |
| prior: abs slack-mean table, LOO | 44 [0,81] | 189 [16,423] | 381 [216,513] | 431 / 9 |
| combo: (1-a) z(MPS hi) + a z(signed slack), a fit on s1 | 95 (a=.4) | 114 (a=.85) | 272 (a=.7) | - |
| combo: (1-a) z(MPS hi) + a z(distance), a fit on s1 | 81 (a=1) | 269 (a=.85) | 153 (a=1) | - |
| combo: MPS hi shrunk to mean by exp(-abs(hi-lo)/s) | 54 | - | no gain (tables.md) | - |
| random Gaussian vector (null, 200 draws) | 67 | 50 | 50 | 42 / 41 |

Where the rim is absent (4x4 d16) nothing beats the null, including chi128 on 16 qubits (max Schmidt rank 256; its mean abs error 0.018
is 5x the signal) and PPS at any eps. Where unscrambled qubits exist (4x5 d8) everything works: PPS eps 1e-3 989, chi64 889, signed
slack table 773. Reading of the depth-16 columns:

- **MPS** values are O(0.2-0.6) and biased positive (chi64 mean +0.22 on 4x5 d16 where exact means are -0.02..0): the "far-row plateau"
  of the native G4 chi32 vector is this artefact. MPS tracks the rim **position** (score restricted to slack <= 6 qubits: 318 at chi32),
  with the wrong sign (rho(chi64, exact) = -0.25 on 4x5 s1). Spread is huge: chi64 63-515 across seeds.
  Cross-chi averaging, shrinkage by chi-to-chi change and MPS/prior blends never beat the better of the two ingredients on held-out seeds.
- **Local coefficient PPS** (the repo kernel `coefficient_pps.propagate`, level 3) reproduces the native G4 failure: eps 1e-2 gives
  exactly 0 on every depth-16 row; eps 1e-3 leaves a sparse vector (max abs 0.005) that is nonzero only on rim qubits, so its score is a
  lottery (9-638); eps 1e-4 exceeds the 200k-term cap before finishing. PPS is a front detector here, not an estimator.
- **Priors**: anything monotone in distance scores 150-250 on average with a 0-600 spread. The slack table (signed mean per slack from the
  other instances) is the best cheap estimator on 4x5 d16 (405, min 232 over 6 seeds, held-out 436) and on the strong-rim 5x5 (309);
  it fails on 4x5 d12 (81), where the rim sits at slack 2 whose sign is random, and on the flat 5x5 s2 (12), where nothing scores.

## 4. Predicted G4 score band (native MPS) and recommended cheap estimator

- Native MPS on 38 qubits at chi 64-256 is far less converged than chi64 on 25 qubits (the needed rank grows exponentially with the
  6-row cut), so its per-row values are artefacts; its score comes only from tracking the rim position. Proxy analogue: chi32-64 on
  4x5/5x5 gives 170-230 on average, 1-100 on weak-rim seeds, 430-515 on strong-rim seeds. Band for G4: **chi64 30-200, chi128 50-250,
  chi256 80-300** (139 observed), chi mostly changing the per-seed luck rather than the mean. A ceiling of ~400-500 applies to any
  method that only reproduces the rim shape; the per-row values of the 16 bulk rows (corrected from 22; ~2e-6) are out of reach for MPS or PPS.
- **Best cheap estimator found (geometry only, no simulation):** v_hat(q) = m(slack(q)) with the pooled signed table
  m(3) = -0.10, m(4) = -0.06, m(5) = -0.02, m(6) = -0.03, m(7) = -0.01, m(>= 8) = 0 (m(-1) = +1, m(0) = +0.04, m(1) = -0.16, m(2) = 0
  are unused in G4). For G4 rows: q36,q37 = -0.10; q5,11,17,23,29,35 = -0.06; q30-34 = -0.02; q4,10,16,22,28 = -0.03; q24-27 = -0.01;
  the other 16 rows = 0 (corrected from 22). Held-out evidence: 4x5 d16 six seeds 405 [232, 530],
  5x5 d16 309 / 12, 4x5 d8 773, 4x5 d4 909. Expected G4 score if the real rim behaves like the proxies: 200-500; if the G4 instance is
  a flat one like 5x5 s2: null (~30). It cannot do worse than the PPS zeros and is, on the proxies, better on average than MPS chi64
  (227) and than every distance prior. `summary.json["g4_prediction"]` holds the per-row values (`analyze.py` regenerates them).
- Negative results worth keeping: MPS chi-averaging, Richardson-like shrinkage and MPS+prior blends do not help; a sigmoid front in
  Manhattan distance is worse than the slack table because contact time, not distance, orders the rim (row 5 enters before col 5).

## 5. Caveats

Proxies are 16-25 qubits; the G4 rim sits at slack 3-7 where the pooled table has n = 12-52 values from mixed grids/depths; 5x5 has only
two seeds (36 min each); chi128 only on 4x4; local PPS is not the native kernel (native levels 1/2 do not collapse the echo at all).
Instance-to-instance spread (5x5 seeds 309 vs 12 for the same estimator) is the dominant uncertainty for any single G4 instance.
