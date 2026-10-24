# Evidence-driven OTOC workflow

**Status: `PAUSED_NO_NEW_RUNS` — October 24, 2026.** The user has stopped quantum
execution. Use saved records for analysis and writing; this document authorizes no
simulation, quote, retry or submission. Any future execution requires the user to
resume it. This is a new decision procedure synthesized from the campaign, not a
claim that every earlier experiment followed it. It develops the pre-challenge
v0 framework, preserved in `8fac5d9:estimation_workflow_v0.md` on October 23,
23:09 EDT (document dated October 22). That proposal already included precision
trends, vector shape, transpilation sensitivity, adaptive allocation, and
conditional extrapolation/fusion. The empirical contribution is the revision of
those ideas into evidence-based decisions, not a claim that these concepts first
appeared after the results. The account-specific outcomes
are maintained in [results.md](results.md); the supporting causal history is in
[optimization-decisions.md](optimization-decisions.md).

Commit `e0ca909` later adds [G2_23_512_and_13_128.csv](../submissions/candidates/G2/G2_23_512_and_13_128.csv) with the message "G2 with 580/600". This is the highest repository-reported G2 score. Comparing saved vectors shows 23 values unchanged from the 579 file and 13 changed. The filename claims a chi512/chi128 mix; source jobs, submitting account, attempt, penalty and website verification remain unavailable. The [feedback record](../submissions/candidates/G2/G2_23_512_and_13_128.feedback.json) preserves these limits. The two reports do not establish a controlled one-point improvement.

## 1. Reuse evidence before proposing computation

Start with complete vectors, per-row native options, job receipts, costs and
attributed submission records. Keep original-account and teammate outcomes
separate. A newer report can correct attribution without changing the older
receipt. In particular, Kevin's G2 498/600 belongs to his MPS chi128 file; the
older attribution of that score to the original chi32 file is disputed. A newer
mixed-precision G2 CSV is user-confirmed as submitted. A later repository
[score note](../submissions/candidates/G2/G2_23_512_and_13_64.score-report.txt)
claims **579/600**, an earlier mixed-precision result; its submitting account,
official attempt and time penalty remain unknown, and no website receipt was
preserved. The note describes 23 GPU MPS chi512 rows and 13 chi64 rows, but no
row-to-job mapping or service receipts accompany it. Kevin's **498/600** remains
the highest G2 result with an account-attributed scored submission receipt. Scores,
prepared exports and terminal job results are distinct evidence types.
[Hybrid submission record](../submissions/candidates/G2/G2_23_512_and_13_64.feedback.json).
[Kevin's imported records](../submissions/teammates/kevin/README.md) were added in
commit `2a3eb2b`; the [submission registry](../src/otoc/submission_registry.py)
defines the local evidence fields.

| Problem | Starting point for any resumed decision |
| --- | --- |
| G1 | Reuse the verified 30-row exact vector. Do not repeat its simulations. |
| G2 | Preserve the original chi32 vector, Kevin's distinct chi128 vector and the newer submitted hybrid. Confirm the hybrids' reported 579/600 and 580/600 with the account and website receipt, and obtain its row provenance before treating it as a verified improvement. |
| G3 | Reuse Kevin's complete level-1 PPS epsilon 0.0003 vector and its reported 773/800 outcome. The original-account epsilon 0.001 candidate and later 0.0005 work remain separate records; they do not justify duplicating an available finer vector. |
| G4 | Preserve the zero-scoring chi32 artifact and the four chi64 diagnostics. Neither a full chi64 cohort nor another submission is presently justified by those diagnostics. |

Check the original account's runtime state and unresolved commitments before any
future execution. A paused process or cancellation request is not proof of a
terminal job or settled charge. Never substitute a teammate's state root to
resolve an original-account ambiguity. The stopped G3 continuation has nine of
36 completed rows, two canceled owned jobs and no active owned jobs; it is not a
submission-ready vector. [Stop snapshot](../reports/audit/campaign-stop.json),
[execution/recovery contract](COHORT_BATCH.md).

## 2. Use calibration to choose a method, then test the native representation

Prefer exact simulation when feasible and already available. For approximations,
use public samples or explicit proxy circuits with known answers to form a prior:
MPS for the Haar chains, PPS for the mostly-Clifford grid. The zero-cost sample
study selected local S1 MPS chi8, S2 MPS chi128 and S3 coefficient-cutoff PPS
epsilon 0.001. These are calibration results, not native settings with certified
accuracy on larger hidden circuits; G4 has no matched sample family.
[Calibration evidence](../reports/calibration_evidence.json).

Treat representation as a separate choice from precision. Native PPS level 2
returned zeros in the recorded S3/G3 tests, whereas levels 0/1 recovered nonzero
sample estimates. This justified level 1 before spending effort tightening its
threshold. It does not establish that level 1 is universally superior or that the
suggested internal transpilation mechanism has been verified.
[Recorded diagnostic and interpretation](../submissions/teammates/kevin/README.md);
`kevin/experiment` commits `e6707fa`, `8d85f21`.

## 3. Choose the cheapest test that could change a decision

Write the decision and its possible branches before a new experiment: complete a
coherent vector, change representation, test higher precision, or stop allocating
resources. First ask whether a cached comparison already answers it. Do not impose
a pilot quota, run every threshold, or demand another precision level indefinitely.

Choose rows for complementary information: G2 transition rows check a region
missed by saturated endpoints; G4 residual influence, sign reversals and separated
interior rows exposed different precision behavior. One fast row establishes that
row's feasibility, not whole-vector runtime. A large increment shows sensitivity,
not improvement; a shrinking increment is not an error estimate. Broaden a panel
only when the extra observation could change allocation.
[G2/G3 allocation review](../reports/next_allocation_review.md),
[G4 subset analysis](../reports/G4_PARTIAL_TREND_REVIEW.md).

Predeclare what observation would change the next choice. A saturated-endpoint
panel calls for transition or interior rows; an all-zero PPS vector calls for a
native-level comparison before a smaller threshold; a direction reversal calls
for wider coverage; an expensive quote calls for a resource stop even if the
numerical question remains open. These branches avoid retrofitting a stopping
rule to the outcome. [Decision history](optimization-decisions.md).

Compare alternatives at the unit the contest actually grades: a **complete
submitted vector** and its returned score and time penalty on the *same account*.
Until both outcomes and the exact penalty rule are known, keep score gain, elapsed
time and billed cost as separate columns. A row's precision change cannot be
converted into expected points, and a favorable quote cannot be converted into
an elapsed-time guarantee. Prioritize decisions with a plausible score effect
and a low marginal time or dollar commitment; stop when no remaining experiment
could plausibly change the chosen complete candidate before the deadline.

## 4. Review precision, shape and independent evidence together

Stage the review so that each calculation answers a distinct question:

1. **Within-method sensitivity:** match IDs, device and all options except the
   precision being varied. For MPS, inspect the signed steps across bond dimensions
   at each row; for PPS, inspect them across coefficient thresholds at a *fixed*
   transpilation level. Retain absolute steps, reversals, zero counts and
   contraction or growth. Compare steps with the centered signal scale instead
   of dividing by a nearly zero row value. A small last step is only observed
   stability, while a large one is sensitivity. PPS thresholds need not improve
   error monotonically; changing its native level starts a new representation
   comparison.
2. **Vector shape:** when aligned coverage is sufficient, center vectors `x,y`,
   retain signed Pearson correlation, fit `a = (x dot y)/(x dot x)`, and inspect
   `y - a*x`, order reversals and centered signal scale. For nondegenerate vectors,
   normalized residual energy equals `1 - rho^2`; a negative slope still matters.
   Two nonconstant points always correlate at +1 or -1. Sparse or nearly constant
   panels cannot validate the full profile.
3. **Independent corroboration:** align MPS and PPS values by observable and
   compute both `max_q |MPS_q - PPS_q|` and an RMS difference scaled by the
   *vector's* centered RMS. Inspect signs, zero rows and high-influence rows too.
   Predeclare any pointwise tolerance using known-answer samples of the same
   family; never tune it from an unknown graded score. Agreement becomes more
   persuasive when both methods are separately stable under precision changes.
   Matching zeros or approximate methods can share bias. Disagreement identifies
   uncertainty, not which result is true.

The positive-Pearson scoring rule makes shape useful, but common offsets and
positive scaling can preserve a score despite pointwise error. Pointwise
MPS–PPS agreement alone is therefore neither a necessary condition for a good
score nor a sufficient accuracy certificate. A complete, valid vector with a
stable *full-profile* shape may be a defensible provisional candidate; otherwise
stop only with an explicit uncertainty or resource reason. Neither these
diagnostics nor sample tolerances supply a universal hidden-error certificate.
Automatic graded convergence stopping remains disabled.
[Numerical implementation](../src/otoc/campaign_reasoning.py),
[retained scoring rules](history/workflow_v1.md),
[sample stopping limitations](../reports/calibration_evidence.json).

## 5. Route hardware toward useful precision

Use GPU only when measured or defensibly quoted time, cost and quotas make a useful
precision attainable. A fixed-setting CPU/GPU match tests consistency and speed;
it does not add mathematical precision. The G4 q0 chi32 GPU trial saved only
10.25 seconds elapsed for $0.20 extra. CPU chi64 subsequently fitted its diagnostic
caps, so the same-chi GPU timing repeat was deferred. The paper's larger speedups
are workload-specific hypotheses for further testing.
[Matched trial](../reports/gpu_matched_pilot.json),
[paper synthesis](../research_notes/GPU%20precision%20recovery/paper_methods.md).

The submitted G2 hybrid records a choice of 23 claimed GPU MPS chi512 rows and 13
chi64 rows. Its repository note reports **579/600**, higher than Kevin's separate
498/600 receipt. Without account attribution, website feedback, per-row receipts,
time costs and a same-account baseline, that comparison does not establish that
the precision mix improved the score or resource efficiency. Treat row-specific
precision as a *conditional* future strategy. A mixed vector needs a row-level
manifest, complete ID coverage, exact source values, device and precision for
each row, and a reproducible assembly script. The current exporter enforces one
device and full option set per cohort, so it does not validate such an assembly.
Compare any future hybrid with a coherent baseline using attributed, complete
score and penalty evidence.

For a future audited hybrid, allocate expensive precision where a matched pilot
shows a material change in the *centered profile* after removing common offset
and positive scale, and where the row's runtime is tractable. This is a
value-of-information ranking, not an expected score gain: a changed row may move
the estimate toward or away from hidden truth, and piecing together precisions
can create shape artifacts. Recompute whole-vector shape after each assembled
candidate; use public known-answer samples to check the selection heuristic.

If execution resumes, the operational gates remain separate from numerical
judgment: fresh exact-action quotes; known charges plus outstanding/new quote
commitments; the $27 planning ceiling within $30; applicable elapsed cancellation
thresholds; job/deadline limits; known total and rolling GPU usage; and one execution
owner. A quote is not a measured runtime or hard billing cap. Prior $0 charges do
not make the next run free. The current detailed limits and controller capabilities
are in [COHORT_BATCH.md](COHORT_BATCH.md) and
[workflow_final.json](../configs/workflow_final.json).

Local Qiskit, OBP, Julia and Quantum Rings alternatives require gates or QASM that
the hidden IDs do not expose. Hardware hybrids remain a future conditional design;
they have not been implemented or validated as a campaign candidate policy.

## 6. Make the stop reason and candidate status explicit

Record whether work stops because of user instruction, resource limits,
uninformative evidence, a sufficient provisional submission case, or numerical
convergence evidence. These are different conclusions. A finite budget may force a
choice among uncertain complete vectors; endless diagnostics cannot certify
unknown truth either.

Validate full ID coverage, finite raw values, the intended observable and row-level
provenance before numerical review. The current exporter requires identical full
options and one device per cohort and does not splice pilot rows. This is an
implementation policy, not an asserted event rule. Its `submission_eligible`
compatibility field means format and resolved signal only; approximate exports
still require review. A highest-completed-precision selection is not proof of best
accuracy. [Exporter](../src/otoc/graded.py), [retained submissions](../submissions/README.md).

Preserve direct estimates: the tested extrapolator failed held-out checks and
fusion showed no held-out gain. Do not infer row values from whole-problem scores.
If a resumed campaign recommends a genuine complete candidate, state its remaining
uncertainty, retain the actual upload bytes and record the returned score under the
correct account. An earlier fallback does not reduce the time penalty attached to
a later best result. [Extrapolation rejection](../reports/extrapolation_rejection.json),
[fusion evaluation](../reports/calibration_evidence.json), [results ledger](results.md).
