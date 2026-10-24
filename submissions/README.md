# Recorded official submissions

Each `S1/`, `S2/`, `S3/` or graded-problem directory contains immutable `attempt-NN.csv`, `.txt` explanation and `.json` receipt. These are **actually submitted** files, not all generated candidates. Receipts distinguish browser-observed submissions from user reports and include the score, upload checksum, source page and supporting run IDs for every row.

The CSV index is [../runs/submissions.csv](../runs/submissions.csv). All three sample attempt-01 files display 100/100 on the website and used one of the 20 allowed attempts. The score display may round and is not an absolute-error bound.

Kevin's previously submitted G1 vector is imported under [teammates/kevin/G1/](teammates/kevin/G1/). Its 100% score is teammate-reported, its actual attempt number is unknown, and its explanation is reconstructed from reviewed code. The CSV matches every one of his 30 completed CPU results. These facts are explicit in its receipt; it is not relabelled as an upload made by the current account.

Complete candidate exports are shared separately under [candidates/](candidates/README.md), with `submitted: false`, their method explanations, job manifests and explicit numerical-review status. They are not official attempts. Runtime exports also remain under ignored `results/workflow/submissions/`. Use `scripts/record_submission.py` only after an actual upload and its displayed score have been observed or reported, selecting the matching evidence source.

The user separately confirmed submitting G1; that confirmation is retained in [G1/user-reported-submission.json](G1/user-reported-submission.json). The current account's attempt number and score remain unverified.

The user also reports a teammate's first G2 attempt scored **498/600** using the
prepared chi32 vector. Its [receipt](teammates/teammate_reported/G2/attempt-01.json)
uses owner `teammate_reported` and status `USER_REPORTED`; it does not consume or
claim an attempt on the current account. The retained explanation is the prepared
method note, with the actual website wording explicitly unconfirmed.

The original account's first G2 attempt is separately recorded at
[G2/attempt-01.json](G2/attempt-01.json): **342/600**, with a reported **3.48-hour
time penalty**, using the same candidate file. The different account scores are
not reconciled by assumption.

The user confirmed that the G4 candidate received an accepted **0/1000**. Its
[feedback record](candidates/G4/direct-930f7e5b7d14.feedback.json) preserves that
result with account and attempt unknown, without inventing an official attempt
identity. G3's archived baseline has not been submitted or scored.
