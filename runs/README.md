# Runs and decisions

This directory is the canonical **tracked** audit trail. Open the CSVs in a spreadsheet or read them from an agent. The old blank XLSX templates and the old combined-submission schema have been retired.

| File | Meaning |
| --- | --- |
| `jobs.csv` | One row per actual local or BlueQubit execution attempt, including unsuccessful and unfinished attempts. |
| `estimates.csv` | Successful, finite estimates joined to the same run ID. No fabricated values for incomplete simulations. |
| `decisions.csv` | Timestamped events: execution states, quotes, cost blocks, scheduling reasons, cache reuse and exports. `details_json` preserves structured evidence. |
| `submissions.csv` | Index of saved submission claims, including browser-observed and user/teammate-reported uploads. Unknown account, attempt, score and upload identity stay blank. `receipt_path` points to the authoritative evidence. Unsubmitted candidates are excluded. |
| `records/*.json` | Detailed receipt for each attempt, including parameters, backend, input/source hashes, diagnostics, timings and actual cost when known. |
| `events/*.json` | Durable events underlying the CSV view; an event ID identifies one observation. |
| `experiments/*.json` | Immutable calibration index, restored into the local cache on a fresh checkout. Cloud receipts similarly restore submitted-job identities so a new checkout does not silently resubmit them. |
| `reconciliation.json` | Last reconciliation against every persisted worker request and cloud-action receipt. |

An execution writes a RUNNING/SUBMITTING receipt **before** launching. Completion, resource limits, cancellation and errors update the same attempt. Separate attempts stay separate even if their input/precision match. Cache hits and quotations are events, not billable executions. A remote submission interrupted before its job ID is known remains uncertain and cannot be automatically resubmitted.

Historical attempts were backfilled from `results/**/attempts/*/request.json` and their terminal receipts, plus `results/workflow/remote_actions/*.json`. A request without a terminal receipt is explicitly unresolved; it is never promoted to success. Initial historical start times come from request-file timestamps. Earlier quote files may contain only their last observation; they are not executions.

```powershell
.venv312\Scripts\python.exe scripts/sync_runs.py
```

Use this after recovery and before committing. It is idempotent and rebuilds the CSV views without duplicating executions. Historical raw outputs remain in ignored `results/`; compact receipts and submitted bytes are tracked. No credentials or full environment dumps belong here.

To refresh only the submission index from repository receipts, without reading account
credentials or contacting BlueQubit, run `python scripts/rebuild_submission_index.py`
in the project environment. `sha256` identifies the retained local CSV; it does not
by itself prove those bytes were uploaded. A blank `displayed_score` is unknown, not
zero. `evidence_source` describes the upload claim; `score_evidence_source`,
`score_evidence_path` and `score_evidence_commit` identify where a reported score
came from when that differs.
The corresponding JSON receipt records how the claim was obtained.

Close a CSV in Excel if it holds an exclusive write lock. The workflow fails closed if it cannot update the ledger. Atomic replacement and a process lock serialize local and remote writers. Do not hand-edit the generated CSVs; make a correction through its source receipt and retain an explicit event explaining it.

Unit tests and lightweight import/numerical smoke checks are validation, not challenge simulation jobs. Their outcomes are recorded in the repository validation report. Any challenge simulator invocation through `execute()` or the BlueQubit adapter is logged automatically, including local resource-cap failures.

Submission payload consolidation is recorded in [submissions/retention.json](../submissions/retention.json). Original receipts keep their path strings and hashes. The derived submission index and archival retries resolve only byte-identical aliases, retaining distinct accounts and attempts without recreating duplicate CSVs. Numerically equal but differently serialized files are recoverable from their recorded Git blobs; they are not interchangeable upload bytes.
