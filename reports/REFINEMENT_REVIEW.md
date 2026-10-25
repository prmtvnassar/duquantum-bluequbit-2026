# Refinement review after teammate G2 feedback

Updated 2026-10-24T18:40:07.935371+00:00. This review edits only these two reports. It makes no simulator/API call, submission, configuration change or estimate adjustment. Receipt hashes, job IDs and attributed feedback are retained in [refinement_pilot_evidence.json](refinement_pilot_evidence.json).

## Dated whole-problem outcome

On **October 24, 2026**, the user clarified that **a teammate's first attempt** using G2 candidate [direct-3643218316ac.csv](../results/workflow/submissions/G2/direct-3643218316ac.csv) received **498/600 = 83%**. This is a **user-reported teammate-account outcome**, not independently browser-verified. It does not establish any submission or score for the current account.

The separate [teammate receipt](../submissions/teammates/teammate_reported/G2/attempt-01.json) records owner teammate_reported, attempt 1, source user_report and prepared explanation evidence. The retained candidate and its 36-row manifest were checked: every value is a direct CPU MPS chi32 result. Their local hashes are preserved. The human associates these bytes with the teammate outcome; actual uploaded bytes and website acceptance were not independently observed.

This feedback elevates **G2's whole-problem refinement priority**. It supplies no per-qubit labels, error locations or fitted corrections. Current-account score_progress remains unchanged; teammate feedback stays separately attributed.

## Why the three-pilot correlation was weak

| Comparison | Correlation between approximate pilot vectors | Order reversals |
| --- | ---: | --- |
| G2 chi16 to chi32, q0/q18/q35 | 0.9999996504 | 0 of 3 pairs |
| G4 chi16 to chi32, q0/q19/q37 | 0.9295947250 | 1 of 3 pairs: q0/q19 |

The G2 correlation near 0.99999965 never measured hidden-truth accuracy, the full 36-row profile, or official score. Two nearly equal endpoint estimates near one dominate that three-point panel; the center can move almost affinely while unmeasured transition rows remain inaccurate. The teammate's 83% result illustrates why sparse approximation-to-approximation agreement could not establish high full-vector accuracy.

**G2 q9 is an unsaturated transition row**, with retained chi32 estimate 0.49444184. It is more informative for the next tractability/sensitivity check than another nearly saturated endpoint. This choice follows the observed approximate profile and was identified before the score arrived; no hidden label is inferred.

G4 still shows greater pilot shape change, including a q0/q19 order reversal. G2 now additionally has whole-problem feedback indicating substantial score headroom. Neither observation identifies which individual values are wrong.

## Next allocation

1. **Preserve baseline coverage priority.** Finish the active G4 chi32 cohort and protect/complete the planned G3 PPS epsilon .001, level 1 baseline. Do not interrupt active jobs or launch a competing runner.
2. **Run G2 q9 CPU MPS chi64 as the first refinement diagnostic**, after protected coverage. Use explicit targeted diagnostics, one slot, a **2400-second quote-runtime ceiling** and **600-second elapsed cancellation-request threshold**, with fresh quote/budget checks. Use configs/cohorts/mps_chi64.json. The diagnostic is proposed; it has not been live-executed.
3. **If tractable, complete one coherent G2 chi64 vector.** A successful q9 run establishes feasibility and pointwise sensitivity, not full-vector improvement. S2 supports trying the chi32-to-64 refinement, but cannot guarantee G2's score. Preserve the chi32 baseline if finer work stops; never replace isolated rows.
4. Keep **G4 q0 chi64** as the next CPU diagnostic with the same 2400/600 quote/execution thresholds. Keep **G3 q35 PPS epsilon .0005, level 1** later, with a 300-second cancellation threshold and configs/cohorts/pps_epsilon0005_level1.json. Preserve its canceled .0003 receipt.

## Timecap and GPU decision

The targeted CPU controller has now been **released and validated**, according to root verification: 107 tests and 75 subtests passed at 18:38 UTC on October 24. The split-cap source and hashes are recorded in the evidence file. No proposed diagnostic has run live. This supersedes the prior report's unimplemented-split wording and 2100/2400-second hard-execution proposals. The legacy serialized adapter still couples both limits through per_job_seconds.

At 600 seconds the controller requests cancellation; termination and cost settlement can occur later. **Reconcile the CPU job to a terminal status with known cost before GPU fallback.** Then obtain a fresh GPU quote for the same G2 q9, chi64 configuration. If CPU timing makes completion impractical, a single matched GPU feasibility check is justified subject to dollar and total/rolling GPU quota gates.

The CPU-only controller cannot launch GPU work. Use the approved GPU path with an explicit bounded timeout compatible with its fresh quote. Do not silently retry or overwrite the canceled CPU action. If the GPU check succeeds materially faster, complete a separate coherent GPU chi64 vector; do not splice CPU and GPU rows.

The earlier G4 chi32 GPU comparison saved only 10.251 seconds elapsed for 0.20 USD extra. That supports CPU-first testing but does not rule out a larger GPU advantage at chi64. Earlier CPU runs billed zero; future CPU work must not be assumed free.

## Budget and validation

Keep actual charges, outstanding/new quotes and protected G4/G3 baseline completion within the configured **$27 spending ceiling**. Since a complete usable G2 baseline exists, its refinement need not reserve the entire chi64 cohort in advance. Preserve every active/new quote commitment and retain the old complete vector if the budget ends.

After completing chi64, compare its full 36-row vector with chi32 using positive centered correlation and squared affine residuals normalized by centered signal energy. Inspect ordering changes and whether residuals contract at further precisions. These are sensitivity diagnostics, not hidden-truth error bars: small changes can share bias, while large changes need not improve accuracy.

Outputs remain raw direct estimates. Extrapolation/fusion stay disabled after failed held-out validation. Submit only genuine complete coherent candidates; never game the scorer or reconstruct labels. A rounded 100 may justify shifting leaderboard effort elsewhere but cannot establish exact values or numerical convergence. The only score added here is the **teammate-reported 498/600**, not a current-account result.
