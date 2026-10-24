# Results and submission evidence

This is an audit of saved evidence, not a new execution or upload. The branch-wide audit covers main through `580776259bf3752bc55e152e1d4a73214960ba1c` and Kevin's branch at `ea163ebbd72db274f9dad56b48e3b45f48bf36fa`. A later main commit, `030518fc3d7a6256d9cdd276dfdf208eb655fe83`, adds a G2 score claim. The [machine-readable inventory](../reports/audit/branch-score-inventory.json) records the audit and this later claim separately.

Commit `e0ca909` later adds [G2_23_512_and_13_128.csv](../submissions/candidates/G2/G2_23_512_and_13_128.csv) with the message "G2 with 580/600". This is the highest repository-reported G2 score. Comparing saved vectors shows 23 values unchanged from the 579 file and 13 changed. The filename claims a chi512/chi128 mix; source jobs, submitting account, attempt, penalty and website verification remain unavailable. The [feedback record](../submissions/candidates/G2/G2_23_512_and_13_128.feedback.json) preserves these limits. The two reports do not establish a controlled one-point improvement.

The earlier mixed chi512/chi64 vector has a reported **579/600 (96.5%)**. That score appears in [repository text](../submissions/candidates/G2/G2_23_512_and_13_64.score-report.txt), not a saved website receipt; the user separately confirmed the CSV was submitted. The submitting account remains unknown. Kevin's chi128 **498/600** has a stronger, account-attributed scored receipt. Kevin's best documented G3 result is **773/800** at Pauli-path epsilon 0.0003, transpilation level 1.

The current checkout retains one CSV per distinct numerical vector. The [curated submission index](../submissions/README.md) separates best/latest results from framework milestones. [The retention manifest](../submissions/retention.json) maps removed duplicate paths to retained files and exact Git recovery sources. Historical paths and hashes below describe the audited snapshots; the original G3 candidate is numerically equivalent to Kevin's v2 but has distinct serialized bytes preserved in Git. All account receipts and candidate decision manifests remain.

## Highest reported result for each problem

These are results across collaborators. They are **not one account's official total**. Percentages are points divided by maximum points, not certified numerical accuracy.

| Problem | Highest reported score | Percentage | Attributed account | Evidence and exact CSV |
| --- | ---: | ---: | --- | --- |
| S1 | 100/100 | 100% | `original_submitter` | Saved browser-observed receipt; [attempt-01.csv](../submissions/S1/attempt-01.csv) |
| S2 | 100/100 | 100% | `original_submitter` | Saved browser-observed receipt; [attempt-01.csv](../submissions/S2/attempt-01.csv) |
| S3 | 100/100 | 100% | `original_submitter` | Saved browser-observed receipt; [attempt-01.csv](../submissions/S3/attempt-01.csv) |
| G1 | Reported 100%, equivalent to 300/300 | 100% | Kevin | Teammate report; [submitted-v1.csv](../submissions/teammates/kevin/G1/submitted-v1.csv) |
| G2 | 580/600 from a commit message | 96.667% | Unknown | [CSV](../submissions/candidates/G2/G2_23_512_and_13_128.csv) and [feedback](../submissions/candidates/G2/G2_23_512_and_13_128.feedback.json); Kevin's chi128 498/600 has account-attributed job provenance. |
| G3 | 773/800 | 96.625% | Kevin | Teammate report; [submitted-v3.csv](../submissions/teammates/kevin/G3/submitted-v3.csv) |
| G4 | Accepted 0/1000 | 0% | Unknown | User report; [feedback](../submissions/candidates/G4/direct-930f7e5b7d14.feedback.json) for [chi32 CSV](../submissions/candidates/G4/direct-930f7e5b7d14.csv) |

For the original account, the supported numeric results are S1–S3 at 100 each and G2 at 342/600. Its G1 submission is confirmed but its score and exact uploaded bytes are unknown; its archived G3 baseline is unsubmitted. G4's zero has no established account attribution. Kevin's documented per-problem bests are G1 100%, G2 498/600 and G3 773/800. No complete account total or time-penalty total is established.

## All retained graded submission claims

| Problem / record | Account | Score | Method | Attempt / time penalty | Evidence |
| --- | --- | ---: | --- | --- | --- |
| G1, original confirmation | `original_submitter` | Unknown | Expected source is Kevin's exact CPU vector; uploaded bytes unverified | Both unknown | [User confirmation](../submissions/G1/user-reported-submission.json), main lines 3–11 |
| G1, Kevin v1 | Kevin | Reported 100% | Exact CPU statevector; all 30 IDs | Both unknown | [Receipt](../submissions/teammates/kevin/G1/submitted-v1.json), main lines 2–14; original source `9714dab` |
| G2, original attempt 1 | `original_submitter` | 342/600 (57%) | CPU MPS chi32; all 36 IDs | Attempt 1; **3.48 hours** reported | [Receipt](../submissions/G2/attempt-01.json), main lines 2–19 |
| G2, older unnamed teammate report | `teammate_reported` | 498/600 (83%), **attribution disputed** | Receipt points to the same chi32 bytes as the original account | Attempt 1 reported; penalty unknown | [Historical receipt](../submissions/teammates/teammate_reported/G2/attempt-01.json), main lines 2–18 |
| G2, Kevin v1 | Kevin | 498/600 (83%) | CPU MPS chi128; all 36 IDs | Both unknown | [Receipt](../submissions/teammates/kevin/G2/submitted-v1.json), main lines 2–15 and 343 |
| G2, new mixed-precision CSV | Unknown; Git upload authored by `xubrandonTECH` | **579/600 (96.5%), repository text claim** | Source text says 23 GPU MPS chi512 values plus 13 MPS chi64 values | Both unknown | User confirms submission; [CSV](../submissions/candidates/G2/G2_23_512_and_13_64.csv) entered at `5807762`, and [score text](../submissions/candidates/G2/G2_23_512_and_13_64.score-report.txt) entered at `030518f` |
| G2, later mixed-precision CSV | Unknown | 580/600, commit-message claim | Filename claims 23 chi512 and 13 chi128 values | Both unknown | `e0ca909`; [feedback](../submissions/candidates/G2/G2_23_512_and_13_128.feedback.json) |
| G3, Kevin v2 | Kevin | 534/800 (66.75%) | Pauli-path epsilon 0.001, transpilation level 1; all 36 IDs | Both unknown | [Receipt](../submissions/teammates/kevin/G3/submitted-v2.json), main lines 2–15 |
| G3, Kevin v3 | Kevin | 773/800 (96.625%) | Pauli-path epsilon 0.0003, transpilation level 1; all 36 IDs | Both unknown | [Receipt](../submissions/teammates/kevin/G3/submitted-v3.json), main lines 2–15 |
| G4, chi32 candidate feedback | Unknown | Accepted 0/1000 | CPU MPS chi32; all 38 IDs | Both unknown | [Feedback](../submissions/candidates/G4/direct-930f7e5b7d14.feedback.json), main lines 2–15 |

`v1`, `v2` and `v3` are filenames, not verified official attempt numbers. Recorded evidence timestamps are not necessarily upload timestamps. The three sample records each identify attempt 1; no sample penalty is recorded. Only G2's original-account record supplies a penalty. Kevin's G3 v3 receipt rounds its fraction to 0.9663; the exact fraction of the reported points is 773/800 = 0.96625.

The chi512/chi64 G2 file is a submission according to the user even though it is stored under `submissions/candidates/`. Its [feedback record](../submissions/candidates/G2/G2_23_512_and_13_64.feedback.json) preserves the submission confirmation and the later 579/600 repository text claim. Commit `5807762` adds the CSV; `030518f` adds the score text. No website score receipt, uploading-account identity, official attempt number, penalty, exact-uploaded-bytes verification or per-row job/configuration mapping accompanies the claim. No matching values were found in the examined `D:/BluQubit` runtime receipt collections. A Git author is not proof of the BlueQubit account owner.

## G2 attribution correction

The original chi32 file has hash `4cb0c3c1…` and a user-reported 342/600. The older unnamed-teammate receipt attaches 498/600 to those same bytes. Kevin's later receipt explicitly says **his 498/600 belongs to the different chi128 file, hash `a92e6e44…`**. Its 36 values and settings match his completed job ledger.

The best specifically attributed numeric G2 result remains Kevin's chi128 submission at 498/600. The earlier mixed vector reports 579/600 and the later variant reports 580/600, with an unknown account and weaker repository text evidence. The older unnamed-account report is retained as conflicting evidence. It is not silently reassigned to Kevin or deleted. No evidence establishes that a penalty or account-dependent scoring explains a same-file score difference.

The correction is in `2a3eb2b:submissions/teammates/kevin/G2/submitted-v1.json`, line 343, and `2a3eb2b:submissions/teammates/kevin/README.md`, line 46. The historical report is in `30990c5:submissions/teammates/teammate_reported/G2/attempt-01.json`, line 8.

## Exact bytes and methods

Hashes below were recomputed from immutable Git blobs. Matching numbers do not imply matching upload bytes or the same submitting account.

| CSV / vector | SHA256 | Method |
| --- | --- | --- |
| S1 attempt 1 | `482778c0611ee0c9f4f0d11e63b9ff6d636da99be9e8cc91f124bab0471bc320` | Local double-precision exact statevector, 4 IDs; independently cross-checked |
| S2 attempt 1 | `dcb2666e0b37da0b1240edcd35a34398c6b3baa9c0e087875baf1a43d77ce82b` | Local double-precision exact statevector, 16 IDs |
| S3 attempt 1 | `92d1cae4a7ebf436a367aee1f7403d72c7fcda06a0020011d59dba402a9950a2` | Local coefficient-cutoff Pauli propagation, threshold 0.01, optimization level 1; 30 IDs; independent implementation |
| Kevin G1 v1 / `problems/04_graded_G1/exact_values.csv` | `d6bbdea66362f95c58a6b4b06290f7b449636c9d4967fe9231c1fcacd003c6e2` | Exact BlueQubit CPU statevector |
| G2 original chi32 / older unnamed teammate file / candidate `direct-3643218316ac` | `4cb0c3c141640461732583a3e719058f8b731699f55078631d55f3eb0a3c79ea` | CPU MPS chi32 |
| Kevin G2 v1 / `mps_chi128_values.csv` on Kevin's branch | `a92e6e44ef9d12d1272d8082b2b0fb5685dbaaa69bf76f00ae802d33bb893c13` | CPU MPS chi128 |
| New G2 `G2_23_512_and_13_64.csv` | `ffb433747eb61b0710fec6e9e73eef6aab06eaaa9b8ed704f9895d43266e7dd0` | Mixed 23 chi512 GPU / 13 chi64, as asserted in upload commit |
| G2 `G2_23_512_and_13_128.csv` | `bd0c968b03684723187653becaa2615f5b453f36c7baf9ca01d210fa24ab0459` | chi512/chi128, filename claim only |
| Original G3 candidate `direct-fb792001c3e7` | `7ce7b051d0fa7f124e7329c93f15247f46f5b36b3ccfb407910dfebe80c71d7e` | Pauli-path epsilon 0.001, level 1; unsubmitted |
| Kevin G3 v2 / `pps_eps0.001_level1_values.csv` | `33c9a6ac4d0e1b06ce9a79607c20a7ea4dd707e571061aeea7f031715075f7ef` | Pauli-path epsilon 0.001, level 1 |
| Kevin G3 v3 / `pps_eps0.0003_level1_values.csv` | `44fdbe227f1fede6b7abe04934dd375420c86a9427c69b760bb70c00e338d691` | Pauli-path epsilon 0.0003, level 1 |
| G4 candidate `direct-930f7e5b7d14` | `73a5887922c63eb2aafe840fae8e9b26402256fdfc13accf9f689ad4329cbb20` | CPU MPS chi32; accepted zero reported |

The original G3 baseline and Kevin's submitted v2 contain **36 identical parsed values**, with different byte serialization and different supporting jobs. Kevin's 534/800 is score evidence for his submission; it does not establish a submission or score on the original account. Kevin's epsilon 0.01, level 1 `G3_v1` is explicitly **not submitted** in his branch's G3 README, line 32. Its 33 zero entries are diagnostic evidence, not an official zero score.

## Provenance verification and branch coverage

All **138** rows of Kevin's scored vectors match succeeded jobs, values, devices, settings and zero recorded credits in `ea163eb:runs/ledger.csv`: G1's 30 rows at lines 56–111, G2's 36 rows at 113–183, G3 v2's 36 rows at 404–470, and G3 v3's 36 rows at 476–542. These ranges include intervening event rows; the inventory identifies the exact succeeded row for every ID. Matching run receipts verify how values were computed, not the reported website scores. The G2/G3 receipts were imported to main in `2a3eb2b`.

All **110** rows of the original G2, G3 and G4 candidate manifests also match completed entries in main's `runs/jobs.csv`, including values, device and full options. Their recorded cohort compute costs are $0. The original S1–S3 score provenance is the saved `VERIFIED_BROWSER`/`browser_observed` entries in `5807762:runs/submissions.csv`, lines 5–7; this audit did not reopen the website. Graded scores remain user or teammate reports. Explanations prepared after the fact are not claimed to be the exact website text.

The frozen branch-wide audit through `5807762` inspected **53** unique commits reachable through then-current references, local reflogs and `git fsck` recovery, and enumerated **20** retained CSV path/blob versions plus **15** submission JSON versions. Every distinct G2 receipt, problem README and submission-index version was searched. No numeric G2 score above 498 was found in that frozen set. The later `030518f` file claims 579/600 for the mixed G2 submission; its claim has not been checked against the website.

| Reference / history | Audited commit | Result |
| --- | --- | --- |
| `origin/main` in branch-wide audit | `5807762` | Original receipts, Kevin's imported G2/G3 receipts, and the newly uploaded mixed-precision G2 CSV |
| `origin/main` after score-text commit | `030518f` | Repository text claims 579/600 for mixed G2; no website receipt added |
| `origin/kevin/experiment` | `ea163eb` | Native ledger, exact G1, chi128 G2, and G3 epsilon 0.001 / 0.0003 vectors |
| Local `codex/graded-main` at audit start | `681828c` | Original G2 342 receipt, G3 candidate/review and G4 zero feedback |
| Local `main` | `c37c361` | Earlier samples, G1 import and chi32 G2 candidate; no additional higher score |
| Backup reference present at audit start | `9cf240b` | Preparation material and `submissions/.gitkeep`; no scored graded submission. The remote reference disappeared during the audit; the commit remained recoverable. |
| Deleted `assistant/G3` reflog history | `c37c361`, `30990c5` | Resolves to already audited main history; no distinct recoverable scored G3 submission |
| Other recoverable practice/rebase commits | Enumerated in inventory | Placeholder submissions or blank templates; no additional score receipt |

Kevin's branch also retains `submissions/S1_v1.csv` and `S2_v1.csv`. They are exact-computation exports with no independently attributed official submission score in the saved records; they are not extra sample attempts. Its `G1_v1.csv` is an alias of the retained exact G1 bytes.

The read-only local audit hashed **39** CSV files under `D:/BluQubit/submissions/` and `D:/BluQubit/results/workflow/submissions/`. Exports and run receipts do not establish official attempts. Those directories may contain multiple account histories; unlabelled records were not folded into the original account or any collaborator's score. The branch inventory preserves their paths and hashes without modifying them.

No new quantum jobs, browser sessions or submissions were performed for this audit. The original branch-scan counts remain frozen; the 579/600 and 580/600 claims are recorded as later, separately sourced updates.

After the user stopped execution, the original account's G3 epsilon 0.0005,
native level-1 continuation was reconciled as **STOPPED** with nine of 36 rows
completed and two in-flight jobs canceled. Every owned job has terminal status and
known cost; the recorded account charges remained $0.20, all from the earlier GPU
pilot. These nine rows are diagnostic evidence, not a complete candidate or a
scored submission. The [stop snapshot](../reports/audit/campaign-stop.json) records
the statuses and cost source separately from the branch score inventory.
