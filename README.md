# BlueQubit Duke OTOC challenge

**This checkout's execution is paused as of October 24, 2026.** The user requested no further runs from this workflow while teammates continue their own G4 investigation. The repository preserves the computations, submission files, scores, and reasoning collected so far.

## Start here

- [Current workflow](docs/workflow.md): how to reuse evidence, choose informative refinements, judge convergence, and account for time and cost if the campaign resumes.
- [Results and score audit](docs/results.md): every attributed submission claim, exact CSV hashes, branch coverage, and unresolved score evidence.
- [Optimization decisions](docs/optimization-decisions.md): what each experiment tested and how the measured outcome changed the next decision.
- [LaTeX write-up](writeup/main.tex) and [G3 figure](writeup/figures/g3_precision.png): the scientific explanation for the campaign.
- [LaTeX presentation](writeup/slides/main.tex), [speaker notes](writeup/slides/speaker_notes.md), and [presentation guide](writeup/presentation.md): the seven-minute talk, four-minute video cut, and offline evidence check.
- [Sample reproduction guide](docs/TEAMMATE_QUICKSTART.md): the three original sample CSVs, explanations, and offline reproduction steps.

The highest repository-reported G2 score is **581/600**, recorded in commit `cf7689f` for the [q30 refinement CSV](submissions/candidates/G2/G2_1_mps2048_22_mps512_13_mps128.csv). Its [feedback record](submissions/candidates/G2/G2_1_mps2048_22_mps512_13_mps128.feedback.json) distinguishes this commit-message claim from a website receipt. The account, attempt, time penalty and source jobs remain unknown. The earlier 579/600 and 580/600 hybrids remain as evolution milestones. Kevin's chi128 498/600 has account-attributed job provenance; the original account reported 342/600 with a 3.48-hour penalty.

Kevin's documented G3 refinement improved from **534/800** to **773/800** at a tighter Pauli-path threshold. G4's MPS bond-dimension-32 candidate received a user-reported accepted **0/1000**; Kevin later reported **133/1000** with PPS. The three sample attempts each displayed **100/100**. These results belong to different or unidentified accounts and cannot be added into one official total; see the [audit](docs/results.md) for attribution and evidence limits.

## Repository map

| Location | Purpose |
| --- | --- |
| [submissions/](submissions/README.md) | Submitted bytes, explanations, account-specific receipts, and candidate feedback |
| [runs/](runs/README.md) | Append-only execution events, row receipts, and CSV job, estimate, decision, and submission indexes |
| [problems/](problems/README.md) | Public sample QASM, problem templates, graded IDs, and checksums |
| [reports/](reports/README.md) | Machine-readable evidence, audit records, and dated reviews |
| [src/](src/) and [scripts/](scripts/) | Local simulation, validation, scheduling, and record-keeping code |
| [configs/](configs/) | Campaign settings and resource gates |
| [docs/history/](docs/history/) | Superseded designs retained for traceability |

Python 3.11 or 3.12 is required. [pyproject.toml](pyproject.toml) lists the dependencies. The offline import smoke test is:

~~~powershell
py -3.12 -m venv .venv312
.venv312\Scripts\python.exe -m pip install -e .
.venv312\Scripts\python.exe scripts/smoke_test.py
~~~

The smoke test does not submit a BlueQubit job. Credentials belong only in the environment or an ignored local .env file. [workflow_final.md](workflow_final.md) remains as a compatibility link for older references; [docs/workflow.md](docs/workflow.md) is the active decision procedure.
