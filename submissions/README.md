# Retained submissions

This directory keeps **11 distinct numerical vectors**: the best/latest reported
results and the milestones needed to explain the framework's evolution. Each
vector has one retained CSV. The [results audit](../docs/results.md) gives score
sources and account attribution; these scores cannot be added into one account's
official total.

## Best/latest reported results

| Problem | Retained CSV | Reported result and evidence |
| --- | --- | --- |
| S1 | [Exact](S1/attempt-01.csv) | 100/100, browser-observed; [receipt and explanation](S1/) |
| S2 | [Exact](S2/attempt-01.csv) | 100/100, browser-observed; [receipt and explanation](S2/) |
| S3 | [Local PPS](S3/attempt-01.csv) | 100/100, browser-observed; [receipt and explanation](S3/) |
| G1 | [Exact CPU](teammates/kevin/G1/submitted-v1.csv) | Kevin reports 100%, equivalent to 300/300; [receipt](teammates/kevin/G1/submitted-v1.json) |
| G2 | [Mixed chi512/chi128](candidates/G2/G2_23_512_and_13_128.csv) | 580/600 in commit `e0ca909`; account, attempt and source jobs unknown. [Feedback](candidates/G2/G2_23_512_and_13_128.feedback.json). |
| G3 | [PPS epsilon 0.0003, level 1](teammates/kevin/G3/submitted-v3.csv) | Kevin reports 773/800; [receipt](teammates/kevin/G3/submitted-v3.json) |

G4 has no successful scored candidate in the saved evidence. Its accepted zero
is retained below as an experimental failure, not a recommended upload.

## Framework evolution

| Problem | Retained milestone | Why it matters |
| --- | --- | --- |
| G2 | [CPU MPS chi32](G2/attempt-01.csv), 342/600 | Original-account baseline; exposed transition sensitivity. [Receipt](G2/attempt-01.json). |
| G2 | [CPU MPS chi128](teammates/kevin/G2/submitted-v1.csv), 498/600 | Kevin's attributed higher-precision milestone before the later mixed strategy. [Method](teammates/kevin/G2/submitted-v1.txt). |
| G2 | [Mixed chi512/chi64](candidates/G2/G2_23_512_and_13_64.csv), 579/600 | Earlier mixed-precision report; 23 values are unchanged in the later 580 vector. [Feedback](candidates/G2/G2_23_512_and_13_64.feedback.json). |
| G3 | [PPS epsilon 0.001, level 1](teammates/kevin/G3/submitted-v2.csv), 534/800 | Baseline for the fixed-representation refinement to 773/800. [Method](teammates/kevin/G3/submitted-v2.txt). |
| G4 | [CPU MPS chi32](candidates/G4/direct-930f7e5b7d14.csv), 0/1000 | Failed candidate that motivated broader diagnostics and explicit uncertainty. [Feedback](candidates/G4/direct-930f7e5b7d14.feedback.json). |

## Provenance without duplicate exports

Distinct account receipts and decision manifests remain separate. In particular,
the [disputed unnamed-account G2 receipt](teammates/teammate_reported/G2/attempt-01.json)
still exists, but its duplicate CSV and explanation share the original G2 files.
The unsubmitted original-account G3 candidate's [manifest](candidates/G3/direct-fb792001c3e7.json)
and [hold decision](candidates/G3/direct-fb792001c3e7.review.json) remain; its CSV
had the same 36 values as Kevin's epsilon-0.001 vector with different serialization.
That equivalence does not transfer Kevin's score to the original account.

[retention.json](retention.json) records why each vector stays, every removed
path, its checksum, its retained equivalent, and the Git commit/blob needed to
recover original bytes. Historical receipts retain their original path strings;
the [submission index](../runs/submissions.csv) resolves byte-identical aliases.
Numerical equivalence is never substituted for exact upload-byte identity.
