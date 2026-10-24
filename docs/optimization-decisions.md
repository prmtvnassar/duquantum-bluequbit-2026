# Optimization decisions and their evidence

This account separates decisions documented on Kevin's submission path from later
original-account diagnostics and the retrospective [new workflow](workflow.md).
**Execution is `PAUSED_NO_NEW_RUNS`.** No result below was produced for this
write-up. [results.md](results.md) holds score attribution and receipt verification;
the historical reports remain dated evidence, not current execution instructions.

## The framework was designed before the challenge

The user confirms that the team prepared v0 before the challenge and revised it
iteratively. Git independently preserves `8fac5d9:estimation_workflow_v0.md` on
October 23 at 23:09 EDT, before the published October 24 kickoff; its internal
date is October 22. The filename says v0 while the internal document version is
1.0. Read that frozen version to distinguish original proposals from later
addenda in the [historical copy](history/estimation_workflow_v0.md).

V0 already proposed MPS/PPS precision sweeps, within-method trends, cross-method
checks, vector shape, transpilation sensitivity, adaptive allocation, and
sample-validated extrapolation/fusion. It explicitly marked these as unvalidated
designs. The scientific story is **design → test → observe → revise**. This was
not a formal preregistration or an unchanged algorithm followed by every run.

| Original proposal | Empirical refinement |
| --- | --- |
| Use samples to choose and calibrate estimators | The released kit had three samples; sample families guided method choice without certifying larger hidden circuits. |
| Compare precision and MPS–PPS agreement | G4 showed that shrinking increments on two rows and matching PPS zeros were insufficient; retain direction changes and wider coverage. |
| Test transpilation | Native S3/G3 evidence made representation testing a prerequisite for meaningful threshold refinement. |
| Allocate expected benefit per cost | G2 endpoint panels and runtime discrepancies motivated decision-changing transition/interior tests and separate quote, elapsed-time, and billing evidence. |
| Validate extrapolation and fusion | Negative held-out checks kept both disabled, preserving direct simulator values. |
| Refine complete baseline predictions | The later G2 hybrid motivates selective precision, conditional on row provenance and a reproducible assembly policy. |

The [LaTeX paper](../writeup/main.tex) formalizes this revised protocol and its
limits. Its novelty claim is a concrete integration and empirical case study;
general superiority and field-wide originality have not been demonstrated.

## Calibration and reuse established the useful starting points

The campaign used public circuits with known values to compare approximation
families without paid sample simulation. All three official sample submissions
displayed 100/100: local exact values for S1/S2 and local PPS epsilon 0.01 for S3.
A separate stricter local calibration selected S1 MPS chi8, S2 MPS chi128 and S3
PPS epsilon 0.001, with maximum errors approximately `2.7e-15`, `0.00329` and
`0.00653`. The uploaded sample settings and calibration selections are different
experiments. Rounded correlation scores did not certify pointwise accuracy.
[Sample receipts](../submissions/README.md), [calibration](../reports/calibration_evidence.json).

Kevin's recorded G2 reasoning adds a 24-qubit proxy with the graded chain's depth:
MPS chi128 reached approximately unit squared correlation with its exact values,
while PPS epsilon 0.001 reached about 0.974. For the mostly-Clifford S3 family,
his recorded comparison favored PPS over MPS. These observations supported method
selection; they did not predict larger hidden-circuit scores or supply a matched
Haar-grid proxy for G4. [G2 method record](../submissions/teammates/kevin/G2/submitted-v1.txt),
[Kevin's approach](../submissions/teammates/kevin/README.md), source tools in
`kevin/experiment` commit `e6707fa`.

G1 required no approximation: Kevin's 30-row exact CPU vector has a reported
300/300 result and verified per-job provenance. Importing it from `9714dab` and
reusing it avoided 30 duplicate simulations. This is the clearest resource saving:
an available exact anchor replaced work, rather than merely making repeated work
faster. The original account's separate submission confirmation does not establish
its own score. [G1 receipt](../submissions/teammates/kevin/G1/submitted-v1.json),
[original-account confirmation](../submissions/G1/user-reported-submission.json),
reuse commit `de9a473`.

## G2: choose chain precision, then respect the cost of further refinement

Kevin submitted a complete CPU MPS chi128 vector and reported **498/600**, the
highest G2 score backed by a dedicated scored submission receipt. His
partial chi256 follow-up moved a value by roughly 0.06; quoted interior jobs of
about $10.88 and seven hours made completing that refinement unattractive under
the campaign resources. The stopping reason was cost and time, not convergence.
The preserved explanation calls the possible gain uncertain; the quotes do not
quantify it. [Submitted file and method](../submissions/teammates/kevin/G2/submitted-v1.txt),
[receipt](../submissions/teammates/kevin/G2/submitted-v1.json), source commit `dce1fa0`.

The original account separately reported **342/600** for CPU MPS chi32. The older
teammate receipt assigning 498/600 to those same chi32 bytes conflicts with Kevin's
new chi128 receipt and must remain marked disputed. Comparing 342 and 498 across
accounts is not a controlled chi32-to-128 score experiment. The new provenance
corrects attribution; the time penalty does not explain or reconcile that conflict.
[Original receipt](../submissions/G2/attempt-01.json),
[attribution correction](../submissions/teammates/kevin/README.md), import commit `2a3eb2b`.

A newer complete G2 CSV in main is user-confirmed as submitted. Its upload commit
claimed a rowwise mix of 23 GPU MPS chi512 values and 13 chi64 values. A later
[repository note](../submissions/candidates/G2/G2_23_512_and_13_64.score-report.txt)
in commit `030518f` claims **579/600**, now the highest repository-reported G2 score.
The decision to use a rowwise mix is recorded, but the specific row sources and
their completion receipts are absent. No website feedback, submitting account,
official attempt or time penalty accompanies the score note. The report supports
studying targeted high-chi MPS as a future option; it does not show that this mix
caused a score gain over Kevin's separate 498/600 result or used resources more
efficiently. Preserve the exact CSV and the claim's source without promoting it
to an independently verified result. [Hybrid CSV](../submissions/candidates/G2/G2_23_512_and_13_64.csv),
[feedback record](../submissions/candidates/G2/G2_23_512_and_13_64.feedback.json),
[branch audit](results.md), upload commit `5807762`.

Later original-account analysis found that q0/q18/q35 gave an impressive
chi16/32 correlation of 0.99999965 because saturated endpoints dominated the
three-point panel. It therefore proposed unsaturated q9, the opposite transition
q31 and the middle q18 for more informative precision coverage. This is a lesson
for future allocation, not the cause of Kevin's earlier chi128 result. Existing
chi128 evidence should now be inspected before any such new work.
[Transition review](../reports/REFINEMENT_REVIEW.md),
[staged panel rationale](../reports/next_allocation_review.md).

The staged q9/q31 CPU chi64 diagnostics then moved q9 from 0.494442 to 0.301455
and q31 from 0.551690 to 0.416197, with $0 recorded charges. They confirmed
large changes at both transition regions that the earlier saturated-endpoint
panel did not expose. They were only two rows, so they did not establish a
complete chi64 score or which direction was more accurate. They also do not
explain the separate submitted hybrid without its row-to-job provenance.
[Row receipts](../runs/jobs.csv), [decision record](../runs/decisions.csv).

## G3: representation selection enabled useful threshold refinement

Native PPS's default level 2 returned a constant-zero G3 vector in the recorded
tests. On the known sample `Duke_S3_1` at epsilon 0.01, levels 2/3 returned zero,
whereas levels 0/1 returned approximately -0.595/-0.580 against an exact value
near -0.538. The stored-ID versus uploaded-QASM comparison did not remove this
behavior. Choosing level 1 therefore addressed a representation failure before
further threshold work. Preservation of Clifford structure is Kevin's proposed
mechanism, not an independently established diagnosis of the service internals.
[Diagnostic record](../submissions/teammates/kevin/README.md), source commits
`e6707fa` and `8d85f21`.

At fixed native level 1, Kevin then tightened epsilon:

| Epsilon | Exact-zero rows out of 36 | Recorded outcome |
| --- | ---: | --- |
| 0.01 | 33 | Complete experiment; not submitted |
| 0.001 | 9 | Teammate-reported 534/800 |
| 0.0003 | 3 | Teammate-reported **773/800** |

The latter two complete profiles agreed at squared correlation approximately 0.80,
compared with approximately zero for the first pair. The score increase of 239
points accompanies a controlled threshold change within Kevin's reported path,
with the representation held fixed and raw values retained. This is the strongest
observed approximation improvement in the retained graded submissions. Fewer zeros
and stronger agreement supported the choice but did not certify convergence or
predict 773 in advance. [v2 receipt](../submissions/teammates/kevin/G3/submitted-v2.json),
[v3 receipt](../submissions/teammates/kevin/G3/submitted-v3.json),
[v3 explanation](../submissions/teammates/kevin/G3/submitted-v3.txt), commits
`4cedd76`, `ea163eb`, imported by `2a3eb2b`.

The original-account epsilon 0.001 baseline has the same 36 numerical values as
Kevin's submitted v2, with different CSV serialization; it has no original-account
score. The later epsilon 0.0005 q19/q14/q34 panel had positive scaling, preserved
order and a narrowly triggered residual flag. It motivated a bounded continuation
in its dated review. That proposal is now superseded by the pause and availability
of Kevin's finer complete vector. It did not produce Kevin's 773/800 result and
should not be narrated as its causal precursor. [Cross-account vector audit](results.md),
[dated panel review](../reports/next_allocation_review.md).

At the user's stop instruction, the original-account epsilon 0.0005 continuation
had nine of 36 rows completed and two owned in-flight jobs canceled. All owned
jobs reached terminal status, with $0.20 total known account charges from the
earlier GPU pilot. The nine saved rows remain diagnostics only. This is an
instruction-driven stop, not numerical convergence or a full-vector outcome.
[Terminal stop snapshot](../reports/audit/campaign-stop.json).

## G4: a failed result changed what counted as useful evidence

The complete CPU chi32 candidate received an accepted **0/1000**, as reported by
the user with account and attempt unspecified. Its local format and provenance
audit passed. On ten matched chi16/32 rows, correlation 0.85912, residual energy
26.19% and 12/45 order reversals exposed substantial shape sensitivity. q4/q0
accounted for 60.49% of that subset's residual energy, motivating initial chi64
checks and an independent PPS check. This selected evidence explains the checks;
it does not locate hidden error. [Feedback](../submissions/candidates/G4/direct-930f7e5b7d14.feedback.json),
[subset review](../reports/G4_PARTIAL_TREND_REVIEW.md).

The completed chi64 panel refuted generalization from its first two rows:

| Row | chi16 | chi32 | chi64 | Observed pattern |
| --- | ---: | ---: | ---: | --- |
| q0 | 0.558910 | 0.270272 | 0.097787 | Shrinking increments |
| q4 | -0.005732 | 0.331990 | 0.493042 | Shrinking increments |
| q1 | 0.135555 | -0.053917 | 0.007232 | Direction reversal |
| q19 | 0.362228 | 0.288101 | 0.084401 | Latest increment grows about 2.75-fold |

All four completed with $0 recorded charge and within their elapsed diagnostic
thresholds. Local contraction did not generalize, and completion did not justify
a 38-row chi64 commitment. At q4, level-1 PPS returned zero at both epsilon 0.001
and 0.0001; compute grew from 5.35 to 178.913 seconds, **33.4-fold without resolved
signal**. This supported stopping blind threshold escalation, not accepting zero
as truth. Terminal receipt details are in [results.md](results.md); the earlier
[GPU recovery report](../reports/GPU%20precision%20recovery.md) predates completion
of q1/q19 and must be read with that update.

## Hardware and rejected shortcuts complete the decision story

The matched G4 q0 chi32 CPU/GPU outputs differed by only `6.63e-12`. GPU roughly
halved compute time but saved only 10.25 seconds elapsed, at $0.20 versus $0 on
those receipts. Since CPU chi64 subsequently fitted its diagnostic caps, another
same-chi GPU timing run was deferred. The supplied paper motivates GPU use to
reach expensive precision, with workload-dependent crossover and nonmonotonic PPS
error; it supplies no hidden-circuit accuracy guarantee. No high-chi GPU or GPU
PPS improvement is claimed from its quotes.
[Matched evidence](../reports/gpu_matched_pilot.json),
[paper methods](../research_notes/GPU%20precision%20recovery/paper_methods.md),
[dated GPU quotes](../reports/alternative_gpu_quotes.json).

The campaign also tested shortcuts offline. Geometric/Aitken extrapolation on
saved S2 precision histories worsened held-out next-level MAE in both windows
(0.04676 versus 0.04447; 0.01344 versus 0.00955), and the second window lost about
3.86 score points against exact values. Leave-one-circuit-family-out fusion showed
no gain. Both remained disabled; submission values stayed direct simulator
outputs. [Extrapolation rejection](../reports/extrapolation_rejection.json),
[fusion evaluation](../reports/calibration_evidence.json).

These results support a prospective policy of reusing complete evidence,
separating representation from precision, selecting decision-changing diagnostics,
and distinguishing resource stops from convergence. That policy is the synthesis
of the campaign. The receipt-backed G1/G2/G3 paths explain their reported scores;
the newer G2 score report still lacks the account and row provenance needed to
explain the full mixed-precision path.
