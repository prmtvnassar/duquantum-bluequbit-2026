# Released Duke OTOC problems

Source: [BlueQubit problems page](https://app.bluequbit.io/hackathons/2GMaAenu3iSsIC6Z?tab=problems), released October 24, 2026.

| Problem | Kind | IDs | Points | Circuit access |
| --- | --- | ---: | ---: | --- |
| [S1](01_sample_S1/) | Sample | 4 | 100 | QASM downloaded; also run by ID |
| [S2](02_sample_S2/) | Sample | 16 | 100 | QASM downloaded; also run by ID |
| [S3](03_sample_S3/) | Sample | 30 | 100 | QASM downloaded; also run by ID |
| [G1](04_graded_G1/) | Graded | 30 | 300 | Run by ID only |
| [G2](05_graded_G2/) | Graded | 36 | 600 | Run by ID only |
| [G3](06_graded_G3/) | Graded | 36 | 800 | Run by ID only |
| [G4](07_graded_G4/) | Graded | 38 | 1,000 | Run by ID only |

Each folder contains the published `Duke_<problem>_<qubit>` IDs and a local blank `circuit_id,value` submission template. The three sample folders also contain their original ZIP and extracted QASM files, one per ID. The four graded circuits have no downloadable gate sequences; the official page says to run each ID through BlueQubit. `selected.csv` is a gitignored working copy for estimates.

The official upload is **one CSV per problem**, with `circuit_id,value` rows. Use `scripts/export_problem_submission.py` to validate selected values and write a per-problem file. The earlier `circuit,qubit,estimate` exporter and six workbooks in `runs/` are pre-release planning tools and do not match this released upload format.
