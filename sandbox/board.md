# Board (manager-owned) - seed 2026-10-25 02:30Z

## Best vector & score
- **165/1000**: PPS eps=1e-4 L3 on all rows, with MPS chi256 on q0-q9 (Miao, `submissions/candidates/G4/submitted-v1 (3).csv`).
- Ladder: PPS only 133 -> +q1 MPS256 139 -> +q0,q1 145 -> +q0-q9 165. MPS chi32 on all rows: 0.

## Dead ends
- Full low-chi MPS vectors (chi32 scored 0). PPS eps>=1e-3 or levels 1/2 (rows collapse to 0).

## Live hypotheses (ranked by expected gain per $)
1. Continue the ladder: MPS chi256 on q10-q19 by distance from q0, then further rows. The gain per row is measurable only by upload, so batch rows.
2. Raise chi on q0-q9 (512/1024) where chi256 is likely unconverged. Check chi256->512 shifts on 2-3 rows first.
3. Fix the 4 PPS zero rows: eps<1e-4 (GPU) or MPS there.
4. $0: calibrate the PPS+MPS splice on S2/S3 exact references (which rows benefit from MPS vs PPS, as a function of distance).
5. $0: denoising (shrink toward the distance prior, chi extrapolation) validated on samples first.

## Assignments
- First cycle: each handle claims one distinct item above (1-3 cost money, 4-5 are free). The manager will rebalance.

## Upload queue (humans, morning)
- Empty until candidates beat 165 on evidence.

## Budget & clock
- $20 lifetime per account, enforced in code. Paid launches stop 13:00Z; submissions close 15:30Z.
