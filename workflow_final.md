# Current graded-submission workflow

This is the active operational guide for October 24, 2026. The resource policy is
[configs/workflow_final.json](configs/workflow_final.json); effective method choices
also depend on the saved native receipts through
[src/otoc/campaign_reasoning.py](src/otoc/campaign_reasoning.py) and
[src/otoc/graded.py](src/otoc/graded.py). The JSON's original PPS/chi16 entries are
starting priors, not a replacement for that evidence-based selection. The design
in [docs/history/estimation_workflow_v0.md](docs/history/estimation_workflow_v0.md)
is retained as history.

## Current choices and evidence

| Problem | Selected direct cohort | Basis and remaining uncertainty |
| --- | --- | --- |
| G1, 30-qubit Haar chain | Reuse all 30 exact CPU values from Kevin | The retained CSV matches his completed source jobs at commit `9714dab3422134c77b7fc36f99e86f5f2dada921`. The user confirmed submission; the 100% score is teammate-reported. No repeat simulations are needed. |
| G2, 36-qubit Haar chain | `mps.cpu`, `mps_bond_dimension: 32` | S2 favors MPS, and the complete native chi32 pilot cohort is available. The chi16-to-chi32 sign change at q18 shows unresolved precision sensitivity. Chi128's representative quote exceeds the current resource allocation. |
| G3, 36-qubit mostly-Clifford grid | `pauli-path`, threshold `0.001`, native transpilation level `1` | The sample favors Pauli propagation. The complete level 1 pilot resolves signal where level 2 returned zeros. The tighter 0.0003 pilot cohort is incomplete; its q0 result must not replace one row of the coarse cohort. |
| G4, 38-qubit Haar grid | `mps.cpu`, `mps_bond_dimension: 32` | Complete native chi32 pilots support this provisional route after flat PPS pilots. G4 has no matching sample family, and q0 changes substantially from chi16 to chi32. |

These choices are provisional baselines, not convergence certificates. See
[reports/GRADED_CAMPAIGN.md](reports/GRADED_CAMPAIGN.md) for the measured comparisons
and [reports/GRADED_DEBATE_REVIEW.md](reports/GRADED_DEBATE_REVIEW.md) for the
adversarial review. Broad discovery is currently disabled so that actual complete
vectors take priority over another round of sparse checks.

G2 now has a complete 36-row chi32 candidate at $0 recorded cohort cost, preserved
with its explanation and job manifest in [submissions/candidates/](submissions/candidates/README.md).
It has not been recorded as an official upload. The next-check review in
[reports/REFINEMENT_REVIEW.md](reports/REFINEMENT_REVIEW.md) distinguishes G2's
nearly affine three-pilot change from G4's stronger shape change; neither sparse
comparison certifies the full vector. The first two-job CPU controller trial
completed successfully; [reports/cpu_concurrency_trial.json](reports/cpu_concurrency_trial.json)
records timing, costs and its limitations.

A **cohort** means one device and identical full native options for every ID in a
problem's retained template. CPU and GPU are separate cohorts; different PPS
transpilation levels are separate cohorts. Coverage counts rows in the selected
cohort. A higher-precision result for one ID stays in the evidence ledger until
its entire cohort is complete. It never replaces an isolated row in a complete
older vector.

All three official sample submissions display **100/100**, with one attempt used
per problem. S1 and S2 used local exact statevectors; S3 used the independent local
coefficient-cutoff Pauli engine at epsilon 0.01. The exact uploaded bytes and
observed website receipts are in [submissions/](submissions/README.md). The display
rounds a correlation-based score: it does not establish error-free values or a
maximum absolute error bound.

Separate local calibration used local Aer references for S1/S2 and free exact
CPU service results for S3, with the engineering targets
maximum absolute error <= 0.01 and offline correlation score >= 99/100. Its
selected settings were S1 MPS chi8, S2 MPS chi128 and S3 local PPS 0.001 at local
optimization level 1; the respective maximum errors were about 2.7e-15, 0.00329
and 0.00653. These are measured local results, not native service guarantees.
Local Quimb MPS and coefficient-cutoff PPS differ from the native kernels, and
local optimization levels are not equivalent to native transpilation levels.
Native MPS/PPS sample quotes were paid, so those native approximation pilots were
not launched under the $0 sample-spend rule. See [reports/calibration_evidence.json](reports/calibration_evidence.json)
and [reports/sample_benchmarks.json](reports/sample_benchmarks.json).

## Budget, time and execution ownership

| Control | Current policy |
| --- | --- |
| Sample spending | $0 |
| Graded budget | $30 total, with a 10% ($3) cushion; planned exposure must fit $27 |
| Selected baseline reserve rates | At least $0.30 per missing G2 row, $0.20 per G3 row and $0.27 per G4 row; matching quotes can increase them |
| Ordinary remote job cap | 600 seconds |
| MPS chi32 cap | 900 seconds for both diagnostic and cohort-completion jobs |
| Submission buffer | 20 minutes before the configured deadline, October 25 at 15:30 UTC |
| Job count | At most 800 account jobs under this policy |
| Serial executor | `max_concurrent_jobs: 1`; one `remote_runner` owner |
| Explicit CPU cohort controller | At most two owned jobs, under the same sole `remote_runner` lock; see [docs/COHORT_BATCH.md](docs/COHORT_BATCH.md) |

The $27 ceiling is a planning constraint, not a service-enforced cost cap. Every
launch requires a fresh quote for the exact ID, device and full options, plus
fresh account reconciliation. Quotes remain commitments until terminal status
and actual cost are known. Previous $0 bills never justify reducing a future
quote. Unknown costs, foreign active jobs, ambiguous submission intents and
inconsistent account state block new launches.

For the bounded cohort controller, admission includes known charges, outstanding
quoted commitments, the new quote and reserves for still-missing, unreserved
selected baseline rows. A valid complete nonconstant older cohort preserves a
usable baseline while a refinement is incomplete; only that problem's future
coverage reserve is then exempted. Active and new refinement jobs still reserve
their full quotes. Reserve evidence is tied to device and full options.
Representative quotes for missing coverage are refreshed at startup and after
five minutes, while known charges persist by job ID across restart and account
index regressions. The controller's operational
contract and release checks are in [docs/COHORT_BATCH.md](docs/COHORT_BATCH.md).

## What the diagnostics decide

Pointwise changes, within-method trends and full-vector shape answer different
questions and are retained together.

- **Pointwise sensitivity** measures changes in the actual observable values and
  disagreement between methods. Large changes identify numerical instability
  even if the correlation-based score would ignore a common offset or positive
  rescaling. Agreement alone cannot exclude shared bias.
- **Within-method trends** retain signed steps, slopes per logarithmic precision
  increment, sign changes and contraction ratios. Oscillation or growth raises
  refinement priority. A contracting sequence may provide a geometric tail
  proxy for scheduling. A flat sequence is `FLAT_UNVERIFIED`: PPS may have dropped
  every term, and low-chi MPS can plateau far from the exact reference. The tail
  proxy is never an error bar or an extrapolated output.
- **Shape sensitivity** compares two complete aligned precision vectors at the
  same device and, for PPS, the same transpilation level. For centered vectors
  `x` and `y`, set `a = (x dot y)/(x dot x)` and residual `r = y - a*x`. The row
  influences `r_i^2/(y dot y)` identify where refinement changes shape after
  removing offset and scale. Their sum is `1 - rho^2`; the separate signed shape
  change is `1 - rho`. A negative slope is explicitly flagged, since a sign
  reversal can have zero residual while changing correlation completely.

The shape diagnostic is useful because positive affine changes preserve Pearson
correlation, whereas local distortions can change the score. It measures
sensitivity **between estimates**, not distance to unknown truth or expected
score gain. Sparse pilots cannot establish full-vector shape stability. Nearly
constant vectors below centered RMS 1e-4 cannot support the shape diagnostic;
the pilot recovery gate separately uses a range greater than 1e-4.

Pilot selection requires every configured pilot ID at one device and identical
full options. It prefers a resolved cohort in the original method family, then
precision; it does not rank candidates by how large their amplitudes look. A
switch to the other family requires an available original-family pilot cohort
and unresolved original-family signal. The selected exact device and options
are preserved. Nonconstant output only permits a provisional baseline choice.

The local stopping diagnostic requires at least three precision levels in each
method, two consecutive small changes, small cross-method disagreement and
resolved stable vector shape. Its pointwise tolerance is
`min(0.001, 0.03 * max(signal_scale, 0.02))` and shape tolerance is 0.001.
Calibration replays complete coarse-to-fine prefix pairs, including early
plateaus; it does not only examine each method's best result. Available samples
and incomplete histories do not validate a universal stopping rule or native
transfer. **Automatic convergence stopping on graded IDs remains disabled.**
Budget, deadline, timeout and job limits can stop work without certifying accuracy.

No extrapolation, fusion, bias correction or hidden-label fitting is enabled.
The tested extrapolation candidate failed held-out precision checks, and sample
fusion did not demonstrate a consistent gain. Mixing zero PPS with a common
positive multiple of MPS merely rescales the vector and cannot improve Pearson
correlation. Raw direct simulator values remain the candidate outputs.

## Decision loop

1. **Reconcile before launching.** Read saved receipts, account job identities,
   costs, the stop flag and the deadline. Resolve ambiguity before any retry.
2. **Complete the selected cohort.** Reuse completed matching rows, preserve the
   G1 anchor and prioritize missing baseline IDs. Every ID is a separate program;
   another ID's value is never reused as its answer. Required pilots and the G4
   independent-method check remain part of the evidence gate.
3. **Quote and admit the exact action.** Preserve baseline reserves, outstanding
   commitments and the submission buffer. Reject unknown or excessive runtime.
   The serial planner additionally uses observed upper-quartile wall time as a
   floor on the quoted runtime for scheduling and deadline checks.
4. **Record intent, then submit once.** Save `SUBMITTING` with its reservation
   before calling the SDK. Poll the known job ID, persist transitions and actual
   costs, then reconsider the next action. A request timeout is not permission
   to submit again.
5. **Export a complete direct candidate.** Exact complete cohorts take precedence;
   otherwise select the highest completed precision in the eligible primary
   family, then a complete fallback. PPS must retain the selected representation.
   Higher precision is a deterministic selection policy, not a monotonic-error
   claim. Validate against the retained template and save an immutable CSV,
   method note and per-ID job/parameter manifest. Preserve the first complete
   baseline and every complete alternative.
6. **Submit through the official process and record evidence.** Exporting a CSV
   does not upload it. Record the actual uploaded bytes, explanation, attempt
   number and displayed score only when those facts have been observed. G1 is
   user-confirmed; G2-G4 website scores remain unverified while browser access is
   blocked. Candidate files and inferred scores must not be recorded as uploads.

After coverage, the serial scheduler ranks feasible refinement candidates using
problem points per row, within-method and cross-method sensitivity, observed
runtime and quoted cost. Complete-vector shape influence adjusts this ranking.
The denominator `quoted_cost + predicted_seconds/3600` is a scheduling heuristic,
not calibrated expected score gain. Verified official scores may reweight effort
between entire problems by remaining headroom, with a rounding floor; they never
determine individual submitted values. An earlier complete baseline remains
available while further genuine simulator configurations are evaluated.

## CPU and GPU policy

The matched G4 q0 chi32 trial agreed between CPU and GPU within 6.7e-12. GPU
compute took 24.189 seconds versus 48.593 seconds on CPU, but elapsed time was
44.804 versus 55.055 seconds: only **10.25 seconds saved** after queue/request
overhead. The GPU receipt billed **$0.20**, while this CPU receipt billed $0.
This single trial supports retaining CPU for the selected baseline; it does not
establish a general speedup or future prices. See
[reports/gpu_matched_pilot.json](reports/gpu_matched_pilot.json).

GPU remains enabled for supported time-sensitive refinements whose fresh quotes
pass all gates. The serial planner compares feasible CPU/GPU routes outside
baseline coverage, preferring lower quoted cost then shorter quoted runtime.
It enforces 7.5 hours of total GPU time and 45 minutes per rolling hour; unknown
GPU usage blocks that route. Baseline coverage keeps its selected device. The
separate two-slot cohort controller is CPU-only. Exact GPU requests for the
36- and 38-qubit graded instances were rejected for size, so they are not an
available exact shortcut in the saved evidence.

## Operation and recovery

Review the saved state without network access:

```powershell
.venv312\Scripts\python.exe scripts/graded_workflow.py --offline-plan
```

The normal command obtains live quotes and writes a plan without simulating;
`--execute` is required to launch. Offline quotes cannot authorize execution.
After the existing runner has released the lock, a bounded serial invocation is:

```powershell
.venv312\Scripts\python.exe scripts/graded_workflow.py --execute --problems G2 G3 G4 --max-jobs 1
```

The separate two-slot path must pass its independent review and offline tests
before the executor hands over from the serial runner. Its explicit cohort
commands and reconciliation rules are in [docs/COHORT_BATCH.md](docs/COHORT_BATCH.md).
Never run a second controller alongside the current owner, including a second
serial invocation. The serial configuration remains at one active job.

`results/workflow/STOP` blocks new launches and requests cancellation of owned
polled jobs. Cancellation does not prove zero cost or release a commitment.
Wait for terminal status and known actual cost; retain unresolved receipts for
reconciliation. A `SUBMITTING` receipt with no job ID must be matched against
service history before any retry. Do not delete a receipt or lock to force a
launch. The cohort controller can restart with the same cohort to attach to
known IDs, and records any unresolved state when its bounded reconciliation
interval ends.

For an actual verified website submission, use:

```powershell
.venv312\Scripts\python.exe scripts/record_submission.py --problem G2 --attempt ACTUAL_ATTEMPT --csv PATH_TO_UPLOADED.csv --note-file PATH_TO_EXPLANATION.txt --score OBSERVED_SCORE
```

The explanation must state the real device, precision, native representation,
qubit ordering and approximation. The recorder requires supporting executions
for every value. Saved quotes, action receipts, run records and decisions remain
the audit trail; a monitoring heartbeat is not an execution authorization.
