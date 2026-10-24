# BlueQubit Duke OTOC challenge

The operational entry point is [workflow_final.md](workflow_final.md), with machine-readable settings in [configs/workflow_final.json](configs/workflow_final.json). The final configuration is regenerated from measured sample evidence; graded execution requires its release status to be READY.

## Results and audit trail

Teammates: [sample files, explanations and local reproduction instructions](docs/TEAMMATE_QUICKSTART.md).

The three official sample submissions each display **100/100**, using one attempt per problem and $0 BlueQubit compute cost. Their exact uploaded CSVs, method explanations, score receipts, checksums and supporting run IDs are preserved under [submissions/](submissions/README.md).

Every local/cloud execution attempt is recorded in [runs/jobs.csv](runs/jobs.csv), successful estimates in [runs/estimates.csv](runs/estimates.csv), and scheduling/quotation events in [runs/decisions.csv](runs/decisions.csv). See [runs/README.md](runs/README.md) for recovery and the schema. Graded results are account-specific: the user reports G2 at 342/600 with a 3.48-hour penalty on the original account's first attempt, and 498/600 on a teammate's first attempt using the same file. The reason for the difference is unverified. G4's chi32 candidate received an accepted 0/1000 and must not be resubmitted; G3's baseline is held for numerical review. See [candidate status](submissions/candidates/README.md).

Kevin's [exact G1 vector](problems/04_graded_G1/exact_values.csv), reported to score 100%, is also retained with verified job-ledger provenance. The scheduler reuses it and avoids duplicate G1 runs. Teammate receipts are namespaced under submissions/teammates/.

The measured results and their limitations are in [reports/calibration_evidence.json](reports/calibration_evidence.json) and [reports/sample_benchmarks.json](reports/sample_benchmarks.json). Within-method trends, cross-method differences, actual scores, time and CPU/GPU quotes guide allocation. Official rounded correlation scores are not pointwise error guarantees.

## Setup

Python >=3.11,<3.13 is required; the active local environment is .venv312. From the repository root:

~~~powershell
.\.venv312\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m pip check
python scripts/smoke_test.py
python -m unittest discover -s tests
~~~

The smoke test is offline and does not submit billable jobs. Dependency versions are in [pyproject.toml](pyproject.toml). The BlueQubit SDK reads BLUEQUBIT_API_TOKEN from the environment or an ignored local .env. Credentials never belong in receipts or Git.

## Calibration and graded execution

~~~powershell
python -m bluequbit_samples inspect --data-root problems
python scripts/sync_runs.py
python scripts/run_workflow.py report
python scripts/run_workflow.py tune
python scripts/graded_workflow.py
~~~

The graded command is plan-only: it obtains quotes and records a decision. Add --execute --max-jobs 1 to execute one reviewed action. Every subsequent action gets a fresh quote and account check. Sample spend is restricted to $0; the original $30 graded allowance has a $3 planning reserve, giving a $27 planned exposure ceiling. Recorded SDK job charges are not a fresh wallet balance. Unknown costs, duplicate/ambiguous submissions, missing references, and deadline violations block execution.

The [bounded cohort controller](docs/COHORT_BATCH.md) supports two CPU jobs or one explicitly targeted GPU diagnostic, with full quote reservations and restart reconciliation. Approximate exports require numerical review before upload. The [GPU precision recovery report](reports/GPU%20precision%20recovery.md) explains how the supplied simulator benchmark changes the refinement strategy.

See the final workflow for the decision tree, numerical stopping limitations, method selection, mandatory submission explanations, actual score recording and recovery.

## Repository layout

- [problems/](problems/README.md): all 50 public QASMs, original per-problem archives, checksums, and the 140 published graded IDs. Hidden QASM is unavailable.
- src/bluequbit_samples/: local exact, Quimb MPS, independent coefficient-cutoff PPS, isolated execution and numerical checks.
- src/otoc/: cloud cost gate, adaptive scheduling, calibration, audit ledger and submission validation.
- configs/: reproducible calibration inputs and the final graded policy.
- runs/: tracked execution evidence and readable CSV sheets.
- submissions/: immutable actual website submissions.
- reports/: measured calibration, decision evidence, verification and cleanup inventory.
- docs/history/: superseded design proposals retained for provenance.
- papers/ and research_notes/: background sources for the algorithm.
- bluequbit_samples_exact_mps_pps.ipynb: optional exploration; its OBP total-L1 budget is distinct from the final coefficient-cutoff PPS implementation.

One ID is one separate program. Evaluate Z on its named qubit from |0...0>; q0 is the rightmost Pauli character. Upload one complete circuit_id,value CSV per problem, together with an explanation of the actual method. A prepared export is not an official submission.

Obsolete blank XLSX sheets, old combined-format exporters, duplicate root archives, and stale preparation notes were removed after verification. Their recovery commit and checks are in [reports/repository_cleanup.json](reports/repository_cleanup.json). Editor state, bytecode, build metadata, local environments and bulky raw outputs are ignored. Scientific inputs, research sources, measured receipts and design history are retained.
