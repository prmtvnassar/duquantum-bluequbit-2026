# Next allocation review — proposal, not new simulation results

Dated 2026-10-24. Read-only review of saved CSVs and native receipts. The active G3 epsilon 0.0005 panel was not read when defining the decision rules below. This review launched no simulations or API requests; this report is its only file change. Numerical flags below are operational allocation choices, not validated hidden-error bounds or expected-score predictions.

## Smallest useful G2 panel

Use **q9, q31 and q18 at CPU MPS chi64**, staged rather than committed to a full vector: start q9/q31 in the two CPU slots, then admit q18 if the first results remain tractable and fresh quotes fit the budget. Preserve the existing 600-second cancellation-request and 2400-second quote-runtime limits. Reconcile failed or canceled jobs before any fallback.

| ID | Saved chi16 | Saved chi32 | Chi32 compute seconds | Reason |
| --- | ---: | ---: | ---: | --- |
| q9 | unavailable | 0.4944418435 | 5.895 | Unsaturated left transition; cheapest proposed feasibility check. |
| q31 | unavailable | 0.5516904172 | 14.268 | Opposite transition with similar coarse amplitude; tests whether the two sides change differently. |
| q18 | -0.0619839420 | 0.0074239175 | 37.777 | Known precision sensitivity; adds the low middle and a slower runtime case. |

One q9 run suffices to test **that row's** feasibility. It is insufficient to project the full-vector runtime or recommend refinement from numerical evidence: its chi32 run was unusually fast, while many retained rows took 30–38 seconds. Two transition rows improve coverage; q18 adds a third precision history and materially different amplitude/runtime. This three-row window is the smallest panel recommended before a full-cohort allocation decision. Do not expand it automatically to more pilots.

q31 is slightly cheaper than q30 (14.268 versus 16.256 seconds), with nearly the same saved value. q12 is a credible cheap alternative near the abrupt left transition (0.00406733, 6.239 seconds), but q18 supplies an actual chi16/32 history and guards against extrapolating runtime from only fast IDs. These are measured timing comparisons, not guaranteed higher-chi rankings.

Do not call q9 a high-influence row on centered signal energy: it contributes only 0.113% of the baseline's centered energy. Its value is transition coverage. The old q0/q18/q35 panel was dominated by saturated endpoints and yielded misleadingly impressive approximation-to-approximation correlation. Avoid another endpoint-heavy panel and never use three-point correlation as a hidden-score estimate.

After this window, make a feasibility/prior-based choice between one coherent chi64 vector and reallocating effort. A large step need not be an improvement; a small step need not be accurate. S2's direct precision sweep supports trying chi64, without a universal requirement for another chi128 pilot. The original-account G2 result is 342/600; the same-byte teammate result of 498/600 remains unexplained and must not calibrate pointwise corrections.

## Predefined G3 decision at panel termination

Use only completed, same-device, same-options q19/q34/q14 comparisons between epsilon 0.001 and 0.0005 at native level 1. Resolve terminal status and recorded costs. Do not substitute partial values into the existing CSV.

The coarse full vector has centered RMS 0.03387064 and nine zero rows. q19/q34 account for 52.44% of centered energy; q14 tests persistence of an apparent zero. For the three-point panel, report raw changes, ordering, and the least-squares relation `fine = a + b * coarse`, including maximum absolute residual. Three points leave only one residual degree of freedom, so this is a limited screen.

Predeclare a **shape-change flag** when the fitted slope is nonpositive, an ordering reverses for a pair separated by more than 0.02 in the coarse vector, or maximum absolute affine residual exceeds 0.01. The 0.01 flag reuses the sample study's engineering tolerance; it is not a certified graded threshold. Changes comparable to the full vector's 0.03387 RMS are material context. A common positive scale or offset alone does not damage Pearson correlation and does not automatically disqualify the coarse candidate.

1. **All three complete; no shape-change flag:** recommend the existing complete epsilon 0.001 vector promptly as a genuine, provisional first G3 submission. Disclose the remaining q0 threshold sensitivity. Do not require another precision level or independent MPS agreement before this first attempt.
2. **Shape change appears and the finer route is tractable:** allocate one bounded continuation to a complete epsilon 0.0005 vector, reusing its finished rows. Use an explicit approximately 60-minute completion allocation after this decision, with fresh quote protection; treat pilot runtime projections as estimates. Review the full vector once and recommend the genuine complete finer candidate if provenance, signal and validity checks pass. No automatic third threshold or growing pilot list.
3. **The panel or continuation becomes impractical/incomplete:** recommend the existing complete epsilon 0.001 vector as fallback, with numerical uncertainty stated. Keep completed finer rows as evidence. Indefinite hold does not establish accuracy or earn points, and G3 has no reported failed submission comparable to G4.

These branches recommend an actual complete candidate, not an artificial scoring check. The early fallback supplies insurance; it does not lower the time penalty of a later improved submission. No hidden labels, fitted output corrections or predicted scores are used.

Sources: `submissions/candidates/G2/direct-3643218316ac.csv`, `submissions/candidates/G3/direct-fb792001c3e7.csv`, and original-account receipts under `D:/BluQubit/results/workflow/remote_actions`. G2 chi32 jobs: q9 `dAGHVu0ky3qVSoed`, q31 `9RmQMucEi62iX3a2`, q18 `bWm41clhLZ9NOIA8`; q18 chi16 `eV35YkTqQE4xkAN9`.

## Actual G3 panel review — 2026-10-24, terminal at 19:33:22 UTC

The root executor supplied these terminal results, all with zero recorded charge. This review calculated the diagnostics from those supplied values; it made no new API call or simulation.

| ID | Epsilon 0.001 | Epsilon 0.0005 | Change | Finer compute seconds |
| --- | ---: | ---: | ---: | ---: |
| q19 | -0.1346211218 | -0.2039095440 | -0.0692884223 | 39.033 |
| q14 | 0 | 0 | 0 | 99.568 |
| q34 | 0.0681082401 | 0.1363642481 | +0.0682560080 | 88.932 |

The fitted relation is `fine = 0.0141889403 + 1.6555006201 * coarse`. Residuals in the table's row order are +0.0047668662, -0.0141889403 and +0.0094220740. The slope is positive, all orderings are preserved, correlation is **0.9973297192**, and relative squared affine residual is **0.0053334312 (0.5333%)**. This three-point comparison has only one residual degree of freedom and is dominated by the extrema. It is not an expected score or validation of the 33 unmeasured rows.

The two nonzero raw changes exceed twice the coarse full-vector RMS, but much of this is positive scaling. Do not turn those raw differences into a claim of score loss. The predefined maximum-residual flag **narrowly triggers**: 0.01418894 exceeds 0.01. There is no slope or ordering failure. Keeping the predeclared rule, select its bounded-refinement branch rather than retrospectively relaxing the flag.

**Concrete allocation: complete one coherent CPU PPS epsilon 0.0005, level 1 vector now.** Reuse the three completed rows, use two CPU slots and the existing 300-second per-job cancellation thresholds, and keep the approximately 60-minute completion allocation. Place q35 early in this same cohort if practical: the .0003 timeout makes it informative about feasibility, without adding a separate diagnostic. Pause the coarse first submission for this short completion window; do not add another threshold or independent-method prerequisite.

There are 33 missing rows. The panel mean compute of 75.8443 seconds gives approximately **20.86 minutes** of remaining compute with two continuously occupied slots; using the panel maximum gives **27.38 minutes**. Queue time, heterogeneous circuits and cancellations can increase elapsed time, so these are projections, not bounds. At the existing $0.20-per-row quotes, the new rows represent approximately **$6.60 of quoted exposure**, subject to fresh admission checks; historical zero CPU charges do not make future work free.

On completion, perform the already planned full-vector/provenance review and recommend the complete .0005 candidate as the genuine first submission if valid and nonconstant. No automatic third precision level. If this bounded continuation becomes incomplete or impractical, promptly recommend the retained complete .001 baseline as provisional fallback, without splicing its rows. There is no evidence-based justification for indefinite hold.

## One higher-precision GPU PPS experiment

G3 q35 at epsilon 0.0001, level 1 on GPU would be a **purposeful new-precision tractability test**, not a same-setting hardware duplicate: its previous CPU epsilon 0.0003 run was canceled near 180 seconds without a value. It would nevertheless change both hardware and threshold, so it could not measure a matched CPU/GPU speedup. The $0.67 quote is an estimate, and the quoted 0.1 seconds is not a credible runtime forecast.

**Do not put this experiment ahead of, or make it a prerequisite for, the complete .0005 CPU candidate.** The desired next cohort is not yet CPU-blocked: its three pilots completed within 100 seconds. A singleton .0001 GPU result cannot fill a CPU cohort, and its uncertain elapsed time would delay the immediately feasible deliverable under the sole-runner lock.

After the .0005 candidate and first-submission decision, one q35 GPU .0001 diagnostic is reasonable if a higher-precision G3 route still competes for further allocation. Admit it only with a fresh quote, known current charges and GPU usage, and a bounded cancellation threshold of at most 600 seconds within remaining quotas. It must remain a separately recorded GPU result. A timeout ends this experiment; success supplies one finer point and a feasibility observation, not permission to infer full-vector accuracy or automatically start a GPU cohort. No same-threshold GPU repeat is needed.
