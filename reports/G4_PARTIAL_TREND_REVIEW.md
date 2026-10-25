# G4 partial precision-trend review

**User-reported graded zero, 2026-10-24:** the user clarified "yes G4 in candidates got 0" for candidate direct-930f7e5b7d14. Treat this as accepted grading reported by the user, not an independently verified current-account result. Account owner and attempt number remain unknown. This whole-problem feedback supplies no hidden row labels. After the active G3 baseline finishes, prioritize G4 investigation ahead of G2 refinement: reported headroom is 1000 points versus 102. Do not interrupt the active baseline.

The complete [G4 CPU chi32 candidate](../submissions/candidates/G4/direct-930f7e5b7d14.csv) contains 38 direct values with 0 USD recorded cohort cost. All 38 values, job IDs and costs were checked against saved native receipts. Only **10 of 38 IDs** have matched CPU chi16 results: **q0 through q7, q19, q37**. This concentrated, nonrandom subset is not a full-vector precision comparison. [Evidence JSON](g4_partial_trend_review.json) preserves values, configurations, job IDs, source hashes and calculations. Inputs were read from the original D:/BluQubit state; only these two reports were written in the isolated worktree.

## Shape changes on the 10 matched rows

For centered old/new vectors a,b, fit beta=(a dot b)/(a dot a), then calculate r=b-beta*a. The fitted relation is chi32 = 0.02876316 + 0.79969190*chi16. This diagnostic fit never changes submission values.

- Centered correlation: **0.8591218413**.
- Relative squared affine residual, ||r||^2/||b||^2: **0.26190966** (26.19%).
- Pairwise order reversals: **12 of 45**; no pairs tied within 1e-8.
- Raw sign changes: **q1, q3, q4**.

This is substantial sensitivity to bond dimension on the subset. Residual energy is not hidden-truth error or an official score estimate. A common positive affine offset can itself cause sign changes; the order reversals and residuals show changes beyond a positive affine transformation. Neither correlation between approximations nor a rounded score of 100 would establish numerical accuracy.

| Row | chi16 | chi32 | Affine residual | Share of subset residual energy |
| --- | ---: | ---: | ---: | ---: |
| q4 | -0.005732 | 0.331990 | +0.307811 | 41.85% |
| q0 | 0.558910 | 0.270272 | -0.205447 | 18.64% |
| q37 | 0.920456 | 0.957061 | +0.192217 | 16.32% |
| q1 | 0.135555 | -0.053917 | -0.191083 | 16.13% |

## Bounded investigation after the active G3 baseline

Use an initial window of **at most three new diagnostics**, with fresh quotes and existing budget protection:

1. **G4 q4, CPU chi64.** It has the largest observed shape influence. This is a sensitivity ranking, not an inferred error ranking.
2. **G4 q0, CPU chi64.** Retain the preplanned comparison. Together q4 and q0 account for **60.49%** of this subset's residual energy and have opposite residual directions.
3. **G4 q4, PPS epsilon 0.001, native transpilation level1.** This tests an independent method and representation before committing to a full MPS refinement. It may go first if a fresh quote makes it substantially quicker.

Proposed MPS limits are **2400 seconds for quote-runtime admission and 600 seconds before requesting execution cancellation**; proposed PPS cancellation is **300 seconds**. These diagnostic jobs were not executed by this review. Quote runtime is an estimate, separate from the execution cancellation threshold; cancellation is not instantaneous termination or settled cost. Reconcile each canceled job before rerouting. Preserve remaining baseline reservations and the 27 USD working budget, including actual and outstanding quoted commitments. CPU jobs billed zero so far do not guarantee future free execution.

Saved G4 PPS receipts contain only epsilon 0.001 level2 pilots q0/q19/q37, all zero. There are no saved G4 level1 or level3 attempts in the scanned source. On G3 q0, the same epsilon produced zero at level2 and -0.07229196 at level1. That motivates representation exploration; it does not prove a G4 benefit or validate either answer. The user-reported graded zero makes changing method family a serious alternative to blindly increasing bond dimension.

One PPS point cannot establish shape, and one zero cannot reject a representation. If level1 is tractable, a later bounded window can extend the identical configuration to q0/q19 before any full cohort. If that small panel is flat or impractical, consider a bounded level3 check; avoid automatic endless changes of threshold or level. The optional third MPS sensitivity row would be q1, but independent PPS has priority in the initial three-job window.

## What would justify a full refinement

Two nonconstant points always have correlation plus or minus one. Smaller chi32-to-chi64 changes at q4/q0 would only indicate local contraction, not an error bound or converged shape. Reassess these raw changes together with independent-representation tractability before allocating a full cohort. If changes remain large or reverse direction, higher bond dimension remains unvalidated; a full chi64 run may still provide useful coverage but has no accuracy guarantee.

Before recommending another G4 submission, require stronger numerical corroboration on a broader same-ID panel spanning q4, q0, q1, q19 and q37: a further precision step within the chosen family and/or an independently informative representation. Inspect centered shape, affine residual and order, not amplitude agreement alone. Material unresolved crossings or large shape changes prevent a confident recommendation. Panel agreement is still not an accuracy guarantee, and correlation with the zero-scoring chi32 baseline is not a success criterion.

Any new export must contain one complete, identical-options, single-device 38-row cohort. Retain the existing chi32 artifact for audit. Do not splice pilot refinements, apply the affine fit, flip signs, reorder rows, extrapolate values or game the scorer with artificial candidates. A completed baseline permits incremental refinement funding while preserving active-job quote commitments; it does not require reserving every higher-precision row in advance. Avoid another submission until a genuine complete candidate and its provenance are ready.

The known G2 result remains **teammate-reported 498/600 on first attempt**, not a current-account score. It supports later G2 refinement, while the user-reported accepted G4 zero now gives G4 bounded investigation higher priority after the active G3 baseline. Neither whole-problem report identifies any row-level truth.
