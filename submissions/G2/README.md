# G2: from a complete baseline to selective precision

The saved G2 records show how the team increased MPS precision. The scores below come from different or unidentified accounts, so their sequence describes the files and reports rather than a controlled score trajectory.

| Stage | Result and files | Decision or open question |
| --- | --- | --- |
| Complete MPS $\chi=32$ baseline | Original account: [342/600 CSV](attempt-01.csv), [explanation](attempt-01.txt), [receipt](attempt-01.json). First attempt; reported time penalty 3.48 hours. | A complete baseline was available, but later row checks found sensitivity near transitions. |
| Complete MPS $\chi=128$ | A teammate: [498/600 CSV](../teammates/teammate-1/G2/submitted-v1.csv), [explanation](../teammates/teammate-1/G2/submitted-v1.txt), [receipt](../teammates/teammate-1/G2/submitted-v1.json). | All 36 values have attributed job records. This is the highest G2 score with that level of account and row provenance. |
| Mixed $\chi=512/64$ | [CSV](../candidates/G2/G2_23_512_and_13_64.csv), [score note](../candidates/G2/G2_23_512_and_13_64.score-report.txt), [feedback](../candidates/G2/G2_23_512_and_13_64.feedback.json): **579/600** reported in repository text; user confirmed submission. | The note describes 23 refined rows and 13 baseline rows. The account and per-row source jobs are unknown. |
| Later mixed $\chi=512/128$ filename claim | [CSV](../candidates/G2/G2_23_512_and_13_128.csv), [feedback](../candidates/G2/G2_23_512_and_13_128.feedback.json): **580/600** reported by commit `e0ca909`. | Twenty-three saved values match the preceding CSV; 13 change. The filename does not establish their source jobs. The account, official attempt, and website score receipt are unavailable. |
| q30 refinement in a further mixed file | [CSV](../candidates/G2/G2_1_mps2048_22_mps512_13_mps128.csv), [feedback](../candidates/G2/G2_1_mps2048_22_mps512_13_mps128.feedback.json): **581/600** reported by commit `cf7689f`. | Only q30 changes from the 580 file, from 0.085805 to -0.022471. The claimed $\chi=2048$ source job, account, official attempt, and website score receipt are unavailable. |

An [older unnamed-teammate receipt](../teammates/teammate_reported/G2/attempt-01.json) reports 498/600 for bytes identical to the original account's $\chi=32$ file. Its attribution conflicts with the later account-specific evidence and remains disputed. Its duplicate CSV and explanation were removed; the distinct claim was retained.

The mixed vectors suggest where rowwise precision might help. The available records do not establish why the 23 rows were chosen or whether either one-point difference came from the changed values. [The decision history](../../docs/optimization-decisions.md) describes the diagnostics and resource limits in more detail.
