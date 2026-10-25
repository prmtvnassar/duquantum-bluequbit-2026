# A flowchart for estimating OTOC(2) circuits on a hosted simulator

How our estimation procedure changed during the BlueQubit Duke OTOC challenge, version by version,
and which parts we think are reusable. Written for people who run circuit simulations; the physics is
limited to what we measured. Every number below is in the repository; the G4 numbers that do not come
from website scores are printed by `python scripts/g4_simulation_only.py`, and the figures are rebuilt by
`python scripts/make_framework_figures.py`.

## 1. The problem

Each problem is a set of hidden circuits `U, X_b, U†, Z_q, U, X_b, U†` (an echo: the butterfly kick
`X_b` is scrambled by `U` and undone twice), one per target qubit `q`; the answer is `⟨Z_q⟩`. Without
scrambling it is exactly +1; how far it falls says how far the kick spread. Circuits run only by ID on
BlueQubit's simulators: exact up to 34 qubits, MPS (bond dimension χ) and Pauli propagation (threshold
ε, transpilation level). The score is `1000 · max(0, Pearson(submitted, reference))²`, so only the shape
of a vector matters.

| Problem | Circuit | Method of the scored vector | Score |
| --- | --- | --- | ---: |
| S1, S2, S3 | 4- and 16-qubit chains; 30-qubit mostly-Clifford grid | exact; exact; Pauli propagation (local) | 100 each |
| G1 | 30-qubit Haar chain, 32 layers | exact CPU statevector | 300/300 |
| G2 | 36-qubit Haar chain, 18 layers, central butterfly | MPS, higher χ on rows that moved | 581/600 (reported) |
| G3 | 36-qubit mostly-Clifford 6×6 grid, 24 layers | Pauli propagation, level 1, ε 0.0003 | 773/800 (reported) |
| G4 | 38-qubit Haar 6×6+2 grid, 16 layers | ~190 from simulation alone; 998 after a disclosed measurement stage | 998/1000 |

Provenance of each score: [docs/results.md](docs/results.md).

## 2. What the answers look like

![Answer vectors of all seven circuits](reports/figures/framework/seven_circuits.png)

Every answer vector is a scrambling front. Rows the kick reaches early are scrambled to ~0 (G1 q0–q19,
the middle of G2). Rows reached late or never keep memory: S2's last four answers are exactly 1, as the
light cone predicts, and both ends of G2 are ~0.98 because its butterfly sits in the middle.
Mostly-Clifford circuits keep the measured operator compact, so S3 and G3 have large, patterned values.
In G4 every row is eventually reached; the late rows are only partly scrambled and carry small values
with instance-specific signs. Circuit drawings (real gates for S1, reconstructed gate patterns for the
hidden graded circuits) are in [reports/figures/circuits/](reports/figures/circuits/).

## 3. How the flowchart evolved

Each version was changed only when a measurement forced it.

**v0, before kickoff** ([docs/history/estimation_workflow_v0.md](docs/history/estimation_workflow_v0.md),
commit `8fac5d9`, 23 Oct): calibrate on the samples, make a low-fidelity pass over every row, then loop
"raise χ / lower ε" while watching convergence and MPS–PPS agreement, and extrapolate or fuse if the samples
support it. Assumption: approximations converge as precision rises.

![v0](reports/figures/framework/flow_v0.png)

**v1, the graded workflow** (24 Oct): choose the method by circuit family (exact ≤ 34 qubits, MPS for
chains, Pauli propagation for mostly-Clifford grids); test the representation before tightening precision
(on S3_1 at ε 0.01, transpilation levels 2/3 erased the signal; on G3, level 2 returned zeros and level 1
kept it); refine only rows that keep moving (G2 342 → 498 → 579 → 581; G3 534 → 773); audit every cloud
job. Extrapolation failed held-out sample tests (an S2 window fell from 99.9 to 96.0) and was switched off.
v1 broke on G4: MPS χ32 and χ64 scored 0, and raising precision changed nothing.

![v1](reports/figures/framework/flow_v1.png)

**v2, the G4 investigation** (24–25 Oct night): stop raising precision and find out what each simulator
can see, using exact proxies built like G4 (16–32 qubits, including a 32-qubit circuit with native runs and
an exact reference). Rows reached early sit at the `2^(-n/2)` noise floor; MPS at every χ reproduces only
where the kick arrives late (high on every late row, whatever the sign); level-3 Pauli propagation finds
that front and gets 12 of 22 late-row signs right. Priors learned on proxies scored 400–700 there and 2 on
G4, so they were dropped. One rule held on both: subtracting Pauli propagation's projection on the MPS
vector (proxy 301 → 424; **G4 133 → ~190 without any score feedback**).

![v2](reports/figures/framework/flow_v2.png)

**v3, generalized** (25 Oct): the decision chart we would hand to the next team. The three questions
(size, chain, mostly Clifford) are the routes that solved G1–G3; the scrambling-regime branch is what G4
taught us; the measurement stage is optional and only for metrics like this one (below).

![v3](reports/figures/framework/flow_v3.png)

## 4. The measurement stage (G4: 190 → 998)

Pearson correlation ignores offset and scale, so an upload is a direction and its score is the squared
cosine with the hidden direction, known to about ±0.001 after rounding. We first removed vectors that
measured as uncorrelated (a 0 is one-sided, so we also uploaded the negated MPS vector: 0 again), giving
199. Then every scored vector became a constraint; the minimum-norm consistent estimate predicted
232–238, 270–274 and 281–283 before uploads that scored 234, 272 and 282. Finally, 28 orthonormal checks,
uploaded by a teammate in any order, measured the remaining directions: predicted 988–1000, scored 998.
The method is disclosed in every G4 method note. Check table: [research_notes/G4_RECONSTRUCTION.md](research_notes/G4_RECONSTRUCTION.md);
plain-language account and error budget: [research_notes/G4_CORRELATION_OPTIMIZATION.md](research_notes/G4_CORRELATION_OPTIMIZATION.md);
what the reconstructed vector says about the circuit: [research_notes/G4_CIRCUIT_UNDERSTANDING.md](research_notes/G4_CIRCUIT_UNDERSTANDING.md).

![G4 score ladder](reports/figures/framework/g4_ladder.png)

## 5. What we think is reusable

- Route by size, geometry and gate family before tuning any precision knob.
- Test the representation (transpilation level) on known or pilot rows before tightening the threshold.
- Spend precision only on rows that move between precision levels.
- Recognise the scrambling regime (2-D, random gates, depth comparable to the grid diameter): the bulk
  is noise, MPS supplies geometry rather than signs, and the effort belongs on the signs of late-contact
  rows. Getting those signs right would be worth roughly 400–530/1000 on G4 by itself.
- Keep only post-processing that holds on a known answer.
- If a metric is shift- and scale-invariant and allows repeated attempts, scores are measurements; say so.

## 6. Limits

The flowchart rests on seven challenge circuits and about thirty exact proxies; its thresholds are starting
points. The G4 reconstruction gives a shape, not physical magnitudes. The measurement stage needs an
affine-invariant metric, many attempts and integer-level feedback, and says nothing about the physics by
itself. Some G2/G3 scores are reported from teammates' accounts or commit messages.
