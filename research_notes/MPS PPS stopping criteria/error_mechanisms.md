# MPS and PPS error mechanisms

## How do finite MPS bond dimension and PPS truncation cause OTOC bias?

### Takeaway
MPS and PPS discard different information: finite-bond MPS compresses the evolving state across cuts, while coefficient-threshold PPS discards Pauli terms from the backward-propagated observable. Their relative accuracy is circuit- and observable-dependent, so there is no transferable numerical value for a “typical” pointwise MPS–PPS divergence.

### Cited Findings
- MPS efficiently follows low-entanglement states; its resource need grows with entanglement, and truncation of an evolved MPS can be monitored by discarded Schmidt weight. [Vidal 2003](https://arxiv.org/abs/quant-ph/0301063); [Tensor Network TEBD documentation](https://tensornetwork.org/mps/algorithms/timeevo/tebd.html)
- Entanglement can grow linearly under local dynamics, forcing exponential resources for a globally faithful MPS approximation; low von Neumann entropy alone does not always imply efficient MPS approximation. [Schuch et al. 2008, entropy growth](https://doi.org/10.1088/1367-2630/10/3/033032); [Schuch et al. 2008, entropy scaling](https://doi.org/10.1103/PhysRevLett.100.030504)
- Pauli propagation works in the Heisenberg picture and tracks a Pauli expansion of the observable. Coefficient truncation discards terms below a threshold; non-Clifford gates generate branching, whereas Clifford gates map Paulis to single Paulis and are an easy, exact limit absent other approximations. [Gharibyan et al. 2025, BlueQubit authors](https://arxiv.org/html/2507.10771v1)
- BlueQubit-authored PPS study found both apparent convergence and strong fluctuations as threshold decreases; it emphasizes that smaller thresholds need not give monotonically better answers, and depth alone does not predict difficulty. [Gharibyan et al. 2025, Sections 4–5](https://arxiv.org/html/2507.10771v1)
- The OTOC tracks information spreading and is connected to Heisenberg operator dynamics. [Xu and Swingle 2024](https://doi.org/10.1103/PRXQuantum.5.010201)

### Inferences
- For an OTOC echo, increased state entanglement may make the MPS branch hard, while spreading of the measured operator into many small Pauli coefficients may make PPS hard. These are related to scrambling but are not identical diagnostics; a Clifford-rich, highly entangling circuit can be easy for PPS and hard for low-bond MPS, while a low-entanglement, strongly non-Clifford circuit can show the opposite.
- Divergence can be strongly nonuniform over qubits because each requested observable follows a different operator trajectory. “Converged qubit count” should therefore be evaluated with per-qubit gaps and a circuit-vector diagnostic, rather than a single circuit average.

### Gaps
- I found no original source that gives a universal, or BlueQubit OTOC-specific, distribution of paired MPS–PPS pointwise differences. It must be measured at matched target rows on the two exact sample circuits and updated on hidden-circuit sweeps.
- The hidden circuits' gate structure, entanglement, operator growth, and exact OTOC definition are unavailable until the challenge kit; these determine which error mechanism dominates.

## What rigorous or a posteriori error certificates exist?

### Takeaway
Local truncation information can support conservative error bounds in principle, but neither a small MPS–PPS gap nor two stable parameter sweeps is an automatic bound on exact OTOC error. The required per-truncation diagnostics may not be exposed by BlueQubit's job results.

### Cited Findings
- MPS methods can record the weight of discarded singular values at each compression; increasing bond dimension is a standard empirical convergence check. [Tensor Network TEBD documentation](https://tensornetwork.org/mps/algorithms/timeevo/tebd.html)
- A recent primary Pauli-propagation review distinguishes per-gate error bounds (combined by triangle inequality) from empirical convergence under relaxed truncation. For Pauli sums, loss of coefficient 2-norm is measurable but coefficient 1-norm directly bounds worst-case additive expectation error; such worst-case guarantees may be loose. [Rudolph et al. 2026, Section III.3](https://arxiv.org/html/2505.21606)
- BlueQubit authors explicitly describe their PPS threshold-convergence protocol as **apparent** convergence, without a general rigorous error guarantee unless all terms are retained; they suggest multiple successive threshold levels within a tolerance and warn about false local convergence. [Gharibyan et al. 2025, Section 4](https://arxiv.org/html/2507.10771v1)
- The Pauli-propagation review reports that oscillatory expectation values make PPS extrapolation and simple monotonic-convergence assumptions particularly difficult. [Rudolph et al. 2026, Section III.3](https://arxiv.org/html/2505.21606)

### Inferences
- If the engine exposes all MPS truncation losses and its implementation uses exact gate updates apart from those truncations, accumulated state-norm loss can conservatively bound observable error by the triangle inequality. If it exposes all discarded Pauli coefficient 1-norms under suitable propagation assumptions, their sum can analogously bound PPS error. The generic mathematics does **not** establish that the BlueQubit API provides these certificates.
- In the likely black-box setting, use at least two adjacent refinements in **each** method, then treat the cross-method gap as another diagnostic rather than a certified tolerance. Include a deliberately finer “challenge” run on some apparently converged sample observables to estimate false-stop frequency.

### Gaps
- I did not find documentation confirming that BlueQubit OTOC jobs return MPS discarded weights or PPS discarded coefficient norms. The kickoff adapter should inspect actual result fields before claiming any formal bound.
- Precise error constants depend on state normalization, observable operator norm, simulation implementation, and whether the kit's OTOC echo is evaluated as a gate circuit or another representation.

## Does MPS–PPS agreement imply accuracy?

### Takeaway
No. Agreement is necessary evidence for a useful cross-check but not sufficient evidence of closeness to the exact observable, because both approximations can share an error or happen to cross at one precision setting.

### Cited Findings
- BlueQubit's PPS study shows that a few successive threshold values can agree at a local fluctuation, yet later threshold reductions can move the estimate; there is no guarantee that apparent convergence precludes a larger later fluctuation. [Gharibyan et al. 2025, Section 4.1](https://arxiv.org/html/2507.10771v1)
- The Pauli-propagation review states that convergence by parameter refinement is a heuristic for biased tensor-network and Pauli-propagation simulations, and no universal extrapolation guarantee exists. [Rudolph et al. 2026, Section III.3](https://arxiv.org/html/2505.21606)

### Inferences
- Algebraically, if the true value is 0.8 and both methods return 0.2, their gap is zero while each has 0.6 error. This demonstrates why the gap itself cannot upper-bound exact error.
- Common upstream mistakes (wrong observable, qubit indexing, sign or normalization) can make both backends agree on the same wrong task. Test the entire pipeline against exact sample labels before calibrating a stopping threshold.
- A safe agreement rule should require: correct sample calibration, each method stable across successive precision settings, cross-method pointwise gap below a **sample-calibrated** threshold, and stability of the full circuit vector under further refinement. These are practical gates, not a proof of accuracy.

### Gaps
- No exact hidden labels exist for direct validation. With only two sample circuits, any learned agreement-to-error relation is weakly supported and should be reported by circuit separately, not as if all qubits were independent samples.
