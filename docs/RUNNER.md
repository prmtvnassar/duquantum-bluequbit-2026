# Job runner

`scripts/run_jobs.py` submits MPS / Pauli-path (PPS) jobs to BlueQubit and records each
result in the circuit's workbook (`runs/*.xlsx`): one **Jobs** row per job, one
**Estimates** row per qubit result (Accepted = 1). The Qubits/Status formulas and
`scripts/export_submission.py` then work as described in [runs/README.md](../runs/README.md).

## Commands

```bash
# Free rehearsal: exact local simulation with fake approximation error.
# Writes to scratch/offline/ copies only; runs/ is never touched.
python scripts/run_jobs.py sample_1 --setup --offline
python scripts/run_jobs.py sample_1 --method mps --slots 1 2 3 --offline

# Real jobs (credits). Always look at the --dry-run plan first.
python scripts/run_jobs.py sample_1 --method pps --slots 1 --dry-run
python scripts/run_jobs.py sample_1 sample_2 --method mps --slots 1
python scripts/run_jobs.py hidden_2 --method mps --settings 512 --qubits 0 1 2

# After Ctrl-C or a timeout: jobs keep running on BlueQubit; collect them later.
python scripts/run_jobs.py --resume

# Tests (free)
python -m pytest scripts/tests -q
```

- `--slots 1 2 3` reads χ / ε from the workbook's Status sheet, so the values written
  match its formulas. `--settings` takes any value but warns if Status doesn't list it.
- Jobs already accepted in the workbook, or already in the ledger, are skipped (`--force` reruns;
  the old Estimates row is set to Accepted 0, not deleted). Results that are in the ledger but
  missing from the workbook are copied over for free.
- Safety: a confirmation prompt (skip with `--yes`), at most `max_jobs_per_command` jobs per
  command (raise with `--max-jobs`), at most `max_in_flight` jobs queued at once.
- Close a workbook in Excel before running; the runner refuses to write to an open workbook.
  A backup of each workbook is saved to `scratch/workbook_backups/` before each command's first write.
- `runs/ledger.csv` records every job event (text, so it merges in git). It is the cache and the
  resume list. If a workbook is lost or reverted, rerunning the same command copies the results back in.

## What to adjust at kickoff

| Unknown until the kit | Where to change it |
| --- | --- |
| Device names, option names, extra options | `[backend]` in `scripts/runner.toml` |
| Sample circuits (QASM files, butterfly qubit) | set `provider = "qasm"`, `path`, `butterfly` per sample in `scripts/runner.toml` |
| Use the kit's `otoc2_circuit` instead of ours | `echo = "kit"` per circuit; check the call in `kit_echo()` in `scripts/runner/targets.py` |
| Hidden circuit IDs | `official_id`, `circuit_id` (pattern with `{qubit}`) per hidden circuit |
| Which qubits to estimate | `qubits = "all"`, `"workbook"` (Qubits!A6:A165) or a list |
| Measured Pauli / qubit ordering | `[observable]` in `scripts/runner.toml` |
| Qubit labels that aren't plain integers | `qubit_index()` in `scripts/runner/targets.py` |
| Something else entirely (kit hands out circuits differently) | write a new `@provider` in `scripts/runner/targets.py` |
| Workbook layout changes | the layout constants at the top of `scripts/runner/workbook.py` |

Things to confirm with one cheap real job before a big batch:
1. A sample job runs and its estimate is close to the exact value (`scripts/smoke_test.py` checks the token).
2. `expectation_value` is a single number for the observable we send.
3. `cost` and `run_time_ms` come back filled in, so the Jobs sheet's credits column is meaningful.
