# SDK routes for GPU precision recovery

## Which native GPU configurations can use the hidden graded IDs?

### Takeaway

The original account's installed SDK 0.19.0b1 recognizes stored circuit IDs, MPS GPU and PPS GPU. Five estimate-only requests accepted the requested G4/G3 configurations on October 24, 2026; this establishes quote availability, not successful execution, runtime, accuracy or admission under campaign limits. [Dated quote evidence](../../reports/alternative_gpu_quotes.json)

### Cited Findings

- Stored IDs are encoded as a `stored` circuit payload containing the ID, without downloading gates. The SDK forwards the observable and options in that payload. The campaign adapter's quote path explicitly uses `estimate_only=True` and `force_run=False`, and records the returned estimate in the original-account quote/event ledger. [Installed serialization](D:/BluQubit/.venv312/Lib/site-packages/bluequbit/circuit_serialization.py:95), [installed jobs API](D:/BluQubit/.venv312/Lib/site-packages/bluequbit/api/jobs.py:91), [campaign quote implementation](D:/BluQubit/src/otoc/bluequbit_adapter.py:154)
- Installed SDK constants include `mps.gpu` and `pauli-path.gpu`; MPS GPU bond dimensions 64 and 128 are below its maximum of 4000. PPS supports an explicit coefficient threshold **at least 1e-5** and native transpilation levels **0, 1, 2, 3**, default 2. The option validator applies the 1e-5 lower bound without a GPU exemption. [Installed constants](D:/BluQubit/.venv312/Lib/site-packages/bluequbit/job_metadata_constants.py:18), [installed option validation](D:/BluQubit/.venv312/Lib/site-packages/bluequbit/bluequbit_client.py:234)
- The public API reference currently identifies itself as 0.18.12b1 and omits PPS GPU from its listed devices, while documenting MPS GPU, the same PPS precision floor and the four native levels. The installed 0.19.0b1 code and the successful PPS GPU quote requests are stronger evidence for this account's available interface. [Public API reference](https://app.bluequbit.io/sdk-docs/bluequbit.sdk.html), [dated installed-version and quote evidence](../../reports/alternative_gpu_quotes.json)
- The supplied paper runs some PPS GPU experiments below 1e-5, but this is not an available precision setting in the installed public SDK/campaign adapter. Its benchmark engine access must not be assumed to equal this account's supported API. No below-floor request was attempted. [Supplied paper, pages 9-10](<D:/BluQubit/papers/alternative approaches.pdf>), [installed option validation](D:/BluQubit/.venv312/Lib/site-packages/bluequbit/bluequbit_client.py:273), [campaign validation](D:/BluQubit/src/otoc/bluequbit_adapter.py:25)

Fresh original-account quotes, UTC on 2026-10-24:

| ID | Device/options | Time | USD | Quoted runtime | Evidence |
| --- | --- | --- | ---: | ---: | --- |
| G4 q4 | `mps.gpu`, chi64 | 19:09:25 | 1.08 | 968.2 s | [Quote](../../reports/alternative_gpu_quotes.json) |
| G4 q4 | `mps.gpu`, chi128 | 19:09:27 | 2.73 | 2448.2 s | [Quote](../../reports/alternative_gpu_quotes.json) |
| G4 q4 | `pauli-path.gpu`, epsilon 0.001, level 1 | 19:09:28 | 0.67 | 0.1 s | [Quote](../../reports/alternative_gpu_quotes.json) |
| G4 q4 | `pauli-path.gpu`, epsilon 0.0001, level 1 | 19:09:29 | 0.67 | 0.1 s | [Quote](../../reports/alternative_gpu_quotes.json) |
| G3 q35 | `pauli-path.gpu`, epsilon 0.0001, level 1 | 19:09:29 | 0.67 | 0.1 s | [Quote](../../reports/alternative_gpu_quotes.json) |

All five returned no error and a warning that actual runtime may differ. The new worktree's credential matched the original account before quoting; credentials were neither printed nor saved. Only quote requests were made; canonical quote artifacts/events were written through the existing adapter. [Quote evidence and scope](../../reports/alternative_gpu_quotes.json)

### Inferences

- A GPU route is implementable with the existing SDK by passing the same stored ID and target `Z_q`, changing the device and explicitly preserving native precision/level options. No hidden circuit extraction or third-party installation is necessary. A successful estimate is not confirmation that execution will complete under quota and timeout constraints. [Installed request code](D:/BluQubit/.venv312/Lib/site-packages/bluequbit/api/jobs.py:91), [quotes](../../reports/alternative_gpu_quotes.json)
- The identical PPS 0.1-second estimates at two precisions are inadequate for predicting useful GPU speedup. Treat them as an admission input requiring a bounded measured pilot, not as a 0.1-second completion promise. The matched G4 chi32 GPU trial already illustrates why queue/elapsed time can erase much of a compute-only speedup. [Fresh quotes](../../reports/alternative_gpu_quotes.json), [matched GPU pilot](../../reports/gpu_matched_pilot.json)

### Gaps

- No GPU PPS job was executed by this research; GPU PPS output consistency, actual runtime, memory limits, exact accelerator model and actual charge remain unmeasured for these IDs. The quote responses contain no guarantees for those quantities. [Quote response fields and scope](../../reports/alternative_gpu_quotes.json)
- Levels 0, 2 and 3 are supported by the installed validator, but this quote tranche tested only level 1. No claim is made about their per-ID performance. [Installed levels](D:/BluQubit/.venv312/Lib/site-packages/bluequbit/job_metadata_constants.py:63), [quote tranche](../../reports/alternative_gpu_quotes.json)

## Can the paper's local alternatives directly solve the hidden graded programs?

### Takeaway

Quantum Rings, Qiskit pauli-prop/OBP and PauliPropagation.jl require circuit gates or an explicit circuit representation. The graded programs provide opaque BlueQubit IDs, so these local methods are not direct replacement routes for G2-G4 under the current access model. [Graded access rules](../../problems/README.md), [Quantum Rings circuit input](https://www.quantumrings.com/doc/usage/qasm_import.html), [Qiskit propagation](https://github.com/Qiskit/pauli-prop), [Julia propagation example](https://github.com/SparqleSim/PauliPropagation.jl)

### Cited Findings

- Quantum Rings accepts OpenQASM 2/3 files and circuit objects constructed from QASM. Its documented inputs do not supply BlueQubit private stored circuits. [Quantum Rings QASM import and execution](https://www.quantumrings.com/doc/usage/qasm_import.html)
- The paper's Qiskit baseline is **`Qiskit/pauli-prop`**, a Rust-accelerated Python library; it is not identical to the separate Qiskit OBP add-on used in this repository's exploratory work. The lower-level propagation engine evolves operators through gate sequences. [Paper reference 4](<D:/BluQubit/papers/alternative approaches.pdf>), [Qiskit pauli-prop repository](https://github.com/Qiskit/pauli-prop)
- Qiskit OBP backpropagates observables through a supplied circuit and exposes operator-size and truncation-error budgets. Its documentation cautions that high non-Clifford content can cause prohibitive truncation error early. This supports investigating near-Clifford samples, not treating OBP as an automatic solution for the hidden Haar grid. [IBM OBP documentation](https://quantum.cloud.ibm.com/docs/en/addons/qiskit-addon-obp)
- PauliPropagation.jl's example constructs a gate circuit and parameters, then calls `propagate(circuit, observable, parameters; ...)`. Its coefficient and weight truncation controls therefore presuppose the circuit description. Its current GPU extension is described as limited and not yet performant; this does not unlock BlueQubit hidden IDs. [Official Julia repository and example](https://github.com/SparqleSim/PauliPropagation.jl)
- The paper's PPS speedup study is a 127-qubit kicked-Ising circuit with a specific observable, and its large GPU advantages arise at large retained Pauli counts. The MPS comparison holds the BlueQubit Quimb-based implementation fixed while changing hardware. The paper also reports nonmonotonic PPS error versus threshold and discloses that its authors are BlueQubit-affiliated. These are useful hypotheses and limitations, not G4-specific validation. [Supplied paper, pages 3-4, 9-10 and 13](<D:/BluQubit/papers/alternative approaches.pdf>)
- The benchmark repository is public, with runners and circuit-generation/loading logic, but its README's `benchmarking/...` instructions differ from the visible root directories (`mps_tests`, `pauli_path_tests`, etc.). It is evidence for reproducibility intent, not a drop-in hidden-ID runner. [Paper repository](https://github.com/arulrhikm/mps-pps-zero-setup-benchmarks)

### Inferences

- Installing local alternatives now would not remove the missing-circuit-input constraint. Their useful current role is public-sample validation or future work on provided circuits; the practical graded recovery routes are native BlueQubit CPU/GPU modes already accepting stored IDs. [Graded circuit access](../../problems/README.md), [SDK stored-circuit representation](D:/BluQubit/.venv312/Lib/site-packages/bluequbit/circuit_serialization.py:95), [native quotes](../../reports/alternative_gpu_quotes.json)
- Keep native threshold, native transpilation level, local coefficient cutoff and OBP error budget distinct. Equal numeric settings across these implementations are not equal accuracy guarantees. [Installed native semantics](D:/BluQubit/.venv312/Lib/site-packages/bluequbit/bluequbit_client.py:400), [IBM OBP controls](https://quantum.cloud.ibm.com/docs/en/addons/qiskit-addon-obp)

### Gaps

- No authoritative source found exposes these challenge IDs to Quantum Rings or local Qiskit/Julia engines. No private circuit export, API workaround, browser bypass or new installation was attempted. [Available stored-ID interface](D:/BluQubit/.venv312/Lib/site-packages/bluequbit/circuit_serialization.py:95), [quote-only research scope](../../reports/alternative_gpu_quotes.json)

## Which routes should be considered next within the existing budget and GPU limits?

### Takeaway

Finish evaluating the current bounded CPU chi64 diagnostics before deciding that GPU MPS is necessary. The most affordable new GPU hypothesis is a small, explicitly bounded PPS level-1 diagnostic; broad GPU MPS completion is not feasible at the representative quotes under the $27 planning ceiling. These are proposed priorities, not execution approvals. [Current policy](../../configs/workflow_final.json), [fresh quotes](../../reports/alternative_gpu_quotes.json)

### Cited Findings

- The saved account snapshot at 19:09:29 UTC had $0.20 known charges, 24.189 GPU seconds total and in the rolling hour, and no unknown terminal charges. Against 27000 total seconds and 2700 seconds per rolling hour, arithmetic headroom was 26975.811 and 2675.811 seconds respectively. This snapshot excludes future commitments as spendable cash and must not replace live admission reconciliation. [Snapshot and quota arithmetic](../../reports/alternative_gpu_quotes.json)
- CPU G3 q35 at native PPS level 1 epsilon 0.001 completed in 39.553 compute seconds at -0.0321978060. Its epsilon 0.0003 attempt was canceled after 179.147 compute seconds with $0 terminal cost. This supplies a concrete time-limited precision branch to test on GPU; there is no existing GPU PPS result for comparison. [Related saved receipts](../../reports/alternative_gpu_quotes.json)
- The earlier matched G4 q0 chi32 GPU run agreed with CPU within 6.63e-12, used 24.189 compute seconds, and billed $0.20. Elapsed time improved only from 55.055 to 44.804 seconds. This measured result supports possible device consistency at that one MPS configuration, not universal numerical equivalence or GPU savings. [Matched GPU receipt comparison](../../reports/gpu_matched_pilot.json)
- Representative full-cohort arithmetic is $41.04 for 38 G4 GPU chi64 rows and $103.74 for GPU chi128. GPU PPS at $0.67 would be $25.46 for 38 G4 rows or $24.12 for 36 G3 rows, before other jobs/commitments. These are multiplications of one-ID quotes, not all-row prices or authorized plans. [Quote arithmetic](../../reports/alternative_gpu_quotes.json)
- Ordinary jobs have a 600-second cap; the 900-second exception is for chi32. Both new GPU MPS quotes exceed 600 seconds. The explicit bounded cohort controller accepts CPU devices only. The current serial planner can compare GPU routes for non-coverage candidates, but must retain dollar, timeout, deadline and GPU-usage gates. [Policy](../../configs/workflow_final.json), [controller device scope](../../src/otoc/cohort_batch.py:25), [serial route comparison](../../src/otoc/graded.py:249)

### Inferences

1. **First GPU diagnostic candidate: G4 q4 PPS level 1, epsilon 0.001, then 0.0001 if useful.** Each currently quotes $0.67. The pair would characterize actual elapsed time and within-GPU precision sensitivity, while the CPU MPS diagnostics characterize a separate approximation. Keep this as a small diagnostic branch; one or two values cannot form or validate a 38-row submission vector. [Quotes](../../reports/alternative_gpu_quotes.json), [G4 sensitivity review](../../reports/G4_PARTIAL_TREND_REVIEW.md)
2. **Next targeted recovery: G3 q35 PPS GPU level 1 at 0.0001**, after preserving the CPU baseline and its commitments. This addresses an observed CPU precision/runtime obstacle for $0.67 quoted. A same-precision CPU/GPU comparison would still be desirable before interpreting changes as precision alone; the 0.001 GPU control would need its own fresh quote. [G3 saved receipts and finer GPU quote](../../reports/alternative_gpu_quotes.json)
3. **Conditional GPU MPS fallback: chi64 at q4 only if CPU chi64 is operationally inadequate.** It quotes $1.08/968.2 seconds and needs an explicit compatible execution/time policy; it cannot be sent through the CPU-only controller. Its quoted duration fits the saved rolling GPU headroom, but a 600-second cancellation request may still interrupt it. [Quote and quota evidence](../../reports/alternative_gpu_quotes.json), [runtime/device constraints](../../configs/workflow_final.json)
4. **Defer GPU chi128 bulk work.** A single q4 estimate quotes 2448.2 seconds, about 91.5% of the saved remaining rolling-hour quota. Chi64 plus chi128 would exceed that snapshot's rolling allowance if both consumed their quoted compute in the same hour. The cost of a full coherent chi128 GPU vector is also incompatible with the planning ceiling. [Quoted costs/times and quota arithmetic](../../reports/alternative_gpu_quotes.json)
5. **Do not splice isolated GPU values into CPU submissions.** Complete cohorts remain defined by one device and identical full options. Retain raw outputs, count actual charges plus outstanding quotes and other baseline reserves, and re-quote immediately before any approved execution. No signs, row order or fitted values should be changed to exploit feedback. [Coherent selection](../../src/otoc/coherent_selection.py:56), [current workflow](../../docs/history/workflow_final_graded.md)

### Gaps

- Actual GPU PPS queue/compute time, billed cost and precision sensitivity are unknown. The paper's roughly 1700-fold comparison is not an estimate for these OTOC programs. Any pilot should measure elapsed time and actual billing before expanding. [Supplied benchmark scope, pages 9-10](<D:/BluQubit/papers/alternative approaches.pdf>), [quote-only evidence](../../reports/alternative_gpu_quotes.json)
- Fresh quotes do not reveal hidden target values and cannot establish that chi64/128 or a tighter PPS threshold will improve the official score. The controller remains CPU-only; this research did not change execution code, run jobs, or authorize a GPU launch. [Quotes and research scope](../../reports/alternative_gpu_quotes.json), [controller](../../src/otoc/cohort_batch.py:25)
