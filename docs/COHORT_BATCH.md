# Bounded CPU cohort controller

By default, `scripts/run_cohort_batch.py` completes one explicitly selected G2, G3 or G4
cohort: every retained template ID on one CPU device with identical full native
options. Supported devices are `mps.cpu` and `pauli-path`. It manages at most two
owned jobs under the existing exclusive `remote_runner` lock. It cannot run
alongside the serial executor or another cohort controller.

The serial configuration remains `max_concurrent_jobs: 1`. This separate entry
point requires `--execute`; without it the CLI rejects the request before any
network call. The new controller must pass independent review and the offline
failure/recovery tests before its first live handoff. Documentation is not a
claim that the selected estimates are accurate. The first two-job G4 trial passed
on October 24: both chi32 CPU jobs completed with $0 recorded charges, in 46.44
seconds from the first request to the final receipt. See
[../reports/cpu_concurrency_trial.json](../reports/cpu_concurrency_trial.json).
This is an operational overlap check, not a matched serial benchmark.

## Explicit invocation

After the existing runner has finished and all its jobs and charges are
reconciled, a bounded two-launch G4 command is:

```powershell
.venv312\Scripts\python.exe scripts/run_cohort_batch.py --execute --problem G4 --device mps.cpu --options-file configs/cohorts/mps_chi32.json --reserve-cohorts-file configs/cohorts/baseline_reserves.json --slots 2 --max-jobs 2
```

`--state-root` selects the shared account-state directory and defaults to
`results/workflow`. When running code from another worktree against this existing
account, pass `--state-root D:\BluQubit\results\workflow` to retain its receipts,
cost journal, STOP file, checkpoints and exclusive `remote_runner` lock. Both the
adapter and completed-cohort export read that same state root. Keep every runner
for the same account on the same state directory; this option does not change the
working directory or the code, config and options files being used.

The selected options files are:

| Cohort | Options file | Native options |
| --- | --- | --- |
| G2/G4 CPU MPS | [../configs/cohorts/mps_chi32.json](../configs/cohorts/mps_chi32.json) | `{"mps_bond_dimension":32}` |
| G3 CPU PPS | [../configs/cohorts/pps_epsilon001_level1.json](../configs/cohorts/pps_epsilon001_level1.json) | `{"pauli_path_truncation_threshold":0.001,"pauli_path_circuit_transpilation_level":1}` |

For G2, change the problem to `G2` and retain `mps.cpu` and the MPS options file.
For G3, use `--problem G3 --device pauli-path` and the PPS options file. Keep one
controller at a time. `--slots 1` is supported. `--max-jobs` bounds **new launches
in that invocation**; completed matching rows are reused and known owned jobs
are reconciled before normal exit. Omitting `--max-jobs` permits up to the
problem's retained row count in new launches, still subject to all gates.

The controller requires a `READY` campaign, $0 sample spending, known-cost
stopping and a graded budget no greater than $30. The retained templates supply
all required IDs; no shortened user-defined manifest is accepted by the CLI.
Normal completion invokes the existing coherent exporter from saved receipts.
It does not upload anything to the website, and exported candidates retain
`submitted: false` until an actual official submission is verified separately.

## Explicit targeted diagnostics

An optional diagnostic mode runs only named IDs at one fixed CPU configuration.
It requires `--targeted-diagnostics`, `--target-ids`, `--execution-timeout` and
`--quote-runtime-limit` together. Both limits must be finite numbers within
1–3600 seconds. Targets must be distinct IDs in the selected problem's full
retained template. Diagnostic arguments without the explicit mode are rejected;
ordinary cohort runtime limits remain unchanged.

For example, after prior owned jobs and costs are reconciled, a reviewed G4 chi64
options file containing `{"mps_bond_dimension":64}` can be used for one bounded
diagnostic:

```powershell
.venv312\Scripts\python.exe scripts/run_cohort_batch.py --execute --problem G4 --device mps.cpu --options-file PATH_TO_REVIEWED_CHI64.json --reserve-cohorts-file configs/cohorts/baseline_reserves.json --slots 1 --max-jobs 1 --targeted-diagnostics --target-ids Duke_G4_0 --execution-timeout 600 --quote-runtime-limit 2000 --diagnostic-reason "Bounded G4 chi64 sensitivity diagnostic; accuracy unverified"
```

Here a fresh runtime quote of 1878 seconds can pass the 2000-second quote limit.
The controller requests cancellation at the first poll reaching 600 seconds
from the saved request time. Cancellation is a service request, not a guarantee
of immediate termination or a billing cap. The full fresh dollar quote remains
reserved; a shorter execution cap never discounts it. Deadline admission retains
`max(quoted runtime, execution timeout) + submission buffer`, so this example
still needs at least 1878 seconds plus the configured buffer.

Targeting does **not** shorten any coverage or export manifest. Missing baseline
coverage is reserved across every retained ID unless a valid complete nonconstant
older vector already exists. Active and new diagnostics always reserve their full
quotes. CPU-only execution, two slots at most, the `READY` requirement, the $27
planned ceiling and all unknown-cost, ambiguity and foreign-job gates still apply.
An unresolved same-configuration job outside the requested target set is foreign
to this diagnostic invocation and blocks new launches.

Successful completion and cost reconciliation of every requested target returns
`DIAGNOSTICS_COMPLETE`, even when the full cohort remains incomplete. Diagnostic
mode never invokes the exporter, including when a full vector happens to exist.
It does not submit anything to the website. `--max-jobs` still bounds new launches;
if that bound prevents finishing the requested set, the controller drains its jobs
and reports `BOUNDED_STOP`. Known target job IDs are resumed and completed targets
are reused. A saved stricter execution cap is preserved on resume. Canceled or
failed targets remain recorded and block automatic retry; they do not count as
successful diagnostic completion.

The selected targets, both caps, mode and diagnostic reason are recorded in each
new receipt, cohort checkpoint and monitor status. `--diagnostic-reason` supplies
a specific rationale; if omitted, the controller records its bounded-diagnostic
purpose explicitly. Full-cohort and target completion counts are reported separately.

## Admission and budget accounting

Before **each** launch, the controller obtains a fresh quote for that ID and full
configuration, then fresh account usage and job identities. Sequential admissions
observe the receipt reservation from the preceding launch, even if the account
index has not yet listed that job. The current admission inequality is:

```text
known actual charges
+ outstanding quoted commitments
+ the proposed job's fresh quote
+ reserves for missing, unreserved selected baseline rows
<= $30 * (1 - 0.10) = $27
```

Known charges are retained by job ID in a durable account-cost journal, using
per-ID maxima from account observations and current-account receipts. This
prevents a restart or lagging account index from forgetting a recorded charge;
teammate-account imports are not added to current-account spending. Terminal
charge evidence is persisted before its quote reservation can be released.
Missing or inconsistent cost breakdowns block new launches. Every outstanding
action still needs a known quote, including a terminal action whose actual cost
is unknown. Cancellation does not release a reservation. Prior $0 bills never
discount outstanding or new quotes. Quotes are nonbinding estimates, so the $3
cushion reduces exposure but cannot guarantee that actual billing will stay below
the planned amount.

Reserve cohorts for all G2-G4 problems are frozen at startup from the effective
selected policies. The explicitly requested target cohort overrides its own
entry. `--reserve-cohorts-file` can supply the complete three-problem mapping;
[../configs/cohorts/baseline_reserves.json](../configs/cohorts/baseline_reserves.json)
records the current choices. Partial mappings and unsupported devices fail.

Rates use quote evidence matching the problem, device and **every option**.
Current selected-cohort evidence supports $0.30 per G2 row, $0.20 per G3 row and
$0.27 per G4 row. The controller retains the largest matching saved quote and
obtains a representative quote for each cohort with missing coverage at startup,
then refreshes it after five minutes. New evidence can raise, but does not lower,
the retained reserve rate. Each proposed launch is separately freshly quoted.
It never assumes that a different
configuration will cost $0.20 or that every row has a binding fixed price.
Completed matching rows and already reserved pending rows are not charged a
second future-coverage reserve.

A valid complete nonconstant coherent vector preserves a usable older baseline
for its problem. If one exists, future rows in a refinement cohort need no
full-vector coverage reserve: the older vector survives an unfinished refinement.
This exemption requires a complete candidate on the full retained template,
valid finite values and known costs, and range above the configured signal floor.
Partial or flat cohorts do not qualify. **Every active or newly launched
refinement still reserves its quoted cost**, and incomplete refinements are never
exported as a mixture with the older baseline.

In ordinary cohort mode, the target quote must fit the runtime cap: 900 seconds for CPU MPS chi32 and
600 seconds for ordinary remote jobs. Admission also leaves the full applicable
timeout plus the 20-minute submission buffer before the configured deadline.
Owned pending IDs, including jobs not yet indexed by the account, count toward
the two-slot ceiling and the account's five-job limit. The account-wide 800-job
policy also applies. GPU is unsupported by this controller.

## Failure, cancellation and restart

New launches fail closed for unknown or invalid costs or quotes, foreign active
jobs, foreign unresolved local receipts, unrecognized active-job identities,
account-count inconsistencies, ambiguous `SUBMITTING` intents without job IDs,
and unreconciled terminal costs or failures. Existing owned jobs are polled while
new launches are blocked. An SDK error is not permission to retry submission.

Each action's `SUBMITTING` receipt includes its quote and admission calculation
**before** the API call. The adapter writes the canonical audit at each transition.
If a call fails after submission may have occurred, its saved intent remains
untouched. Reconcile it against service history before any new launch; do not
remove receipts or locks to force a retry. A restart with the same full cohort
attaches to known job IDs and resumes polling. Failed actions remain recorded
and require review rather than automatic resubmission.

`results/workflow/STOP` prevents launches and requests cancellation of owned jobs.
A timeout does the same for the affected job. The cancellation request is still
attempted when reading a nonterminal owned job fails. The controller polls for
terminal status and actual cost. If cancellation, service reconciliation or cost ambiguity
persists beyond the bounded reconciliation interval, it exits with an explicit
blocked state and retains the reservation. Resume the same cohort only after
resolving the recorded condition; do not start a second process to recover it.

## Review and monitoring records

Before first live use, review the controller alongside
`tests/test_cohort_batch.py` for simultaneous commitments, account-index lag,
durable costs across restart, reserve-quote freshness, full-cohort reserve pricing,
the older-baseline exemption, foreign/ambiguous state and cancellation during
lookup failures. The independent review and offline test results
are release evidence; successful documentation edits alone do not establish them.
Targeted-diagnostic tests also cover explicit-mode validation, unchanged ordinary
runtime limits, full-manifest reserves, separated runtime caps, deadline buffers,
timeout cancellation, reuse/failure behavior and suppressed partial export.

Each invocation writes `results/workflow/cohort_batches/<cohort-key>.json` with
the selected cohort, reserve cohorts/rates, latest admission calculation, owned
pending IDs, row counts and explicit blockage reason. The monitor-facing
`results/workflow/batch_status.json` exposes owned IDs/statuses, completed and
required rows, the last progress timestamp and blockage reason. Action receipts,
`runs/records` and ledger entries remain the per-job audit.
`results/workflow/cohort_accounting.json` retains account-scoped per-job costs
and a monotonic spent floor across restarts. Exception type names
are retained without exception bodies or raw SDK responses.

A `COMPLETE` status means that a fixed direct cohort is complete. It does not mean
convergence, a confirmed upload or a verified official score. Scientific selection
and submission evidence remain governed by
[../workflow_final.md](../workflow_final.md) and
[../reports/GRADED_CAMPAIGN.md](../reports/GRADED_CAMPAIGN.md).
