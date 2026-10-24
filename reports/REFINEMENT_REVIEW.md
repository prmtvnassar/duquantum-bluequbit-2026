# Proposed refinement review

This review uses saved receipts only. No new simulation, API call, setting change or submission was made. Inputs, job IDs, source hashes and configurations are retained in [refinement_pilot_evidence.json](refinement_pilot_evidence.json). Recommendations apply after preserving coherent G2/G4 CPU MPS chi32 and G3 PPS epsilon .001, level1 baselines.

## Existing score-shape evidence

| Comparison | Correlation on three pilots | Order reversals |
| --- | ---: | --- |
| G2 chi16 to chi32, q0/q18/q35 | 0.9999996504 | 0 of 3 pairs |
| G4 chi16 to chi32, q0/q19/q37 | 0.9295947250 | 1 of 3 pairs: q0/q19 |

These are correlations between approximations on **three pilot IDs**, not full-vector shape validation, official scores, or comparisons with hidden truth.

G2 q18 changes from -0.06198394 to 0.00742392, yet this pilot panel barely changes direction after centering. Its two endpoint values are nearly equal and near one, making the panel insensitive to changes elsewhere. G2 q9 has a measured chi32 estimate of 0.49444184; this unsaturated transition row is a more useful next diagnostic than another endpoint. Its selection uses the observed approximate profile, not an assumed exact answer.

G4 has stronger observed pilot shape instability: q0/q19 reverse order and relative affine residual energy is 0.135854. This does not prove chi32 is more accurate.

G3 q0 remains unresolved: MPS chi16/32 gives 0.02691361/0.64750278, while PPS level1 epsilon .001/.0003 gives -0.07229196/-0.14774957. Level0 at .001 gives -0.05771247. The q35 level1 .0003 job was canceled after 179.147 seconds of reported compute. Neither amplitude disagreement nor cancellation establishes convergence or a correct method.

## Three bounded next diagnostics

1. **G4 q0, mps.cpu, chi64:** a third precision at a changing row; propose a **2100-second hard timeout**, conditional on a fresh quote fitting that limit and the dollar gates.
2. **G2 q9, mps.cpu, chi64:** checks the transition region; propose a **2400-second hard timeout**, conditional on its own fresh quote. A quote for another ID is not execution authorization.
3. **G3 q35, pauli-path, epsilon .0005, level1:** propose a **300-second hard timeout**. This is a distinct intermediate precision. Preserve the canceled .0003 receipt; do not silently retry or overwrite it.

These caps are **proposed, not applied**. Start with approximately $3 of quoted diagnostic allocation if fresh quotes permit. Known actual charges, outstanding quotes and protected completion of any still-incomplete baselines must fit the configured $27 spending ceiling. Retained receipts currently contain 0.20 USD in known charges. Earlier CPU jobs billed zero; future CPU runs must not be assumed free.

## Runtime and device policy

The current adapter uses per_job_seconds both as its quoted-runtime admission ceiling and its actual elapsed cancellation threshold. Setting 2100 seconds therefore permits up to 2100 seconds of execution; it is not a 600-second probe.

Saved G4 chi64 quotes are CPU $0.79/1877.8 seconds and GPU $1.08/968.2 seconds. These dated estimates are nonbinding. A **proposed, unimplemented** improvement would separate quote admission, for example 2400 seconds, from an execution cap, for example 600 seconds. Until that split exists, the explicit raised caps above are the available bounded approach; the old 600/900-second quote gate does not establish physical infeasibility.

Prefer CPU for the first chi64 diagnostic. Matched G4 q0 chi32 CPU/GPU estimates differ by 6.63e-12; GPU saved 24.404 seconds of compute but only **10.251 seconds elapsed**, billing 0.20 USD versus CPU 0.00 USD. This single comparison does not establish performance at larger bonds.

A matched chi64 GPU probe becomes useful if CPU chi64 takes several minutes or reaches its cap. Require fresh cost and GPU-quota checks. Preserve device-specific vectors; one matching value does not authorize mixing CPU and GPU rows into a fixed-device cohort.

## Decisions after the diagnostics

If tractable, G2 chi64 is the strongest first full-refinement candidate because S2 supports substantial chi32-to-64 improvement. For G4, add chi64 q19/q37 only if q0 and observed runtime justify expansion. For G3, a single .0005 result establishes feasibility and pointwise sensitivity; obtain matching q0/q14 values before interpreting its pilot profile. Two-point correlation cannot validate shape.

Once a complete usable baseline exists, retain it and reserve outstanding/new quotes without requiring advance funding for every row of a higher-precision cohort. Partial refinements stay as evidence; export only complete coherent vectors.

For complete successive vectors, compare positive centered correlation and squared residuals after affine alignment, normalized by centered signal energy. Inspect ordering changes and whether residuals decline across precision levels. Uniform offset or positive scaling may leave score unchanged. Single-row trends, sparse pilot stability and cross-method agreement do not certify accuracy.

Keep raw direct outputs. Extrapolation and fusion remain disabled after the held-out candidate failed validation. An observed rounded 100 can justify shifting leaderboard effort elsewhere, but cannot establish exact values or numerical convergence. Never probe the scorer or reconstruct hidden labels.
