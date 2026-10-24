# Adversarial review of graded estimation

Date: October 24, 2026. Two GPT-6 Astra reviewers using Ultra reasoning examined
the scheduler and sample transfer independently, then challenged the revised
implementation. Their review used saved data; only the root executor submitted
the recorded native diagnostic jobs.

## Claims rejected by the review

**Nonconstant pilots establish accuracy.** Rejected. Native G3 MPS chi16 has
pilot values approximately [0.02691, 0, 0]. On the related S3 sample, some MPS
chi8 and chi16 estimates both remain near zero despite exact values near -0.5.
The partial S3 chi16 maximum error is about 0.6535. Signal recovery is useful
for a provisional baseline, but cannot support a near-perfect score claim.

**A smaller cross-method gap alone justifies stopping.** Rejected. G2 q18
changes sign between MPS chi16 (-0.061984) and chi32 (0.007424). G4 q0 changes
from 0.558910 to 0.270272. G3 q0 changes from 0.026914 to 0.647503. The observed
steps demonstrate material precision sensitivity, not an error bound.

**PPS's zero result is representation independent.** Rejected by native jobs:
G3 epsilon 0.001 level 2 gives [0,0,0] at q0/14/35, while level 1 gives
[-0.072292,0,-0.032198]. Level1 does not thereby become ground truth. Its pilot
direction conflicts with MPS. Native transpilation levels and local Qiskit
optimization levels are not asserted equivalent.

**Extrapolation is necessarily better than direct simulation.** Rejected for
the specific conservative geometric/Aitken candidate tested in
[extrapolation_rejection.json](extrapolation_rejection.json). Two held-out S2
precision windows predict the next level worse than the last direct estimate.
The latter extrapolated vector drops exact-reference correlation score from
99.86264 to 95.99984. This does not reject every possible extrapolation model.

**Blending zero PPS with MPS can improve Pearson scoring.** A common positive
blend weight only rescales MPS, leaving correlation unchanged. Existing sample
LOCO fusion gives no gain, so no such variants are submitted.

## Implemented consequences

- Export only complete vectors with one device and identical full options.
  Partial higher-precision values never replace isolated rows in an older
  complete vector. Preserve all complete candidates and missing-ID diagnostics.
- Coverage counts missing rows of the selected configuration, rather than any
  result from any method. Keep the chosen route consistent while filling it.
- Keep bounded native representation and chi32 probes available after a
  temporary primary-method switch. No unbounded level enumeration.
- Keep precision histories separate by device and PPS transpilation level.
- Permit chi32 CPU jobs under a deliberate 900-second cap, including completion
  jobs. Conservative quotes still gate dollars and deadline; actual runtime
  observations never imply future free billing.
- Pilot recovery preserves the actual selected device and every option. CPU
  and GPU cannot jointly masquerade as one complete pilot configuration.
- Use affine-residual shape diagnostics only as sensitivity rankings. Their
  total equals 1-rho^2 between estimates, not error against unknown truth.

## Tradeoff and next evidence

Completing a cheap baseline early has value. Exploration has value only while
it can change a feasible method choice. The blanket 101-row MPS16 batch was
stopped cleanly after seven additional G4 rows; completed work remains cached.
The bounded next tranche completes chi32 pilot cohorts for G2/G4 and tests a
tighter level 1 threshold plus one level0 comparison on G3. After that tranche,
choose a coherent baseline instead of repeatedly exploring configurations.

The user confirmed G1 was submitted. No G1 simulations are repeated. Native
transfer therefore remains unvalidated against G1's exact labels. No new
graded score has been observed: browser access is still blocked, and neither
reviewer has certified 100% accuracy from these diagnostic comparisons.

## Agreed provisional baseline plan

The final debate distinguishes scientific family preference from initial
affordability choices: MPS for G2, PPS for G3, incumbent MPS for unmatched G4.
Complete native chi32 pilot cohorts support selecting that precision for G2
and G4. Select G3 level 1 at 0.0003 if bounded tighter probes complete usefully;
otherwise level 1 at 0.001 remains the available provisional choice. Stop broad
discovery after this tranche and complete actual coherent vectors. Further
decisions require full-vector or genuine score evidence.

The selected chi32 quote reserves are $0.30 per G2 row and$0.27 per G4 row,
with $0.20 per G3 row. The internal cushion is reduced from $4.50 to $3 to admit
these coherent baseline commitments inside the user's unchanged $30 budget.
Known billing so far is zero; this is not a promise of future free compute.
One matched G4 chi32 GPU probe is authorized to test whether its speed benefit
justifies a route change. CPU and GPU cohorts remain separate.

G3 q0 at level 1 epsilon 0.0003 completed at -0.1477496, materially different
from -0.072292 at 0.001. The corresponding q35 tighter probe reached its
180-second diagnostic cap and was canceled with zero cost. The tighter pilot
cohort is therefore incomplete: do not claim shape convergence or substitute
its q0 into the coarse vector. The initial G3 baseline remains level 1 at 0.001.

Matched GPU pilot: G4 q0 chi32 agreed with CPU within6.7e-12; compute24.189s vs48.593s, elapsed44.804s vs55.055s. GPU billed$0.20, CPU$0. CPU remains the baseline route. Full receipt comparison is in gpu_matched_pilot.json.
