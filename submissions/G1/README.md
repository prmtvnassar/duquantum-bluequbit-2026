# G1: exact results reused

A teammate ran each of the 30 G1 programs on the exact CPU backend and reported a 300/300 result. The completed vector and its job references were already available, so the team reused those values rather than running the same programs again.

| Record | Files | What it establishes |
| --- | --- | --- |
| A teammate's reported submission | [CSV](../teammates/teammate-1/G1/submitted-v1.csv), [explanation](../teammates/teammate-1/G1/submitted-v1.txt), [receipt](../teammates/teammate-1/G1/submitted-v1.json) | Complete exact vector with per-row job references and a teammate-reported 100% score. The explanation was reconstructed from the run records. |
| Original account's confirmation | [Confirmation](user-reported-submission.json) | An upload was confirmed; its score, attempt number, and exact uploaded bytes were not recorded. |

The original confirmation names a former copy at `problems/04_graded_G1/exact_values.csv`. Its bytes were identical to a teammate's retained CSV. [The retention record](../retention.json) gives the original Git blob and checksum. The reported 300/300 belongs to a teammate's record.
