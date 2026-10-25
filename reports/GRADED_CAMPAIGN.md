# Graded campaign evidence, October 24, 2026

The active decisions are to preserve the exact G1 anchor, complete CPU MPS chi32
cohorts for G2/G4, and complete native CPU Pauli-path threshold 0.001 at
transpilation level 1 for G3. These are provisional direct estimates. Native
precision sensitivity is unresolved, and no hidden-circuit accuracy guarantee
follows from the current pilots. The operational policy is
[../docs/history/workflow_final_graded.md](../docs/history/workflow_final_graded.md).

The user confirmed G1 submission, recorded separately in
`submissions/G1/user-reported-submission.json`. A teammate's reported G1 score is not
an independently observed score from this campaign. Browser site access remains
blocked. G2-G4 generated CSVs are candidates, with official upload status and
scores unverified. Compute continues through the previously authorized SDK;
export never implies submission.

## Evidence supporting the selected cohorts

| Problem | Relevant native evidence | Decision and limit |
| --- | --- | --- |
| G2 | PPS 0.001 at level 2 gave zero pilots. At q0, PPS 0.0001 gave 0.045095738448185416 while MPS chi16 gave 0.9996910502231614. At q18, MPS changed from about -0.061984 at chi16 to 0.007424 at chi32. | Prefer the sample-informed MPS family and the complete chi32 CPU pilot cohort. The sign change demonstrates sensitivity; it does not estimate error against truth. |
| G3 | PPS 0.001 level 2 gave `[0, 0, 0]` at q0/14/35; native level 1 gave approximately `[-0.072292, 0, -0.032198]`. MPS q0 changed from about 0.026914 at chi16 to 0.647503 at chi32. | Prefer PPS at native level 1 and threshold 0.001. Representation changes matter, and the direction disagrees with MPS. Neither nonconstant result is ground truth. |
| G4 | PPS 0.001 level 2 gave zero at q0/19/37. MPS q0 changed from 0.5589102913779098 at chi16 to 0.27027187138182995 at chi32; a complete chi32 CPU pilot cohort is available. | Complete the CPU chi32 vector while preserving earlier direct results. There is no matched Haar-grid sample; chi32 remains uncertified. |

G3 q0 at level 1 threshold 0.0003 completed at approximately -0.1477496, materially
different from -0.072292 at 0.001. The corresponding tighter q35 check reached
its 180-second diagnostic cap and was canceled with $0 terminal cost. The tighter
pilot cohort is incomplete. It supplies sensitivity evidence, not full-vector
shape convergence, and its q0 must not replace an isolated coarse-cohort row.

G2 q0 PPS 0.0001 took 196.694 seconds of compute and about 243 seconds elapsed.
Its subsequent 0.00001 check was canceled to prioritize coverage and has a $0
terminal receipt. These examples show why elapsed time and cancellation costs
must be recorded separately from compute time and quotes.

The original PPS/chi16 configuration entries capture affordable starting priors.
The effective policy is recovered from complete, fixed-configuration pilots,
with original-family preference followed by precision and deterministic device
selection. The current selected full options are also recorded in
[../configs/cohorts/baseline_reserves.json](../configs/cohorts/baseline_reserves.json).
Discovery is disabled after the bounded diagnostic tranche so that completion
has priority over repeated sparse exploration.

## Matched GPU result

One matched G4 q0 chi32 comparison is available in
[gpu_matched_pilot.json](gpu_matched_pilot.json):

| Measurement | CPU MPS | GPU MPS |
| --- | ---: | ---: |
| Direct value | 0.27027187138182995 | 0.2702718713884605 |
| Compute seconds | 48.593 | 24.189 |
| Queue seconds | 1.421 | 19.149 |
| Elapsed seconds | 55.055394 | 44.803906 |
| Actual cost | $0.00 | $0.20 |

The absolute value difference is 6.63e-12. GPU halved compute time in this trial
but saved only 10.25 seconds elapsed and incurred the $0.20 charge. CPU remains
the baseline route. GPU is still an option for a supported, necessary refinement
when its fresh quote and time benefit justify it. One trial is not a statistical
benchmark, and zero billing on these CPU receipts does not imply future free
compute. Current aggregate spending must be read from reconciled account state,
not inferred from this table.

## Why both trends and score shape are retained

Shape stability and pointwise accuracy are different properties. A sign
reversal is consequential.

[src/otoc/campaign_reasoning.py](../src/otoc/campaign_reasoning.py) compares only
complete precision vectors at a fixed device and PPS representation. After
centering, it projects the newer vector onto the older and ranks squared
residual components relative to the newer vector's centered energy. The total
relative residual equals `1 - rho^2`. It also records `1 - rho` and flags negative
affine slope, so a sign reversal is not mistaken for harmless rescaling. These
row weights measure where refinement changed shape; they do not estimate hidden
error, official score gain or the value of another run. Constant or nearly
constant vectors cannot support this normalized comparison.

[src/otoc/adaptive.py](../src/otoc/adaptive.py) separately records within-method
signed changes, slopes per log precision, oscillation, contraction and flat
segments. Oscillation and growth increase scheduling priority. A contracting
history can yield a geometric tail proxy; flat histories are `FLAT_UNVERIFIED`.
Low-chi MPS on S3 can remain near zero when the exact value is near -0.5, and
native PPS zero plateaus can break under precision or representation changes.
Cross-method agreement can share bias. Consequently none of these diagnostics
is a certified error bound, and automatic native convergence stopping is disabled.

Scheduling uses the greater of the quote and the observed upper-quartile elapsed
time for that problem/device. This is an empirical floor, not a runtime guarantee.
Cost plus elapsed-time weighting and shape sensitivity form a transparent
priority heuristic; their superiority over a fixed allocation has not been
established by an equal-budget trial.

The sample submissions each display 100/100, but that rounded display does not
bound pointwise errors. Local reference comparisons are separate evidence, and
local MPS/PPS implementations are not interchangeable with the native kernels.
Transfer to native MPS/PPS was not tested on samples because those paid jobs
would violate the $0 sample-spend requirement. Free exact CPU reference jobs
remain distinct evidence. G4 has no matched sample family.

## Selection, resources and audit

[../src/otoc/coherent_selection.py](../src/otoc/coherent_selection.py) groups by
actual device and every option. It selects complete exact cohorts first, then
complete eligible primary-family precision, then a complete fallback. A partial
higher-precision cohort cannot replace individual rows in an earlier complete
one. The first complete baseline and all complete alternatives are preserved.
Near-constant exports are marked for signal review, not treated as eligible
submitted answers. Raw direct values are used throughout.

Extrapolation and fusion remain disabled. The specific geometric/Aitken candidate
in [extrapolation_rejection.json](extrapolation_rejection.json) failed held-out
precision tests; one S2 window reduced the exact-reference score from 99.86264
to 95.99984. The available sample LOCO fusion tests showed no gain. These findings reject those proposed transformations under
the current evidence, not every possible future estimator.

The unchanged total graded budget is $30. The current cushion is 10% ($3), so
planned exposure is limited to $27. Selected-cohort per-row reserves are at least
$0.30 for G2, $0.20 for G3 and $0.27 for G4, increased by matching quote evidence.
Chi32 jobs have a 900-second cap; ordinary remote jobs retain 600 seconds. A
20-minute submission buffer and the configured account/GPU limits still apply.
Quotes are nonbinding, and unknown costs block new launches.

The serial executor remains configured for one active job. The separate
[CPU cohort controller](../docs/COHORT_BATCH.md) can own at most two CPU
jobs under the same exclusive `remote_runner` lock after release checks and a
clean handoff. Its admission calculation includes actual charges, outstanding
quoted commitments and missing selected-baseline reserves. A complete usable
older baseline exempts only future coverage of that problem's refinement cohort;
active and newly launched refinements still reserve their quotes. Foreign jobs,
ambiguous submission intents and unknown terminal costs block new launches.

Every attempt is checkpointed before submission in `results/workflow/remote_actions`
and mirrored through the canonical adapter audit into `runs/records` and the run
ledger. Quotes and decisions are retained in `runs/events`. Cancellation remains
a committed action until terminal cost is reconciled. Method explanations and
per-ID manifests accompany complete candidate CSVs. Official submission facts
are recorded only after an upload is confirmed.
