# Candidate files and feedback

A complete CSV is a prepared vector, not an accuracy certificate. Some files here were later submitted; follow each feedback record and the [results audit](../../docs/results.md) for current status.

| Problem | File | Method and recorded status |
| --- | --- | --- |
| G2 | [Original bond-dimension-32 CSV](G2/direct-3643218316ac.csv), [explanation](G2/direct-3643218316ac.txt) | All 36 CPU MPS rows. Original-account attempt 1 scored **342/600** with a reported **3.48-hour** penalty. An older unnamed-teammate claim of **498/600** on these bytes is disputed; Kevin's documented 498 belongs to another file. |
| G2 | [Mixed-precision CSV](G2/G2_23_512_and_13_64.csv), [score note](G2/G2_23_512_and_13_64.score-report.txt), [feedback](G2/G2_23_512_and_13_64.feedback.json) | **User-confirmed submitted; later repository note claims 579/600**, the highest G2 score reported in this repository. This is not a website-verified score. Account, official attempt and time penalty remain unknown. The note describes 23 GPU MPS bond-dimension-512 rows plus 13 bond-dimension-64 rows, but no per-row job mapping or source receipts accompany it. |
| G3 | [Original baseline CSV](G3/direct-fb792001c3e7.csv), [explanation](G3/direct-fb792001c3e7.txt), [hold](G3/direct-fb792001c3e7.review.json) | All 36 native Pauli-path rows, threshold 0.001, transpilation level 1. This original-account candidate is **unsubmitted** and held for numerical review. Kevin separately submitted a vector with identical parsed values and scored 534/800. |
| G4 | [Bond-dimension-32 CSV](G4/direct-930f7e5b7d14.csv), [feedback](G4/direct-930f7e5b7d14.feedback.json) | All 38 CPU MPS rows. **Accepted 0/1000**, user reported; account and attempt unknown. Do not reuse this failed candidate. |

The submitted Kevin G2 bond-dimension-128 file and his G3 threshold-0.0003 file are in the [collaborator archive](../teammates/kevin/README.md). Kevin's **498/600** is the highest G2 result with an account-attributed scored submission receipt. Candidate manifests retain the original jobs and settings where available. The mixed-precision file's exact uploaded bytes, explanation and row provenance have not been verified. Its higher reported score cannot establish a score gain from the precision mix across accounts. The original G3 candidate's format checks do not settle numerical accuracy.

For any future submission after the campaign resumes, validate the full circuit-ID set and row provenance, review precision trends, upload the matching CSV, paste the matching explanation, and save the displayed score and attempt under the correct account. Do not revise recorded upload bytes.
