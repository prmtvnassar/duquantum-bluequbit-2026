# Recorded official submissions

Each `S1/`, `S2/`, `S3/` or future graded-problem directory contains immutable `attempt-NN.csv`, `.txt` explanation and `.json` receipt. These are **actually submitted** files, not all generated candidates. The receipt includes the observed score, upload checksum, source page and supporting run IDs for every row.

The CSV index is [../runs/submissions.csv](../runs/submissions.csv). All three sample attempt-01 files display 100/100 on the website and used one of the 20 allowed attempts. The score display may round and is not an absolute-error bound. No graded submission has been made by this implementation pass.

Kevin's previously submitted G1 vector is imported under [teammates/kevin/G1/](teammates/kevin/G1/). Its 100% score is teammate-reported, its actual attempt number is unknown, and its explanation is reconstructed from reviewed code. The CSV matches every one of his 30 completed CPU results. These facts are explicit in its receipt; it is not relabelled as an upload made by the current account.

Reviewed complete candidate exports are shared separately under [candidates/](candidates/README.md), with `submitted: false`, their method explanations and job manifests. They are not official attempts. Runtime exports also remain under ignored `results/workflow/submissions/`. Use `scripts/record_submission.py` only after an actual upload and its displayed score have been observed.

The user separately confirmed submitting G1; that confirmation is retained in [G1/user-reported-submission.json](G1/user-reported-submission.json). The current account's attempt number and score remain unverified.
