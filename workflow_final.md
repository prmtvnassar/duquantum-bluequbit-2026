# Current graded-submission workflow

Updated October 24, 2026 after the GPU precision review, both G4 CPU chi64
diagnostics, both independent PPS level-1 threshold checks and the start of the
q1/q19 CPU chi64 panel extension. The objective is maximum
graded accuracy with as few justified official submissions as practical. No
sample, approximation agreement or paper benchmark guarantees the hidden score.
The [GPU precision recovery report](<reports/GPU precision recovery.md>) separates
measured results, paper claims and proposed experiments.

Resource limits come from [configs/workflow_final.json](configs/workflow_final.json).
Its PPS/chi16 starting priors are superseded by saved native evidence through
[campaign_reasoning.py](src/otoc/campaign_reasoning.py) and
[graded.py](src/otoc/graded.py). Historical designs remain in
[estimation_workflow_v0.md](docs/history/estimation_workflow_v0.md). Older reports
are evidence snapshots, not current account-status authorities.

## Current evidence and recommendation status

| Problem | Complete direct evidence | Current decision |
| --- | --- | --- |
| G1, 30-qubit Haar chain | Reused exact CPU vector from Kevin; source commit `9714dab3422134c77b7fc36f99e86f5f2dada921` | Submission user-confirmed; 100% score teammate-reported. Preserve the anchor; no repeat simulations. |
| G2, 36-qubit Haar chain | CPU MPS chi32, candidate `direct-3643218316ac`, $0 recorded cohort cost | Original-account attempt 1 is user-reported 342/600 with 3.48-hour penalty. The same retained CSV was separately reported as teammate attempt 1, 498/600. Preserve both attributed receipts; investigate transition-region precision. |
| G3, 36-qubit mostly-Clifford grid | All 36 CPU PPS rows, epsilon 0.001, native level 1, candidate `direct-fb792001c3e7`, $0 recorded cohort cost | Complete, archived and held for numerical review. Tighter-threshold and independent-method disagreement remain unresolved; no upload or score is inferred. |
| G4, 38-qubit Haar grid | CPU MPS chi32, candidate `direct-930f7e5b7d14`, $0 recorded cohort cost | Accepted 0/1000 is user-reported; account and attempt unknown. Local CSV/provenance audit passed. Do not resubmit it or automatically complete a higher-chi cohort. |

The G2 receipts identify the same CSV hash, but the cross-account score difference
is unexplained. Do not transfer, average or fit one account's score to another.
The exact website-uploaded bytes and explanation were not independently observed.
Original-account headroom is 258 points, not the teammate-derived 102.
See [original G2 receipt](submissions/G2/attempt-01.json),
[teammate receipt](submissions/teammates/teammate_reported/G2/attempt-01.json),
[G3 hold review](submissions/candidates/G3/direct-fb792001c3e7.review.json), and
[G4 feedback](submissions/candidates/G4/direct-930f7e5b7d14.feedback.json).

The new G4 CPU chi64 diagnostics are terminal with $0 actual cost:

| ID | chi16 | chi32 | chi64 | chi64 compute seconds |
| --- | ---: | ---: | ---: | ---: |
| q0 | 0.558910 | 0.270272 | 0.0977871537006 | 202.018 |
| q4 | -0.005732 | 0.331990 | 0.4930423131044 | 336.895 |

These are meaningful precision changes, not error estimates. Their increments
contract locally, but two rows cannot establish shape convergence. Reuse the
[q0 receipt](D:/BluQubit/results/workflow/remote_actions/225a79bfa8bb77ab409bb6eb552ea41c5b9d63aebdb7b0713f531ebc25858568.json)
and [q4 receipt](D:/BluQubit/results/workflow/remote_actions/87add220aab23167d1965176a5d518d441a407a780638d3d61c535badb4a7ff9.json).
The [G4 partial review](reports/G4_PARTIAL_TREND_REVIEW.md) retains the earlier ten-row
chi16/32 comparison: correlation 0.85912, 26.19% affine residual energy and 12/45
order reversals. Its old pending-job and teammate-only G2 status is superseded here.

G4 q4 CPU PPS at native level 1 returned **zero at both epsilon 0.001 and
0.0001**. Compute increased from 5.35 to 178.913 seconds: **33.4 times more work
without resolved signal**. The finer run had 0.368 queue seconds and $0 actual
charge, completing at 19:23:12 UTC as job `onNMNzb84Wz82A0D`. Stop blind threshold
escalation; matching zeros do not establish accuracy or reject the MPS results.
[Coarse PPS receipt](D:/BluQubit/results/workflow/remote_actions/a0c1a8ca3db38b92021d125dbb11727c2006a8de9f731f48e7922bd6a8f7fe19.json),
[finer PPS receipt](D:/BluQubit/results/workflow/remote_actions/e62bbc55568029b732b145e156492df4029190f5a1b2d0e776c6902fa676148a.json).

CPU chi64 q1/q19 diagnostics are now running, each with a 600-second elapsed
cancellation-request threshold and 2400-second quote ceiling. q1 had a prior sign
change; q19 supplies a separated interior point. With q0/q4 they form a four-row
panel, still not full-vector accuracy evidence. Reconcile and review these jobs
before deciding on q37, further precision or any full-cohort commitment.
[q1 receipt](D:/BluQubit/results/workflow/remote_actions/f5af7715e19da04b093115c2dddf58dbc1b56f1b24ded4f17a51a07a8a5419d3.json),
[q19 receipt](D:/BluQubit/results/workflow/remote_actions/84fa71b407af83bc1049821831179a6607e2e7ff19106f145e22191eb096c348.json).

The original account's authoritative runtime state remains
`D:/BluQubit/results/workflow`; the isolated Git worktree records code and review
artifacts. Never switch to a dummy, assistant or teammate account/state root to
continue the campaign or resolve ambiguous jobs.

## Export is separate from a submission recommendation

A cohort uses one device and identical full native options for every retained
problem ID. CPU/GPU and different PPS levels are distinct cohorts. An isolated
finer result stays in the evidence ledger; it never replaces one row in an older
complete vector. Every ID is a separate program with its own target Pauli string,
using q0 rightmost.

The exporter checks full template coverage, finite values, provenance and
resolved signal. Its compatibility field `submission_eligible` means only
`format_and_resolved_signal_only`. Approximate exports carry
`submission_recommended: false` and `review_status: NUMERICAL_REVIEW_REQUIRED`.
Highest completed precision is a deterministic export-selection rule, not a
monotonic-accuracy claim. A complete exact resolved vector has a separate exact
recommendation reason without predicting its grade. See
[export implementation](src/otoc/graded.py:370) and [controller contract](docs/COHORT_BATCH.md).

Before recommending another approximate submission, review precision sensitivity,
independent-method or representation evidence, full-vector shape and applicable
actual score feedback. For G4, require broader same-ID evidence spanning
q4/q0/q1/q19/q37, further precision and an informative independent-method review
before another bulk commitment or upload. Nonzero output, contracting steps,
larger amplitude or agreement with the zero-scoring baseline does not pass this
review by itself. No universal numeric convergence threshold is validated here.

Official attempts are for genuine complete candidates, not tests of signs,
permutations or fitted corrections. The retained rules allow 20 attempts per
problem and retain the best score. Its submission-time penalty governs the
relevant tie-break contribution: an early poor result gives fallback insurance,
not a lower penalty for a later better result. Prefer a reviewed result promptly
and retain the submission buffer. [Retained rules](docs/history/workflow_v1.md:45).

## Next bounded experiments

1. **Review G3's complete baseline offline.** Audit the full vector and saved
   precision/representation comparisons before recommending it. Its q0 change
   from about -0.072292 at 0.001 to -0.147750 at 0.0003, and canceled finer q35
   run, remain sensitivity evidence.
2. **Review the fixed-level PPS plateau and stop blind escalation.** G4 q4
   remained zero at 0.001 and 0.0001 while compute grew 33.4-fold. Do not
   automatically tighten epsilon again or buy a same-threshold GPU repeat.
   These zeros do not identify truth; retain independent-method disagreement.
3. **Complete the already launched q1/q19 CPU chi64 diagnostic window.** Preserve
   their 600/2400-second execution/quote limits and reconcile saved jobs without
   duplicates. Review the resulting q0/q1/q4/q19 panel before q37, a further
   precision step, representation change or full 38-row spending. Four varied
   rows still cannot validate full-vector accuracy. No bulk G4 is recommended.
4. **Defer the same-chi64 GPU timing repeat.** CPU chi64 fitted its cap on both
   initial IDs, and hardware alone adds no precision. GPU chi128 remains a
   conditional precision experiment subject to evidence, cost and quotas, not
   an automatic next step. Reconcile canceled jobs to terminal status and known
   cost before any later fallback.
5. **Reconsider allocation after each window.** G2 q9 is an unsaturated transition
   row for a proposed CPU chi64 diagnostic; broaden to transition and endpoint
   rows before a full cohort. G3 can compare 0.001/0.0005 at fixed native level 1,
   including q35, or use its quoted GPU branch when justified. These are reasoned
   priorities, not predicted score gains. Scores never determine individual values.

A lightweight visualization is being prepared from saved records to make the
precision/resource tradeoffs open to critique; it requires no new quantum calls.

These proposals apply the paper's precision sweeps, controlled hardware comparisons
and nonmonotonic PPS checks. Quantum Rings, Qiskit pauli-prop, OBP and
PauliPropagation.jl need circuit gates or QASM that hidden IDs do not expose.
Local alternatives remain sample tools. Do not extract private circuits, combine
separate IDs into one circuit or bypass access restrictions. The paper's target-bit
recovery is not an OTOC estimator. [Paper/SDK synthesis](<reports/GPU precision recovery.md>).

## CPU and GPU routing evidence

The matched G4 q0 chi32 trial agreed within 6.63e-12. GPU compute took 24.189
seconds versus 48.593 on CPU, but elapsed time was 44.804 versus 55.055 seconds:
only 10.25 seconds saved, for $0.20 versus $0 on these receipts. This supports
CPU at that configuration; it neither proves accuracy nor rules out a useful
higher-chi GPU advantage. [Matched evidence](reports/gpu_matched_pilot.json).

Installed SDK 0.19.0b1 supports hidden-ID `mps.gpu` chi64/128 and
`pauli-path.gpu`; PPS thresholds must be **at least 1e-5**, with native levels 0?3.
The paper's finer research sweep cannot bypass this floor. Five original-account
estimate-only requests on October 24 at 19:09 UTC succeeded:

| Route | Quoted USD | Quoted seconds |
| --- | ---: | ---: |
| G4 q4 MPS GPU chi64 | 1.08 | 968.2 |
| G4 q4 MPS GPU chi128 | 2.73 | 2448.2 |
| G4 q4 PPS GPU 0.001, level 1 | 0.67 | 0.1 |
| G4 q4 PPS GPU 0.0001, level 1 | 0.67 | 0.1 |
| G3 q35 PPS GPU 0.0001, level 1 | 0.67 | 0.1 |

These [dated quotes](reports/alternative_gpu_quotes.json) are not measurements or
binding cost caps. PPS's repeated 0.1 seconds is an unreliable runtime forecast.
No high-chi GPU or GPU PPS pilot has completed in this review. Both GPU MPS quotes
exceed the ordinary 600-second policy. The explicit targeted GPU path is now implemented and released. The coordinator
reported 124 tests and 137 subtests passing plus import/Bell-state smoke checks;
these were offline checks, not cloud trials. GPU diagnostics require one slot,
finite known actual total/rolling usage plus full quoted runtime within quota,
durable dollar exposure, and the same unknown/foreign-state gates. They never
automatically export. Full-cohort mode remains CPU-only. Use the reviewed
[GPU admission contract](docs/COHORT_BATCH.md:121); legacy serial GPU behavior
must not be confused with the targeted controller's separate quote/execution caps.

At the saved snapshot, 24.189 GPU seconds and $0.20 were known. The total GPU limit
is 27000 seconds and the rolling-hour limit 2700. Chi128 alone quotes about 91.5%
of the saved remaining hourly allowance. Representative 38-row GPU MPS costs are
$41.04 at chi64 or $103.74 at chi128, above $27; one-ID multiplication is not a
full-cohort quote. GPU PPS at the representative rate would consume $25.46 for
G4 before other commitments. No bulk GPU plan follows. Reconcile usage and
re-quote before every actual action.

## Budget, time and execution ownership

| Control | Current policy |
| --- | --- |
| Sample spending | $0 |
| Graded budget | $30 total; 10% ($3) cushion; planned exposure <= $27 |
| Missing selected-baseline reserve rates | At least $0.30/G2 row, $0.20/G3 row and $0.27/G4 row, increased by matching quotes |
| Ordinary remote job cap | 600 seconds |
| MPS chi32 cap | 900 seconds |
| Explicit CPU diagnostic limits | Separate quote admission and elapsed cancellation-request thresholds; G4 chi64 used 2400/600 seconds |
| Submission buffer | 20 minutes before October 25 at 15:30 UTC |
| Job count | At most 800 account jobs |
| Serial executor | `max_concurrent_jobs: 1`, one `remote_runner` owner |
| Explicit CPU cohort controller | At most two owned jobs under the same sole lock |
| Explicit targeted GPU controller | One owned GPU job, implemented/tested; no automatic export |
| GPU usage | 27000 seconds total, 2700 per rolling hour; unknown usage blocks GPU |

Every launch needs a fresh exact-ID/device/full-options quote and account
reconciliation. Admission sums known charges, outstanding quoted commitments,
the full new quote and genuinely missing unreserved baseline coverage. Quotes
remain commitments until terminal status and actual charge are known. Earlier
$0 charges and shorter cancellation thresholds never discount a new dollar quote.
The $27 ceiling is not service-enforced billing protection. Deadline admission
retains the longer of quote runtime and execution timeout plus submission buffer.

A valid complete nonconstant older cohort exempts that problem's missing-baseline
coverage reserve, not active/new refinement commitments. This operational
exemption does not establish quality, especially for failed G4. Reserve evidence
is tied to device/options; representative quotes for missing coverage refresh at
startup and after five minutes. Known charges persist by job ID across restarts
and account-index regressions. Unknown costs, foreign active jobs, ambiguous
intents and inconsistent state block launches. [Full contract](docs/COHORT_BATCH.md).

## What numerical diagnostics can establish

Pointwise changes expose observable sensitivity and disagreement between methods.
Within-method trends retain signed increments, slopes per logarithmic precision
step, sign changes and contraction ratios. Oscillation or growing changes raise
refinement priority. A geometric tail proxy is a scheduling heuristic, never an
error bar or an extrapolated output. Flat sequences remain `FLAT_UNVERIFIED`:
PPS can drop all terms and low-chi MPS can plateau far from truth.

Shape sensitivity compares aligned vectors at fixed device and, for PPS, native
level. Center x and y, fit `a = (x dot y)/(x dot x)`, and retain residual
`r = y - a*x`. Row influences `r_i^2/(y dot y)` sum to `1 - rho^2`; signed shape
change is `1 - rho`. Explicitly flag a negative slope: sign reversal can have
zero residual while scoring differently. Nearly constant vectors below centered
RMS 1e-4 cannot support this diagnostic; pilot recovery separately uses a range
above 1e-4. Sparse panels cannot validate full-vector shape.

Positive affine changes preserve Pearson correlation, so larger amplitudes or
small residuals between approximations do not prove closeness to truth. Keep
shape beside pointwise and independent-method evidence. Neither absolute error
nor fidelity guarantees a score without information about true centered signal.
PPS error can be nonmonotonic as epsilon decreases. Native levels and local
algorithms are different representations; equal thresholds are not equal accuracy.

The local stopping diagnostic asks for three precision levels per method, two
small consecutive changes, small cross-method disagreement and stable resolved
shape. Its pointwise tolerance is `min(0.001, 0.03 * max(signal_scale, 0.02))`,
shape tolerance 0.001. Sample histories do not validate a universal native rule.
**Automatic graded convergence stopping remains disabled.** Budget, timeout,
deadline and job limits can stop work without certifying accuracy.

No extrapolation, fusion, bias correction or hidden-label fitting is enabled.
Tested extrapolation failed held-out checks and fusion showed no consistent gain.
Mixing zeros with a positive multiple of MPS merely rescales its vector. All
candidates retain raw direct simulator values and full provenance.

## Samples remain calibration evidence

All three official sample submissions display 100/100, one attempt each. S1/S2
used local exact statevectors; S3 used the independent local coefficient-cutoff
Pauli engine at epsilon 0.01. The rounded display is not an error-free guarantee.
Uploaded bytes and browser-observed receipts are in [submissions/](submissions/README.md).

Separate local calibration selected S1 MPS chi8, S2 MPS chi128 and S3 local PPS
0.001 at local optimization level 1, with maximum errors about 2.7e-15, 0.00329
and 0.00653. These met local targets max error <=0.01 and offline score >=99/100.
Native kernels and levels differ; paid native sample approximation quotes were
not launched under the $0 sample-spend rule. See
[calibration evidence](reports/calibration_evidence.json) and
[sample benchmarks](reports/sample_benchmarks.json). G4 has no matched sample family.

## Operation, recovery and recording

Review saved plans without network access:

```powershell
.venv312\Scripts\python.exe scripts/graded_workflow.py --offline-plan
```

Normal planning obtains quotes; simulation requires explicit `--execute`. Offline
quotes never authorize execution. Use reviewed explicit target/cohort commands
in [COHORT_BATCH.md](docs/COHORT_BATCH.md), with the original account state root.
Do not start another runner while the sole owner holds its lock. Completed
targets are reused; canceled/failed targets are not silently retried. Broad
discovery remains disabled, and existing baselines do not authorize automatic
bulk refinement without the numerical decision above.

`results/workflow/STOP` blocks launches and requests cancellation of owned jobs.
Cancellation is not instantaneous termination, zero charge or release of a
commitment. Retain unresolved receipts. A `SUBMITTING` record without a job ID
must be matched to service history before retry; never delete receipts or locks
to force a launch. Save intent/reservation before requesting a job, then record
known transitions and actual cost. Request timeout is not a retry permit.

Candidate export never uploads. Record actual submissions with
[scripts/record_submission.py](scripts/record_submission.py), retaining owner,
actual attempt, CSV hash, source and displayed score. `browser_observed` and
`user_report` stay distinct; user reports are `USER_REPORTED`, not
`VERIFIED_BROWSER`. Use `prepared_explanation` unless website wording was
confirmed. `--time-penalty-hours` stores the reported number without inventing
upload time. Teammate attempts have separate owner paths; G4's unknown owner and
attempt remain candidate feedback rather than a fabricated receipt.

Quotes, intents, run records, immutable submission evidence and decisions form
the audit trail. A heartbeat or available GPU option does not authorize an
unreviewed action, and no score is used to manufacture row values.
