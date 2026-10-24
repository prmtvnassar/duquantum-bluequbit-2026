# Reproduce and submit the sample methods

The original submitted files are already in Git. All three displayed 100/100 on our submission page; a teammate's score must be observed on their own submission page. No API token is needed to read or reproduce these files.

| Problem | CSV | Required explanation | Method used for that submission |
| --- | --- | --- | --- |
| S1 | [attempt-01.csv](../submissions/S1/attempt-01.csv) | [attempt-01.txt](../submissions/S1/attempt-01.txt) | Local Qiskit Aer exact statevector, independent Statevector cross-check. |
| S2 | [attempt-01.csv](../submissions/S2/attempt-01.csv) | [attempt-01.txt](../submissions/S2/attempt-01.txt) | Local Qiskit Aer exact statevector. |
| S3 | [attempt-01.csv](../submissions/S3/attempt-01.csv) | [attempt-01.txt](../submissions/S3/attempt-01.txt) | Independent local coefficient-cutoff PPS, epsilon 0.01, Qiskit optimization level 1, 100,000-term cap. |
| G1 | [exact_values.csv](../problems/04_graded_G1/exact_values.csv) | [method explanation](../submissions/teammates/kevin/G1/submitted-v1.txt) | Kevin's exact BlueQubit CPU vector, matched against all 30 completed jobs; reported 100% score. The explanation was reconstructed from his code, not recovered verbatim from the website. |

In the BlueQubit challenge's Submissions tab, upload the CSV for the matching sample problem, paste its entire explanation into **Briefly explain how you arrived at your answer**, submit once, and verify the displayed score and attempt number. A generated candidate does not count as a recorded website submission until that verification.

To recompute the values instead of using the retained uploads, clone/pull main, install Python 3.12 and run from the repository root:

```powershell
py -3.12 -m venv .venv312
.venv312\Scripts\python.exe -m pip install -r requirements.txt
.venv312\Scripts\python.exe scripts/smoke_test.py
.venv312\Scripts\python.exe scripts/reproduce_samples.py
```

Linux/macOS equivalents use `python3.12 -m venv .venv312` and `.venv312/bin/python`. The final command runs all 50 public programs serially, writes `results/reproduction/S1.csv`, `S2.csv`, `S3.csv` and their explanation files, and reports the difference from the original uploads. It submits **no cloud jobs and spends no BlueQubit credits**. Add `--samples S1` for a small reproduction check. Every execution enters the tracked `runs/` ledger. Repeating the command can reuse valid local cached results and records reuse as an event.

Each ID names a different program. Evaluate Z on the qubit named in the ID, with qubit zero at the rightmost Pauli position. Do not use one sample statevector to answer other IDs.

The original S3 submission is an approximation: 100 is the displayed correlation score, not proof of zero absolute error. The tighter settings selected in [the final workflow](../workflow_final.md) are distinct from the method actually used in the original S3 upload. Use the matching explanation for whichever file you submit.

Submission receipts in this repository describe the original submitter's observed attempts. Do not overwrite those with another account's attempt-1 history; retain a separate account-specific receipt when reporting a teammate's result. Never commit a BlueQubit token or copy one from someone else's environment.
