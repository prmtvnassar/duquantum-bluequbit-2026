# Prepared candidate files

Each candidate contains a complete validated CSV, a `.txt` explanation for the
mandatory submission field, and a `.json` manifest with the exact jobs and
parameters. These are direct simulator outputs. Actual uploads and their
account-specific score evidence are recorded separately; a complete vector is
not a convergence certificate.

| Problem | CSV | Method explanation | Configuration |
| --- | --- | --- | --- |
| G2 | [direct-3643218316ac.csv](G2/direct-3643218316ac.csv) | [Explanation](G2/direct-3643218316ac.txt) | CPU MPS, bond dimension 32; all 36 rows; $0 recorded cohort cost |
| G3 | [direct-fb792001c3e7.csv](G3/direct-fb792001c3e7.csv) | [Explanation](G3/direct-fb792001c3e7.txt) | **Hold for numerical review; not submitted.** Native PPS, threshold 0.001, transpilation level 1; all 36 rows; $0 recorded cohort cost |
| G4 | [direct-930f7e5b7d14.csv](G4/direct-930f7e5b7d14.csv) | [Explanation](G4/direct-930f7e5b7d14.txt) | **Failed candidate: user reports 0/1000. Do not resubmit.** CPU MPS chi32; all 38 rows; $0 recorded cohort cost |

The user reports that a teammate's first G2 attempt using this candidate scored
**498/600**. Its [separate receipt](../teammates/teammate_reported/G2/attempt-01.json)
retains that attribution. The original account's first attempt using the same
file scored **342/600**, with a displayed **3.48-hour time penalty**, according
to the user. Its [separate receipt](../G2/attempt-01.json) preserves that evidence.
The reason for the different scores is unverified. The exact explanations pasted
on the website are unconfirmed.

The G3 baseline is archived for reproducibility, with an explicit
[review hold](G3/direct-fb792001c3e7.review.json). Its complete, nonconstant vector
passes file checks, but threshold sensitivity and accuracy remain unresolved.
Do not interpret the manifest's format eligibility as an upload recommendation.

The user confirmed that the G4 candidate received an accepted zero grade. Its
[feedback record](G4/direct-930f7e5b7d14.feedback.json) preserves the score while
leaving the account and attempt unknown. The CSV matches every recorded job, but
chi16-to-chi32 trends remain unstable. See the
[numerical review](../../reports/G4_PARTIAL_TREND_REVIEW.md). A complete valid file
alone is insufficient evidence to recommend an approximate submission.

For a candidate that passes numerical review, upload the matching CSV and paste
its explanation together. Record the actual
attempt number and displayed points only after submitting. Preserve each version
so teammates can distinguish prepared files from the exact bytes uploaded.
