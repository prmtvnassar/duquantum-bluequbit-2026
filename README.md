# BlueQubit Duke OTOC challenge

The [released challenge](https://app.bluequbit.io/hackathons/2GMaAenu3iSsIC6Z?tab=problems) has seven problems: three open samples (S1–S3) and four graded circuits (G1–G4). [Problem folders](problems/README.md) contain all 50 downloadable sample QASM files and published ID lists for all 190 observables. The 140 graded circuit IDs are accessible **by ID only** through BlueQubit; their QASM is not published.

The earlier [estimation workflow](estimation_workflow_v0.md) is a pre-release algorithm design. Its assumed sample count, kit interface, and combined `circuit,qubit,estimate` submission format have been superseded by the released page. Use it for simulation and scheduling ideas, not for submission instructions.

## Python setup

The project requires Python `>=3.11,<3.13`. A Python 3.12 environment is available at `.venv312/` alongside the older Python 3.13 `.venv/`. From the repository root:

```powershell
.\.venv312\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m pip check
python -m unittest discover -s tests
```

The exact Qiskit, Aer, Quimb, and Qiskit add-on versions are in [pyproject.toml](pyproject.toml), along with the released BlueQubit SDK requirement `bluequbit>=0.19.0b1`. The SDK reads `BLUEQUBIT_API_TOKEN` from the environment; `otoc.config.get_client()` can load a local ignored `.env`. Never put tokens in run records or submissions.

## Circuits and submissions

Each problem has one circuit ID per qubit, `Duke_<problem>_<q>`. Each ID is a separate QASM program. For a result, take the expectation of Z on qubit `q`, where `q0` is the rightmost character of the SDK Pauli string. The three sample sets may be simulated locally from the downloaded QASM. The graded IDs must be run on BlueQubit. The preparation and export scripts do not submit jobs; `scripts/smoke_test.py` does when invoked.

The released upload is **one `circuit_id,value` CSV per problem**, with every published ID and a finite value. Fill the gitignored `selected.csv` in that problem folder, then validate and export it:

```powershell
python scripts/export_problem_submission.py --problem S1 --check-only
python scripts/export_problem_submission.py --problem S1 --baseline
```

The exporter writes `submissions/S1.csv`; `--baseline` also protects `data/checkpoints/S1_baseline.csv` against replacement. Repeat for each problem. The page permits up to 20 submissions per problem and keeps the best score. Its score is squared positive Pearson correlation times the problem's points; a negative correlation or constant vector scores zero.

The six `.xlsx` workbooks, `runs/csv/` records, and `scripts/export_submission.py` remain as **pre-release** planning artifacts. Their old combined CSV format must not be uploaded to the released challenge.
