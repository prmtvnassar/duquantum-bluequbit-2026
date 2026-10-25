# Paper methods for GPU precision recovery

## Which GPU and precision techniques does the paper actually demonstrate?

### Takeaway
The measured benefit is a workload-dependent ability to run more expensive approximations faster. GPU choice alone does not increase mathematical precision at fixed settings, and the paper does not establish accuracy for this campaign's hidden circuits.

### Cited Findings
- The supplied paper is *Benchmarking Zero-Setup Quantum Circuit Simulators*, marked arXiv:2607.09882v4, September 2, 2026, by Mazumder et al. The 14-page source has SHA256 `97f009b8783e1695ba8db8ac2268f56c1aca647f25fa1253b12d6ce014dd8405`. Full text was read and pages 6-10 rendered/visually checked. Pages 1 and 13 identify its scope and BlueQubit affiliation. - [Supplied primary source](<D:/BluQubit/papers/alternative approaches.pdf>)
- For 40-qubit depth-10 quantum-volume circuits, the reported MPS runtime exponents are CPU 2.03 +/- .11 and GPU 1.49 +/- .06; chi5000 runtimes are explicitly extrapolated. Pages 6-7, Figures 3-4. - [Supplied primary source](<D:/BluQubit/papers/alternative approaches.pdf>)
- QFT at chi_max64 and 96 qubits takes about 90 seconds GPU versus 12 seconds CPU. The peaked example crosses near chi128; chi256 CPU is about twice as slow as GPU. Pages 8-9, Figures 7 and 9. - [Supplied primary source](<D:/BluQubit/papers/alternative approaches.pdf>)
- At chi256, fixed-circuit build time is about 715 seconds CPU versus 360 seconds GPU; speedup falls from about 2x at one shot to about 1.3x at 10,000 shots. Page 7, Figure 5. - [Supplied primary source](<D:/BluQubit/papers/alternative approaches.pdf>)
- The peaked 46-qubit example's overlap rises from 50% at chi4 to 100% at chi1536, with intermediate reversals; chi1536 GPU takes about 22 hours. Overlap is the agreement of the bitstring reconstructed from local-Z signs with an embedded target. Pages 5 and 9, Figure 9. - [Supplied primary source](<D:/BluQubit/papers/alternative approaches.pdf>)
- On one 127-qubit kicked Ising benchmark, GPU PPS takes 3.17-3.52 seconds at delta=.000025 and 27.6 million Paulis, versus 5,714 seconds on BlueQubit CPU. GPU crossover is around .001; coarse .005 and above favors CPU. Pages 9-10, Figure 10. - [Supplied primary source](<D:/BluQubit/papers/alternative approaches.pdf>)
- PPS absolute error is about .015 at .005, about .14 near .00005, and about .016 at .00000289. The reference .2955 comes from converged tensor-network work with reported absolute error below .01. Pages 10-11, Figures 11-12. - [Supplied primary source](<D:/BluQubit/papers/alternative approaches.pdf>)
- BlueQubit CPU's sub-1e-5 limit is described as API-imposed, while local CPU baselines hit laptop memory limits. Research GPU sweeps reach below that floor. Pages 10-11. - [Supplied primary source](<D:/BluQubit/papers/alternative approaches.pdf>)

### Inferences
- Test higher chi separately from hardware: first obtain a controlled precision comparison, then assess whether a matched GPU route makes that precision affordable in elapsed time and dollars.
- The chi128 crossover is a benchmark observation, not a universal rule. Our hidden-ID quote and actual elapsed measurements must govern route selection.
- Coarse and fine PPS points can both be informative because error need not be monotonic; the paper does not identify the best threshold for our circuits.
- Target-bit recovery does not transfer to OTOC estimation. Do not label its 100% overlap as state fidelity or expected graded score.

### Gaps
- No paper data covers this campaign's hidden Duke IDs, their entanglement, retained-Pauli counts, full OTOC vector error, or official Pearson score.
- No verified GPU-PPS named-ID capability, fine threshold below 1e-5, custom hardware selection, or custom contraction strategy is established for this account by the paper.
- No source raw-data reproduction was performed. The linked repository and referenced papers were not fetched; all paper-specific findings above refer to the supplied version.

## What can be tried now without hidden circuit QASM?

### Takeaway
Use native bond dimension and PPS options on matched IDs, with the existing cost and cancellation controls. The highest-priority bounded experiment remains the G4 chi64 q4/q0 plus independent q4 PPS level1 window; a GPU MPS pilot is conditional on local elapsed-time evidence.

### Cited Findings
- G4's matched chi16/chi32 subset has rho .8591218413, residual energy .26190966 and 12/45 order reversals. The q4/q0 rows account for 60.49% of its residual energy. - [Saved numerical review](<C:/Users/youss/.codex/worktrees/graded-main/BluQubit/reports/G4_PARTIAL_TREND_REVIEW.md>)
- The saved G4 q0 chi32 CPU/GPU values differ by 6.63e-12. Compute times are 48.593/24.189 seconds, elapsed times 55.055394/44.803906 seconds, and charges $0/$0.20. - [Matched pilot](<C:/Users/youss/.codex/worktrees/graded-main/BluQubit/reports/gpu_matched_pilot.json>)
- The retained G2 review identifies q9 as an unsaturated transition row at chi32 .49444184, more informative than another saturated endpoint. Its older 498/600 outcome is explicitly teammate-attributed. - [Saved refinement review](<C:/Users/youss/.codex/worktrees/graded-main/BluQubit/reports/REFINEMENT_REVIEW.md>)
- The current operating guide requires coherent single-device, identical-options cohorts, $27 exposure protection, fresh quotes and terminal cost reconciliation; GPU and CPU routes are separate cohorts. It documents exact GPU rejection for 36/38-qubit IDs. - [Operating guide](../../docs/history/workflow_final_graded.md)

### Inferences
- Rank offline review of complete G3 first; then the bounded G4 three-job window; conditional matched GPU chi64 feasibility; broader G4 panel; G2 q9 chi64 and transition panel; G3 .001/.0005 at fixed level1. Adapt to actual quote and pilot outcomes rather than a precommitted full sweep.
- For G4, use MPS quoted-runtime ceiling 2,400 seconds with cancellation requested after 600 elapsed seconds, and PPS cancellation at 300 seconds through the supported controller. These are existing campaign proposals, not paper results. Reconcile the coordinator's separately launched q0/q4 checks before any retry.
- Before broader allocation, extend G4 to q1/q19/q37, preserve signed changes and centered shape diagnostics, and seek another precision or an informative independent method. Sparse agreement cannot establish full-vector accuracy.
- The serial GPU runner couples quote admission and timeout; it must not be called as if it already supports CPU split caps. A valid GPU pilot needs its supported bounded timeout and quota gates or a reviewed code change.
- No local Qiskit/Julia/Quantum Rings/cuPauliProp/custom tensor-network switch is executable for hidden named IDs without circuit access. The paper's pauli_sum over one circuit does not combine different Duke IDs into one circuit.

### Gaps
- The coordinator's latest session evidence says current-account G2 is 342/600 at 3.48 hours, G3 baseline has 36 completed rows, G4's accepted 0/1000 remains user-reported with account/attempt unknown, and G4 chi64 q0/q4 checks are now starting. These updates were not independently verified by this read-only subtask; use the coordinator's actual new receipts in the final report.
- This subtask made no live quotes, simulations or submissions. Its report must not be cited as evidence that the proposed experiments completed or improved accuracy.

## How strong are the benchmark and scoring conclusions?

### Takeaway
Treat the paper as a useful set of hypotheses and experimental controls. Neither its runtime rankings nor agreement between two approximate methods establishes this campaign's unknown correlation with truth.

### Cited Findings
- The protocol uses five runs per configuration and plotted means; native MPS CPU/GPU holds implementation fixed, while cross-vendor comparisons also change hardware/software. Pages 3-5. - [Supplied primary source](<D:/BluQubit/papers/alternative approaches.pdf>)
- The paper uses two-core native MPS/PPS CPU, a 16 GB laptop for local PPS, A100 for MPS GPU, and H100/H200/MI300X for PPS GPU comparisons. Pages 3-4 and 12. - [Supplied primary source](<D:/BluQubit/papers/alternative approaches.pdf>)
- All authors are BlueQubit-affiliated; symmetric cost accounting and compile/transpile time are omitted. cuPauliProp points are inferred from external speedup ratios rather than directly measured, with unspecified comparison accelerator. Pages 10-13. - [Supplied primary source](<D:/BluQubit/papers/alternative approaches.pdf>)
- The campaign's shape diagnostic deliberately removes common offset/positive scale and treats correlation between approximations as sensitivity, not score prediction. - [Operating guide](../../docs/history/workflow_final_graded.md)

### Inferences
- GPU agreement at fixed chi supports implementation consistency, not closeness to exact values. Higher chi can move signs or order without guaranteeing a better grade.
- Similar error at the finest and a favorable coarse PPS point means that paying for the deepest sweep need not give the best result per dollar on every problem.
- Keep G2's current-account 258-point headroom separate from the teammate's 102-point headroom. Scores allocate whole-problem attention; they do not supply per-row corrections or evidence that the same account response can be reproduced.
- Runtime and quality fit extrapolations, post-hoc affine corrections, score-derived values, spliced pilot estimates and the peaked-circuit marginal attack are not justified candidate-generation methods here.

### Gaps
- No symmetric cost-to-accuracy data, universal crossover, guaranteed stopping rule, or calibrated score-improvement model is supplied.
- Paper prose around chi256 alternates between approximately 2x, 2-3x and greater-than-3x depending on passage; retain each concrete experiment and avoid a universal precise ratio.
- The finest PPS reference is not an independent exact statevector result, and no hidden-truth labels are available for this campaign. Numerical review must communicate this uncertainty.
