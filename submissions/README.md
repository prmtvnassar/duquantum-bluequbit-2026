# Submission archive

The [results audit](../docs/results.md) is the current score and attribution register. A score receipt says whether its evidence came from the browser, a collaborator, or the user. File names such as v1 and v3 do not establish official attempt numbers.

## Original account

- [S1](S1/attempt-01.json), [S2](S2/attempt-01.json), and [S3](S3/attempt-01.json) each have the submitted CSV, mandatory explanation, browser-observed 100/100 result, and attempt-1 receipt.
- [G2 attempt 1](G2/attempt-01.json) records the MPS bond-dimension-32 CSV at **342/600**, with a user-reported **3.48-hour** time penalty.
- [G1 confirmation](G1/user-reported-submission.json) records that the user submitted G1. The original account's score, attempt number, and exact uploaded bytes remain unknown.

## Collaborator submissions and feedback

- Kevin's [G1 exact vector](teammates/kevin/G1/submitted-v1.json) is reported at 100%; his [G2 bond-dimension-128 vector](teammates/kevin/G2/submitted-v1.json) at **498/600**; and his [G3 Pauli-path vectors](teammates/kevin/README.md) at **534/800** and **773/800**. His completed row jobs were checked against these files. His G2 result is the highest with an account-attributed scored submission receipt.
- An older [unnamed-teammate G2 receipt](teammates/teammate_reported/G2/attempt-01.json) also reports **498/600**, but attaches that score to the bond-dimension-32 CSV. That attribution conflicts with Kevin's distinct bond-dimension-128 receipt and is retained as disputed evidence.
- The user confirmed that the newer [mixed-precision G2 CSV](candidates/G2/G2_23_512_and_13_64.csv) was submitted. A later [repository note](candidates/G2/G2_23_512_and_13_64.score-report.txt), introduced by commit `030518f`, claims **579/600**, the highest repository-reported G2 score. This is a text claim, not website feedback. The note describes 23 GPU MPS bond-dimension-512 rows and 13 bond-dimension-64 rows, but no per-row source mapping or completion receipts accompany it. The submitting account, official attempt number, time penalty, and exact uploaded bytes remain unverified in the [feedback record](candidates/G2/G2_23_512_and_13_64.feedback.json).
- The user reported that the [G4 bond-dimension-32 candidate](candidates/G4/direct-930f7e5b7d14.feedback.json) was accepted and scored **0/1000**. Its account and attempt number remain unknown.

The [candidate directory](candidates/README.md) contains both prepared files and candidates that were later submitted. Location alone does not establish upload status. The [submission CSV index](../runs/submissions.csv) and the [run ledger](../runs/README.md) provide machine-readable records; unresolved claims are preserved in JSON feedback files. Keep repository-text claims distinct from website-observed scores and account-attributed receipts. A whole-problem score does not reveal any row's true expectation value.
