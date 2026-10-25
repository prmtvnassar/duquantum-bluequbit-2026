# Validity and scoring: GPU precision recovery

Scope: adversarial review of the supplied 14-page paper and saved campaign evidence, October 24, 2026. No simulations, API calls, private-site access or score fitting were performed. Only this research note was written. Paper page numbers refer to the supplied PDF, not a separately verified web version.

## 1. Which accuracy claims transfer to hidden-ID OTOC estimation?

### Takeaway

The paper supports investigating more capable numerical regimes; it does not establish accuracy for these hidden circuits. State fidelity, bitstring recovery, observable absolute error and Pearson score are different quantities. Higher precision and cross-device agreement are evidence to examine, not certificates.

### Cited Findings

- The paper defines pure-state fidelity as F = |<psi_exact|psi_approx>|^2 where tractable, and PPS accuracy as observable absolute error. However, its 46-qubit peaked-circuit quality metric is overlap of a reconstructed bitstring obtained by thresholding signs of local Z expectations. Its 100% at chi1536 is therefore perfect sign-bit recovery on one instance, not 100% state fidelity, exact marginals or a Pearson score. The intermediate overlap trajectory is nonmonotonic. [Supplied paper, pp5 and9](<D:/BluQubit/papers/alternative approaches.pdf>); [extracted text](../../results/pdf_review/alternative_approaches.txt:414).
- The paper's PPS example uses one observable Z62 on a 127-qubit kicked Ising circuit. Its reference 0.2955 comes from converged tensor-network studies, whose reported error is below0.01; it is not a mathematical exact certificate. The quoted PPS error improves to about0.015 at epsilon0.005, worsens to about0.14 near0.00005, then recovers to about0.016 at the finest tested threshold0.00000289. Thus the finest result is not demonstrably better than the cheap coarse result on this example, and the last decimals of reported errors should not be overinterpreted. [Supplied paper, pp10-11](<D:/BluQubit/papers/alternative approaches.pdf>); [extracted text](../../results/pdf_review/alternative_approaches.txt:855).
- The target is the Z expectation of the named program, with each ID representing a separate program. [Retained rules and scoring definition](../../docs/history/workflow_v1.md:39); [formula and sign caveat](../../docs/history/workflow_v1.md:70).
- Current-account G2 has user-reported342/600 on attempt1 with a3.48h time penalty, owner original_submitter, for direct-3643218316ac. The teammate's498/600 remains separate. G4's direct-930f7e5b7d14 has user-reported accepted0/1000 with owner and attempt unknown. These are whole-problem feedback records, not row labels or a reason to fit outputs. [Current G2 receipt](D:/BluQubit/results/workflow/official_submissions/G2-01.json); [separate teammate receipt](../../submissions/teammates/teammate_reported/G2/attempt-01.json); [G4 candidate feedback](../../submissions/candidates/G4/direct-930f7e5b7d14.feedback.json).
- On the10 matched G4 chi16/chi32 rows, centered correlation is0.8591218413, squared residual after affine alignment is26.190966% of the chi32 centered energy,12/45 pairs reverse order, and q1/q3/q4 change raw sign. q4/q0 contribute60.492236% of that subset's residual energy. This is a concentrated10-of38 subset, not complete shape or accuracy validation. [Saved values, hashes and calculations](../../reports/g4_partial_trend_review.json); [review](../../reports/G4_PARTIAL_TREND_REVIEW.md).

### Inferences

**Mathematical derivation, conditional on actual normalized state fidelity.** Let rho=|psi><psi|, sigma=|phi><phi| and ||A||_op<=1. Then

    |Tr[A(rho-sigma)]| <= ||rho-sigma||_1 = 2*sqrt(1-F).

For the measured Pauli Z, ||A||_op=1. F=0.9999 only bounds observable error by0.02; guaranteeing error<=0.01 by this bound requires F>=0.999975. This is a worst-case bound, not a prediction. Neither XEB fidelity nor the paper's marginal-bit overlap may be substituted for F. The campaign does not have a certified F for each hidden-ID state. The derivation follows the paper's squared-overlap definition and the target observable in the retained rules. [Fidelity definition](../../results/pdf_review/alternative_approaches.txt:447); [target observable](../../docs/history/workflow_v1.md:41).

**Mathematical derivation for score sensitivity.** Center the true vector t and prediction y. Decompose the centered error as e=alpha*t+e_perp with t dot e_perp=0. Then y=(1+alpha)*t+e_perp, and, when1+alpha>0,

    rho(t,y)^2 = (1+alpha)^2*||t||^2 /
                 ((1+alpha)^2*||t||^2 + ||e_perp||^2).

Absolute error or fidelity alone cannot certify a weak centred signal: a vector with tiny absolute errors can still have the opposite shape. [retained shape analysis](../../docs/history/workflow_final_graded.md:106).

- Paper support for nonmonotonic PPS convergence defeats a naive rule that every tighter threshold must improve the answer. It also does not prove that our next tighter threshold will be worse or that extremely fine PPS is necessary. Both directions need actual evidence on the same IDs and representation. Cross-device agreement tests numerical implementation consistency; matching two approximations does not locate truth. [Supplied paper, pp10-12](<D:/BluQubit/papers/alternative approaches.pdf>).
- The G4 failure and shape instability justify investigation. They do not justify sign reversal, value permutations, affine correction, inferred labels or a presumption that chi64 fixes the issue. Current G2 headroom is258, not the teammate-derived102 used in older notes; G4's reported1000-point headroom remains account-unspecified. Cross-account scores must not be averaged or treated as a before/after improvement. [Current G2 receipt](D:/BluQubit/results/workflow/official_submissions/G2-01.json); [G4 feedback](../../submissions/candidates/G4/direct-930f7e5b7d14.feedback.json).

### Gaps

- No hidden-circuit state fidelity, exact G4 observable reference or lower bound on the true centered RMS is available. No quantitative guarantee of100% follows from this paper or current pilots. The reasons the same reported G2 candidate received different account scores remain unknown; do not invent differing circuits, upload mistakes or a scoring correction.
- G3 now has a complete coarse36-row PPS baseline according to the coordinator, but completeness is not an accuracy finding. Its retained finer q0 estimate moves from-0.07229196 at0.001 to-0.14774957 at0.0003, and the finer q35 attempt was canceled. That unresolved sensitivity remains relevant to its held recommendation. [Saved G3 sensitivity evidence](../../reports/refinement_pilot_evidence.json).

## 2. What hardware and alternative-simulator conclusions are justified?

### Takeaway

Our low-chi CPU/GPU experiment cannot rule out a useful high-chi GPU advantage. Equally, the paper's scaling fits cannot supply a speed or dollar forecast for hidden OTOC circuits. External simulators are not a route to hidden IDs without their circuit definitions.

### Cited Findings

- The paper fits MPS total runtime exponents2.03+/-0.11 for CPU and1.49+/-0.06 for GPU on40-qubit depth10 QV circuits. These are empirical fits over its tested range, not new asymptotic complexity. Its extrapolation to chi5000 is explicitly illustrative. Its separate peaked circuit crosses toward GPU around chi128 and takes about22hours for one GPU chi1536 run. [Supplied paper, pp6-9](<D:/BluQubit/papers/alternative approaches.pdf>).
- The MPS CPU/GPU comparison holds the Quimb-based implementation fixed. CPU MPS uses two cores, while GPU MPS uses A100 hardware; external SDK PPS baselines use a16GB laptop. The authors disclose platform affiliation, hardware asymmetry, absent full cost accounting, and omitted compilation/transpilation time. Some cuPauliProp figures are inferred from another source rather than directly measured. [Supplied paper, pp3-4,10-13](<D:/BluQubit/papers/alternative approaches.pdf>).
- Low-entanglement QFT exhibits up to7.5-times GPU slowdown. Fine PPS on the specific kicked Ising circuit produces roughly1600-1800-times GPU acceleration against the paper's limited CPU configurations; CPU's inability to go below1e-5 includes a platform option restriction, not a fundamental CPU impossibility. These are workload and implementation claims, not a guarantee about this event's available options or GPU SKU. [Supplied paper, pp8-11](<D:/BluQubit/papers/alternative approaches.pdf>).
- Our matched G4q0 chi32 run agrees across CPU/GPU within6.63e-12. GPU saved24.404seconds of compute but only10.251488seconds elapsed, billed0.20USD while CPU billed0. The existing evidence explicitly describes one route trial, not universal equality, speed or free-CPU behavior. [Matched route evidence and source job IDs](../../reports/refinement_pilot_evidence.json).
- Quantum Rings appears only in the paper's state-vector-interface comparison, not a configurable MPS or PPS sweep. Local Quimb, Qiskit pauli-prop, Julia and Quantum Rings need a concrete circuit description; our graded path submits retained hidden program IDs, whereas the public QASM inputs belong to samples. [Supplied paper, pp3-4](<D:/BluQubit/papers/alternative approaches.pdf>); [retained input distinction](../../docs/history/workflow_v1.md:39); [native ID planning](../../src/otoc/graded.py).

### Inferences

- A high-chi GPU trial is justified if actual CPU time makes the desired precision impractical and its fresh cost and quota checks pass. The paper gives a reason to test, not a reason to extrapolate its reported1700-times PPS or power-law MPS speedup into our budget. Same precision on GPU is not inherently more accurate; the potential gain is reaching higher precision sooner. Queueing, overhead and actual account limits matter to submission time. [Supplied paper, pp6-12](<D:/BluQubit/papers/alternative approaches.pdf>); [matched route evidence](../../reports/refinement_pilot_evidence.json).
- A tiny10-second chi32 elapsed saving does not settle the high-chi decision; neither does the benchmark prove that skipping straight to chi512 or1536 is economical. First compare matched options at the next useful precision, retaining both outputs and costs. A full cohort must remain one device and identical full options for provenance. [Cohort contract](../../docs/history/workflow_final_graded.md); [paper's22-hour example](../../results/pdf_review/alternative_approaches.txt:760).
- Porting sample QASM to another simulator could test algorithmic transfer at zero sample spending, but repeating already strong sample calibration is lower priority than resolving graded G4 sensitivity. It cannot simulate an opaque graded ID. Do not reconstruct hidden QASM or assume an external SDK accepts organizer IDs. [Existing calibration and input limits](../../docs/history/workflow_final_graded.md:61); [sample-only QASM distinction](../../docs/history/workflow_v1.md:39).

### Gaps

- The current SDK/device option audit is delegated to a separate researcher. This review does not assert that the paper's sub1e-5 GPU PPS range, specific hardware, chi1536 or custom-cutoff controls are available for the competition IDs.
- We lack a matched high-chi GPU timing/cost measurement and a symmetric cost-to-solution comparison. The paper explicitly lacks the latter. A power-law fit to a different family does not close those gaps.

## 3. Which bounded trials have the highest present value?

### Takeaway

Retain the initial three-job G4 decision window: CPU chi64 q4 and q0, plus independent PPS level1 on q4. The coordinator is launching the first two; this reviewer has launched none. Pause afterward to select the next method and precision from actual evidence, rather than automatically filling another weak cohort.

### Cited Findings

- q4 then q0 are the strongest observed shape influences in the10-row G4 comparison. Their chi16-to32 changes have opposite directions. Existing G4 PPS epsilon0.001 level2 q0/q19/q37 pilots are all zero; there are no level1/3 attempts in the review's saved scan. G3's same-threshold level1 output resolved signal where level2 was zero, which motivates representation testing without certifying transfer. [Detailed partial review](../../reports/g4_partial_trend_review.json).
- Policy permits30USD graded spending with a10% cushion, so planned exposure must fit27USD; sample spending is0. The targeted CPU runner separates quote-runtime admission from elapsed cancellation requests, preserves full dollar quotes until terminal settlement, and cannot launch GPU jobs. Its CPU batch has at most two owned slots under one runner lock. [Policy](../../configs/workflow_final.json); [targeted execution contract](../../docs/COHORT_BATCH.md:70).
- A complete approximate vector passes format and resolved-signal checks but is not automatically recommended for submission. The workflow retains independent and precision evidence gates, and avoids mixed partial refinements or fitted values. [Export and review distinction](../../docs/COHORT_BATCH.md:50); [failed G4 candidate feedback](../../submissions/candidates/G4/direct-930f7e5b7d14.feedback.json).

### Inferences

1. **G4 q4, mps.cpu, chi64:** highest observed shape influence; test whether its near-zero chi16 value and0.332 chi32 result move again, and whether useful precision fits the actual schedule. **G4 q0, same device/options:** retains the existing anchor and supplies a contrasting residual direction. Use the coordinator's2400-second quote ceiling and600-second cancellation-request threshold. The current launch plan is reported by the coordinator, not newly verified execution here. [Check rationale](../../reports/G4_PARTIAL_TREND_REVIEW.md).
2. **Third new diagnostic: G4 q4, pauli-path, epsilon0.001, native level1**, with a300-second elapsed cancellation request and fresh quote admission. It changes approximation family and representation, so it can expose a failure shared by low-chi MPS. A zero is not rejection and a nonzero is not success. If useful and tractable, the next bounded window should extend the same options to q0 and q19; consider level3 only after reviewing the level1 panel. [Existing PPS evidence](../../reports/g4_partial_trend_review.json).
3. **Conditional replacement or later window, not an automatic fourth launch:** if CPU reaches its cap or measured high-chi runtime makes coverage impractical, reconcile it to terminal known cost, then quote one matched G4q0 chi64 GPU job through the audited GPU path. Compare elapsed time, compute time and direct values at identical options. Require the full quote plus actual/outstanding commitments to fit27USD and comply with GPU quotas. If CPU64 is tractable but unstable, a later chi128 GPU pilot may be more informative than duplicating cheap chi64 solely for timing; its value is additional precision, not an established GPU accuracy advantage. [GPU motivation](<D:/BluQubit/papers/alternative approaches.pdf>); [local route caveat](../../reports/refinement_pilot_evidence.json); [budget rules](../../docs/COHORT_BATCH.md).

At the decision point, inspect signed increments16->32->64, changes in relative order and disagreement with PPS. Two nonconstant points always correlate at+/-1, so do not use the q0/q4 correlation as convergence evidence. A shrinking step is only local sensitivity contraction; a flat MPS/PPS sequence can share bias. Before recommending another G4 submission, seek a broader varied-ID panel such as q4/q0/q1/q19/q37 with another precision step or independently informative representation, and require a complete coherent38-row candidate. Compare its full shape against chi32 for audit, but agreement with the zero-scoring baseline is not a success target. No finite pilot proves100%; unresolved large changes should be stated rather than hidden. [Partial-sensitivity limitations](../../reports/G4_PARTIAL_TREND_REVIEW.md); [nonmonotonic PPS evidence](../../results/pdf_review/alternative_approaches.txt:919).

Budget protection remains dollar-based: past CPU bills of zero do not reduce future full quotes; known0.20USD GPU spending is not a prediction for another job. Once complete baselines exist, do not reserve an entire new higher-precision cohort before every diagnostic, but retain every active/new quote and any remaining genuine baseline reserve. The operational existence of the failed G4 candidate is not scientific confidence in it. An early weak submission does not lower the penalty of a later best submission, so diagnostics need no official upload. If G4 checks remain costly and uninformative, stop this window and reconsider G2q9 chi64 rather than launching unlimited exploration; current G2 has258 points of headroom. [Matched cost evidence](../../reports/refinement_pilot_evidence.json); [controller budget and timing](../../docs/COHORT_BATCH.md:66); [current G2 receipt](D:/BluQubit/results/workflow/official_submissions/G2-01.json).

### Gaps

- No claim is made that these checks yield a score increase, that GPU fallback will be admitted, or that G3's complete coarse baseline deserves submission. The decisions depend on actual reconciled outcomes, fresh quotes and broader numerical evidence.
- The proposed limits are cancellation-request thresholds, not hard service kill or billing caps. A failed or ambiguous attempt must be reconciled; do not duplicate it or hide it by changing accounts, devices or state roots. [Execution and audit contract](../../docs/COHORT_BATCH.md:70).
