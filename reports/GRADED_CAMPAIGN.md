# Graded campaign, October 24, 2026

The user confirmed that G1 was submitted and authorized starting G2-G4.
The confirmation is recorded separately from website-verified scores in
`submissions/G1/user-reported-submission.json`. Browser site access remains
blocked; the campaign uses the previously authorized BlueQubit SDK for compute.
No submission or score verification through an alternate browser is attempted.

## Mathematical upgrades from the original proposal

`src/otoc/campaign_reasoning.py` implements three conservative extensions:

1. **Independent signal recovery.** A flat primary pilot may be replaced only
   after the other method supplies every pilot ID at one identical precision
   setting with nonconstant outputs. This is a baseline recovery rule, not a
   proof of accuracy or permanent rejection of the original method.
2. **Observed runtime floor.** Scheduling uses the larger of the fresh quote
   and the upper quartile of completed wall times for that problem/device.
   Actual elapsed time includes queue and request overhead. Costs are never
   discounted merely because earlier jobs were free. Sparse histories and
   harder future settings can still exceed this empirical estimate.
3. **Score-relevant shape sensitivity.** For two complete precision vectors,
   center both, project the newer vector onto the older, and compute the
   residual. Squared residuals divided by the newer centered signal energy
   identify rows whose refinement changes shape instead of only offset/scale.
   The scheduler modestly boosts those refinement priorities. Comparisons stay
   within the same device and PPS transpilation level. Constant vectors are
   rejected and sign reversal is explicitly reported. These sensitivities are
   neither hidden-label error estimates nor predicted official score gains.

Raw direct outputs remain the submission values. No extrapolation, fusion,
or bias correction is enabled without held-out sample validation. Current
sample evidence does not justify those transformations.

## Follow-up evidence and allocation

G2 q0 MPS chi16 returned 0.9996910502231614. PPS at 1e-4 returned
0.045095738448185416 after 196.694 seconds of compute (243 seconds elapsed),
compared with zero at 1e-3. This is a plateau breaking with increased precision,
not convergence. The subsequent 1e-5 check was canceled to prioritize complete
independent pilot coverage; its terminal receipt reports $0 billed. Cancellation
and its justification are retained in the ledger. Missing MPS chi16 pilots are
being measured before selecting any full baseline method.

## Initial native evidence

G4 PPS at threshold 0.001 and transpilation level 2 returned exactly zero on
q0, q19, and q37. MPS at bond dimension 16 returned 0.5589102913779098 on q0.
All four completed receipts report zero dollars billed, although their quotes
were $0.20 each. Future costs remain governed by fresh quotes and usage checks;
these observations do not establish that later jobs will be free.

The flat PPS pilot blocks bulk coverage. The MPS discrepancy is evidence of
method sensitivity, not proof that MPS is accurate. Follow-up should inspect
both tighter PPS thresholds and increasing MPS bond dimensions before choosing
a complete submission vector. Do not submit an unresolved constant vector.

## Audit and execution

Every actual cloud attempt is checkpointed before submission in
`results/workflow/remote_actions` and mirrored in `runs/records` and the run
ledger. Quotes and scheduler justifications are in `runs/events`.
The campaign remains serial, preserves the configured reserve, and stops on
unknown costs or an uncertain prior submission. Generated answer CSVs are
candidates until an actual upload is confirmed.
