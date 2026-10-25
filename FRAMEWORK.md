# A practical framework for estimating OTOC(2) values on a hosted simulator

This document describes the estimation framework we ended up with for the BlueQubit Duke OTOC
challenge, how it grew out of the one we designed before the event, and which parts we think are
reusable. It is written for people who run quantum-circuit simulations, not for theorists; the
physics is kept to what we actually observed.

## 1. The problem

Each graded problem is a set of hidden circuits of the form `U, X_b, U†, Z_q, U, X_b, U†` (an echo:
a butterfly operator `X_b` is scrambled by `U`, a check `Z_q` is inserted, and the circuit is run
back and forth again), one circuit per target qubit `q`, and the task is the final `⟨Z_q⟩` for each.
The circuits can only be run by ID on BlueQubit's simulators (statevector up to 34 qubits, MPS with
a bond-dimension knob, Pauli propagation with a truncation-threshold knob). The website scores a
submitted vector by `1000 · max(0, Pearson(submitted, reference))²`.

Scores reached: samples S1–S3 100/100 each; G1 300/300 (exact statevector, 30 qubits); G2 581/600
(MPS, 36-qubit chain); G3 773/800 (Pauli propagation, 36-qubit grid); G4 998/1000 (38-qubit Haar grid,
see Section 4). Per-problem evidence is in [docs/results.md](docs/results.md).

## 2. What we started with

Before the event we built an evidence-driven workflow (now in `docs/history/`):

- **Calibrate on the samples**, where exact answers exist, before touching graded circuits.
- **Treat every cloud job as a quoted, audited action**: fresh quote, budget gate, receipt, ledger
  (`runs/`). One controller at a time; no silent retries.
- **Keep cohorts coherent**: one device and identical options for all rows of a submission, so a
  vector is reproducible from its method note.
- **Watch precision sensitivity**, not agreement: two approximations agreeing can share a bias.

This worked for G1 (exact), G2 (MPS on a 1D chain) and G3 (Pauli propagation on a mostly-Clifford
grid). It stalled on G4: a 38-qubit Haar-random grid at depth 16 where a complete MPS vector scored 0
and the best Pauli-propagation vector scored 133. The rest of this document is about what we learned
there and what changed in the framework as a result.

## 3. What G4 taught us about the two simulators

All of this is measured on G4 itself or on exact proxies we built (smaller grids with the same
circuit construction, 16–32 qubits, exact answers computed locally or on the 34-qubit statevector
backend). Details: [research_notes/G4_CIRCUIT_UNDERSTANDING.md](research_notes/G4_CIRCUIT_UNDERSTANDING.md).

1. **At depth 16 most rows carry no signal.** Where the scrambled butterfly reaches a qubit early,
   the exact `⟨Z_q⟩` sits at the `2^(-n/2)` noise floor. Only the "rim" — qubits the butterfly reaches
   in the last few layers (16 of 38 rows here are bulk, 22 are rim) — has values of order 0.03–0.15.
   Which rows are rim is a geometry question; what sign each takes is instance-specific.
2. **MPS reads the geometry, not the values.** A truncated MPS loses entanglement, so the echo returns
   too well: every late-contact row reads +0.8…+0.97 regardless of its true sign. The resulting vector
   is a contact map (correlation 0.86 with the measured contact order) and has zero correlation with
   the reference at every bond dimension we tried (32 to 256). Raising χ does not fix this.
3. **Pauli propagation is a front detector.** Coefficient truncation removes the whole operator on
   early-contact rows (those read exactly 0, which is correct) and keeps a few per cent of it on the
   rim. At the finest threshold the service allows for 38 qubits it got 12 of 22 rim signs right and
   10 wrong — including the two rows where its own values were largest. It is the only direct method
   that carried any signal (133/1000), and finer thresholds help on known-answer proxies.
4. **Priors transfer poorly across instances.** A geometry prior built from exact proxies scored
   between 400 and 700 on held-out proxies and 2/1000 on the real G4, because the real instance's rim
   has mixed signs. Averaging across χ, extrapolating in χ or in threshold, and MPS-feature
   corrections never beat the best single input on labelled data.

## 4. What changed in the framework

The useful change is to treat the score itself as a measurement and to be explicit about what each
step can and cannot know.

- **Measure, don't assume (new).** Pearson is blind to offset and scale, so a submitted vector is a
  direction; its score is the cosine with the reference direction, known to about ±0.001 after
  rounding. Every upload is one scalar measurement. We logged each one with its exact file and note.
- **Project out directions that measured ≈ 0 (new).** If a whole vector scores ~0 in both signs, it is
  orthogonal to the reference; regressing it out of a signal vector removes variance without removing
  signal. This took G4 from 133 to 199 (predicted 202). Two cautions came with it: a score of 0 is
  one-sided — the vector may be anti-correlated rather than null (on a known-answer proxy the MPS vector
  scored 0 by clipping while being anti-correlated at ρ ≈ −0.5, and on G4 we checked by uploading the
  negated MPS vector, which also scored 0); and only *measured* null directions qualify — a merely
  plausible one (the geometry prior on the proxy) cost points.
- **Fit within the span of scored vectors and check by leave-one-out (new).** With several scored
  vectors, their scores pin the reference's coordinates in their span; the minimum-norm consistent
  point is a safe estimate whose length is a lower bound on the achievable correlation. We only trusted
  it because leaving each score out and predicting it reproduced every known score within 3 points,
  and because it predicted the next upload's score before each upload (234, 272, 282 came in as
  predicted).
- **Add information with designed checks (new).** When the span was exhausted, each further upload was
  the current estimate plus a small multiple of a direction orthogonal to everything measured; its
  score measured one new coordinate. A batch of 28 orthonormal checks, uploaded by a teammate in any
  order, pinned the remaining coordinates; the final fit scored 998 (predicted 988–1000). Scaled
  exact proxies and the local Pauli-propagation ladder were used to decide *where* checks mattered,
  not to fill values. Plain-language account and error budget:
  [research_notes/G4_CORRELATION_OPTIMIZATION.md](research_notes/G4_CORRELATION_OPTIMIZATION.md).
- **Keep the audited job workflow (unchanged).** Quotes, receipts, ledgers and coherent cohorts
  carried over; we added observable lists (all 38 `⟨Z_j⟩` from one MPS job at no extra cost), a
  sample-calibration override, relaunch after a $0 cancel, and a GPU quota gate based on observed
  runtimes.

## 5. What we think is reusable

Stated carefully, because much of it rests on one competition's circuits:

- For OTOC(2) echo circuits at depth comparable to the system size, spend simulation effort on the
  late-contact rows and on their signs; the bulk is noise and MPS cannot supply signs.
- Measure the contact geometry on the circuit itself (an all-`Z` MPS job per row gives it for the
  price of one row) rather than assuming a layer order.
- When a competition metric is affine-invariant and allows repeated attempts, whole-vector scores are
  measurements; a disclosed, non-adaptive check design reaches the metric's rounding limit in about as
  many uploads as the vector has degrees of freedom. This is a property of the metric, not of the
  physics, and it says nothing about the absolute values.
- Validate every estimator on a known answer first, and prefer a lower bound you can check to an
  estimate you cannot.

## 6. Limits

Scale and offset of the G4 reference are not observable from the score, so the reconstructed vector
is a shape; the per-row values quoted in our notes are anchored by assumption (bulk ≈ 0) and bracketed,
not measured. The physics statements are drawn from one 38-qubit instance and a few dozen smaller
exact proxies. The check method requires an affine-invariant metric, many attempts, and integer-level
score feedback; it is disclosed in every method note we uploaded.
