# Stopping protocol for converging qubits

## How to combine pointwise, within-method, vector-shape, and cross-method diagnostics

### Takeaway
Use MPS–PPS agreement as a *screen*, not as an accuracy certificate. A robust stop rule requires agreement between methods **and** stability under one or more precision refinements within each method, evaluated at the circuit-vector level as well as per qubit.

### Cited Findings
- BlueQubit-affiliated PPS authors propose checking successive estimates at progressively smaller coefficient thresholds, but explicitly call this *apparent* convergence because a finer threshold can later change the value; truncation error is nonmonotonic. Their example protocol requires multiple successive estimates within a tolerance, not one adjacent pair. — [Gharibyan et al., A Practical Guide to using Pauli Path Simulators](https://arxiv.org/html/2507.10771v1)
- In a separate primary study, Pauli propagation appeared converged at the tested weight and coefficient thresholds yet retained a significant discrepancy from exact statevector results. That experiment also found MPS needed very large bond dimension for accuracy in its setting. This is a counterexample to treating an observed numerical plateau as guaranteed truth; it is **not** a quantitative estimate for the OTOC challenge. — [Kiss et al., Communications Physics 2026](https://pmc.ncbi.nlm.nih.gov/articles/PMC13518235/)
- SciPy defines Pearson correlation from centered vectors; for a constant vector it is undefined, and for a nearly constant vector numerical cancellation can make it unreliable. — [SciPy `pearsonr` reference](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.pearsonr.html)

### Inferences
- Define matched estimates for circuit `c`, observable `q`: `M[q]` at bond dimension `chi_k`, `M_prev[q]` at the preceding bond dimension, `P[q]` at threshold `eps_j`, and `P_prev[q]` at the preceding threshold (same observable definition, normalization, qubit key, and transpilation policy). Calculate `cross[q] = abs(M[q]-P[q])`, `step_M[q] = abs(M[q]-M_prev[q])`, and `step_P[q] = abs(P[q]-P_prev[q])`. Use an absolute tolerance first; relative error with denominator `abs(M[q])` is unstable around zero.
- If more than one refinement is affordable, require two successive small steps for each method or an additional finer-point challenge run. A single tiny step can be a false plateau, particularly for PPS. Phrase the status as `numerically_stable_at_tested_precisions`, not `accurate`.
- The raw pointwise difference can overstate a score problem if the score is invariant to a common positive affine transform, but it can understate error if both methods share bias. For vectors, compute `shape_cross = 1 - Pearson(M,P)` and each method's adjacent-level shape change. Algebraically, the Euclidean distance between two centered unit vectors is `sqrt(2*(1-rho))`; this supplies an interpretable geometry, but still no bound to the unknown exact vector. If either centered norm is tiny relative to a scale floor determined on samples, mark `NEAR_CONSTANT_VECTOR` and replace correlations with raw RMS/max differences.
- A circuit-level stop should require a complete prediction vector, controlled *tail* of per-qubit differences (e.g. `max_q cross[q]` and `max_q max(step_M[q], step_P[q])`, or a predeclared high quantile plus explicit review of excluded outliers), and stable vector shape. Counting the fraction of converged qubits alone can miss one or two high-impact qubits that rotate the centered vector.
- The key logical asymmetry follows from the triangle inequality: if `cross[q]=d`, at least one method has true absolute error at least `d/2`; when `d` is small, neither method's true error is bounded above. E.g. exact `0.7`, MPS `0.20`, PPS `0.21` gives close methods and two large errors. For a pure-correlation score, two identical reversed vectors can agree perfectly with each other and each score `-1` against truth.

### Gaps
- There is no universal numerical MPS–PPS disagreement or universal acceptable tolerance for these hidden OTOC circuits; benchmark data and the actual scoring function are needed.
- Whether BlueQubit exposes trustworthy per-job truncation certificates or partial outputs for these challenge jobs must be verified from the release interface; none is assumed in this protocol.

## How to derive a threshold from only two exact sample circuits

### Takeaway
Predeclare a small tolerance grid, replay a proposed early-stop policy against both labeled sample circuits, and use two-way leave-one-circuit-out (LOCO) evaluation. If no threshold preserves the official sample score on both held-out circuits, do not enable agreement-based automatic stopping.

### Cited Findings
- scikit-learn's validation guide explains that when multiple observations belong to a dependent group, validation should hold out entire groups to assess generalization to a new group. `LeaveOneGroupOut` does this explicitly. — [scikit-learn cross-validation guide](https://scikit-learn.org/stable/modules/cross_validation.html)
- The same guide warns that repeated tuning on a test set causes overfitting of the evaluation itself. — [scikit-learn cross-validation guide](https://scikit-learn.org/stable/modules/cross_validation.html)
- BlueQubit-affiliated PPS authors show that the answer's apparent convergence can depend strongly on the spacing of tested thresholds and tolerance, and that different circuit instances must be probed independently. — [Gharibyan et al.](https://arxiv.org/html/2507.10771v1)

### Inferences
- Treat each sample *circuit* as one validation unit; qubits within it are coordinated outputs, not independent validation circuits. Fix a short policy family before seeing scores, for example thresholds on `cross`, within-method steps, and whole-vector shape. Avoid separately tuning thresholds for each qubit or each hidden circuit.
- On sample A, simulate the same precision ladder planned for hidden circuits, recording the earliest stage at which the candidate stop rule would fire. Compare that stage's *actual official sample score* and raw errors with the best feasible later stage and with a direct-estimate anchor. Fit/tune the threshold using A only; evaluate unchanged on B. Reverse A/B. Retain per-circuit results and the worse of the two degradations, not just the mean. A permissible score-loss margin `eta` must be chosen according to the team objective before inspecting candidates; it is a tradeoff, not a scientific error bound.
- A conservative acceptance rule is `max(score_best_feasible[s]-score_stop[s] for s in {A,B}) <= eta`, plus both samples satisfy any required max-qubit/RMSE error gate, and the saved compute is material. Because just two circuits are available, even two passing folds are weak evidence; tag the rule as empirical. If the hidden circuits visibly differ in width, depth, or score regime from samples, relax confidence in transfer and schedule at least one challenge refinement beyond the stop point where affordable.
- If the official score is correlation-dominated, calibrate `shape_step` and `shape_cross` jointly with amplitude-aware gates only if they affect the score; do not optimize a raw absolute tolerance against a score that ignores a benign affine shift. Conversely, use the actual official scorer if it penalizes amplitude. Do not assume Pearson equals the challenge score until the scorer is inspected.
- Inspect failures at small and large target magnitudes and nearly constant vectors separately. A threshold can appear successful on average while failing precisely where the score is sensitive. Consider `tau_abs = alpha * scale_sample` with a predeclared small grid for `alpha`; the scale could be a robust across-sample spread with a nonzero floor, but the same formula must be used unchanged on hidden predictions.

### Gaps
- The two exact sample circuits and official `score_csv` implementation were not available to this researcher, so no numerical threshold, typical score loss, or observed stopping cost can honestly be supplied yet.
- Official scoring could depend on normalization and amplitude rather than Pearson alone; the release scorer is needed to finalize the score-loss margin and vector gate.

## Whether to stop running jobs or decline future refinements

### Takeaway
Interpret “stop” primarily as **do not launch the next precision job** after a completed stage passes the calibrated rule. Cancel an already-running BlueQubit job only if the actual API/billing semantics show that cancellation saves enough credits or time to justify losing that job's result.

### Cited Findings
- BlueQubit-affiliated PPS authors give an explicit resource-aware rule: refine the coefficient threshold until a prescribed sequence of estimates agrees or the allotted compute time is exceeded; they also show that more expensive refinement may leave the answer essentially unchanged. — [Gharibyan et al.](https://arxiv.org/html/2507.10771v1)
- In that paper's generic comparison, PPS normally handles an observable with a separate propagation, while MPS can evolve one approximate state and extract multiple expectations; challenge-specific batching remains to be verified. — [Gharibyan et al.](https://arxiv.org/html/2507.10771v1)

### Inferences
- With independent per-qubit jobs, freeze qubits passing all gates and spend further jobs on unresolved qubits. With a bundled or whole-circuit job, a count such as “90% of qubits converged” is **not** itself a cost saving; decide whether the expected score impact of the remaining qubits divided by *whole-job* credits and wall time beats another feasible circuit/action. Keep the completed baseline vector regardless.
- Proposed decision loop (heuristic, not a calibrated confidence interval):

```text
after each completed precision stage for circuit c:
    if any required q lacks a finite baseline: prioritize coverage; continue
    compute cross[q], step_M[q], step_P[q] on aligned outputs
    check near-constant-vector guard, vector shape changes, and outlier tail
    if the entire vector passes a sample-validated stop rule:
        mark c as provisionally stable; skip the next precision job
    else:
        list supported next MPS/PPS actions at the actual billing granularity
        predict score-impact proxy, credits, wall time, and failure risk
        run only actions whose expected benefit exceeds alternatives and reserves
    retain prior complete CSV checkpoint throughout
```

- If only a few qubits fail, first verify those rows' indices and normalization. If further precision is feasible, prioritize them. If the interface forces whole-circuit reruns, use the potential *vector* effect of those few values, not their count, to compare gain against cost. A near-deadline run that cannot finish or threatens the submission buffer should be declined even if the numerical stop gate has not passed.
- Already running jobs should generally complete while next actions are chosen; cancellation requires concrete evidence that billing halts and no useful partial result is forfeited. A rapidly converging circuit can still be de-prioritized even if its epistemic status remains only `provisionally stable`.

### Gaps
- Challenge-specific job granularity, partial-output availability, cancellation behavior, and actual billing are not established in the sources used here; all are kickoff measurements.
