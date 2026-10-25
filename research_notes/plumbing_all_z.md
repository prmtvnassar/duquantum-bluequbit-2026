# all_z plumbing: one MPS job, every single-site <Z_j> (2026-10-24, offline-tested only)

## What changed
- `src/otoc/bluequbit_adapter.py`: `observable_pauli_sums()`; `quote()` and `run()` take
  `observables=None|"all_z"`. `all_z` is accepted on `mps.cpu`/`mps.gpu` only (the SDK's
  `_validate_pps_job` rejects >1 observable on pauli-path; cpu/gpu are refused here too).
  Single-observable calls are unchanged: same `pauli_sum=[(z,1.0)]`, same action, same keys.
- `src/otoc/ledger.py::record_remote`: scalar `estimate` stays `<Z_q>`; `estimates_vector`
  and `observables` go into `runs/records/remote-*.json` only; `reason` is prefixed with
  `observables=all_z job; ...`. `jobs.csv`/`estimates.csv` columns are unchanged.
- `src/otoc/cohort_batch.py`: quotes carrying `observables` are ignored for row reserve rates.
- `scripts/bluequbit_control.py --observables all_z`; new `scripts/run_feature_jobs.py`;
  offline tests in `tests/test_all_z_observables.py` plus one cohort-controller test.

## Receipt schema (`results/workflow/remote_actions/<key>.json`, mirrored in the ledger)
```
action: {circuit_id, device, options, pauli: <Z_q string, q0 rightmost>, observables: "all_z"}
key = sha256(sorted JSON of action)           # differs from the single-<Z_q> receipt
status, requested_at, quote{..., observables:"all_z", observable_count:n}, scheduler_justification
job_id, cost_usd, compute_ms, queue_ms, updated_at
estimate          = estimates_vector[q]      # float, same gate as before: finite, |x| <= 1
estimates_vector  = [<Z_0>, <Z_1>, ..., <Z_{n-1}>]   # list index j == qubit j
observables_count = n
```
Pauli sum sent (quote and run, identical): `[[("I"*(n-1-j)+"Z"+"I"*j, 1.0)] for j in range(n)]`.
If the service returns anything other than a list of n finite numbers the receipt becomes
`INVALID_RESULT` with the raw value kept under `estimates_vector` and `estimate = null`.

## Grouping by existing readers (all read the scalar; none crash on the new keys)
- `coherent_selection.select_coherent_vector` and `graded.select_record/valid`: an all_z
  COMPLETED receipt is grouped **into the same device/options cohort** as single-<Z_q> rows
  (per-ID duplicates resolve to the latest timestamp). Acceptable: same MPS, same `<Z_q>`.
- `cohort_batch`: `_matches` also groups it (owned/pending/coverage counts include it), but
  `_next_action` keys on the single-observable action, so a cohort run at the same options
  would still launch the plain `<Z_q>` job for that ID. Unresolved all_z receipts block the
  controller exactly like any other unresolved receipt of that cohort.

## Smoke test first (cheap chi16 G4 row, one job, under the usual gates)
```powershell
$env:PYTHONPATH="src"
.venv312\Scripts\python.exe scripts\bluequbit_control.py quote --id Duke_G4_0 --device mps.cpu --options '{"mps_bond_dimension": 16}' --observables all_z
.venv312\Scripts\python.exe scripts\bluequbit_control.py run --id Duke_G4_0 --device mps.cpu --options '{"mps_bond_dimension": 16}' --observables all_z --config configs/workflow_final.json --timeout 600 --justification "all_z smoke test: verify expectation_value list shape and order"
```
Check the printed receipt: `estimates_vector` has 38 entries, `estimate == estimates_vector[0]`,
and `estimates_vector[0]` agrees with the existing single-observable chi16 `Duke_G4_0` value.
Compare a second component against another existing chi16 row to confirm the index order.

## G4 all-Z feature jobs (chi32, serial, resumable; skips IDs with a COMPLETED all_z receipt)
```powershell
.venv312\Scripts\python.exe scripts\run_feature_jobs.py --execute --problem G4 --device mps.cpu --options-file configs/cohorts/mps_chi32.json --observables all_z --ids 0 1 2 3 --timeout 900 --justification "G4 all-Z chi32 feature vectors for the local estimator" --log results/workflow/feature_jobs_g4_chi32.jsonl
```
Stops with exit 1 at the first BLOCKED_*/CANCELED/INVALID_RESULT/unknown-cost outcome; honours `results/workflow/STOP` between jobs; needs the sole `remote_runner` lock.

## Not verifiable offline
- The wire shape of `expectation_value` for a list of sums: the SDK only annotates it
  `float | list[float]` and never reorders it; order == request order is assumed and
  the adapter validates length/finiteness. The smoke test above settles it.
- Whether an all_z MPS quote costs/runs the same as a single-<Z_q> job (likely close: one
  MPS build, n cheap contractions), so quote before committing the 38-row loop.
