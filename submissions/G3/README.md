# G3: a PPS threshold refinement

Kevin kept native transpilation at level 1 while tightening the Pauli-path threshold. The two complete submitted vectors give the clearest scored comparison on one collaborator's path.

| Stage | Result and files | What changed |
| --- | --- | --- |
| Threshold 0.001 | [534/800 CSV](../teammates/kevin/G3/submitted-v2.csv), [explanation](../teammates/kevin/G3/submitted-v2.txt), [receipt](../teammates/kevin/G3/submitted-v2.json) | Nine of 36 values are zero. |
| Threshold 0.0003 | [773/800 CSV](../teammates/kevin/G3/submitted-v3.csv), [explanation](../teammates/kevin/G3/submitted-v3.txt), [receipt](../teammates/kevin/G3/submitted-v3.json) | Three of 36 values are zero; the reported score rises by 239 points. |

The original account also prepared a complete threshold-0.001 candidate, but [held it for numerical review](../candidates/G3/direct-fb792001c3e7.review.json). Its [manifest](../candidates/G3/direct-fb792001c3e7.json) remains. That candidate has the same 36 parsed values as Kevin's first submitted vector, with different CSV bytes and no score on the original account. The retired bytes are recoverable through [retention.json](../retention.json).

At threshold 0.01, a saved level-1 diagnostic had 33 zero rows and was not submitted. Earlier sample tests also showed that native transpilation levels 2 and 3 could erase useful signal. These observations motivated fixing the representation before comparing thresholds. [The paper](../../writeup/main.tex) gives the vector comparison and its limits.
