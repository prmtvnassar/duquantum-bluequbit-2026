# BlueQubit / DuQuantum context

Checked 2026-10-23. Keep replies brief, plain, and intuitive. Work on the current personal branch; do not switch or merge until asked. On first review the branch was `prmtvnassar/practice`, with pre-existing edits to study notebooks, `.env.example` deleted, and `papers/` untracked. Recheck `git status` before editing and preserve those changes. Never read or print `.env` or API tokens.

## Challenge

- DuQuantum 2026 / BlueQubit runs 2026-10-24 11:30 ET to 2026-10-25 11:30 ET. Kit, full rules, circuit sizes, and coupon arrive at kickoff.
- Estimate OTOC(2) for 4 hidden circuits by BlueQubit circuit ID: about 140 values, one per qubit. Two sample circuits are inspectable and include exact answers. Hidden circuits must run on BlueQubit; AI is allowed.
- Submit one CSV: `circuit,qubit,estimate`. Each circuit is scored by correlation/SNR; later, harder circuits count more, and ordering matters more than a constant offset. Exact formula, aggregation, and weights are unknown until the kit arrives; follow its scorer.
- The mock invents its circuit sizes, 1:2:3:4 weights, budget, and 12-qubit statevector cap. Rehearse mechanics only; never assume these are real.

## OTOC in one minute

`U` scrambles information; `X_b` is the butterfly; `Z_q` probes qubit `q`. From `|0...0>`:

```text
OTOC(1): U, X_b, Udagger                         -> measure <Z_q>
OTOC(2): U, X_b, Udagger, Z_q, U, X_b, Udagger -> measure <Z_q>
```

OTOC(1) detects whether the evolved butterfly has reached the probe (equivalently, whether it fails to commute with `Z_q`). OTOC(2) repeats the echo around the probe and reveals interference among operator paths. Values are often simple (~1) ahead of the light cone, circuit-specific near its front, and small after deep scrambling. Signed interference makes OTOC(2) hard to approximate: terms that look small midway can later refocus and change the answer.

Qiskit/BlueQubit Pauli labels put qubit 0 at the rightmost character: `IIZ` means `Z` on qubit 0. Validate mapping before writing CSV rows.

## Simulator choices

- **Statevector (`cpu`/`gpu`)**: exact; stores `2^n` amplitudes.
- **MPS (`mps.cpu`/`mps.gpu`)**: bond dimension `chi` controls cost and truncation; works when entanglement stays low. Sweep `chi` and anchor on exact samples.
- **Pauli path (`pauli-path`)**: propagates Pauli terms backward and drops coefficients below threshold `delta`. Good for Clifford/near-Clifford or shallow structure; can collapse on random OTOC(2) echoes. Smaller `delta` costs more.
- Approximate jobs may return plausible but wrong values without warning. Calibrate methods on exact samples, check convergence, and cross-check independent methods where useful.
- At kickoff: read the kit; compare settings on samples; submit a complete low-cost baseline for all hidden rows early; spend the remaining actual credit budget on unstable, high-weight circuits. Use `challenge_tools.score_csv` as ground truth.

## SDK

Official docs checked 2026-10-23; the API reference identifies SDK version 0.18.12b1. `bluequbit.init()` reads `BLUEQUBIT_API_TOKEN`.

```python
r = bq.run(qc, device="mps.cpu", pauli_sum=[("IIZ", 1.0)],
           options={"mps_bond_dimension": 32})
value = r.expectation_value
```

Pauli path uses `options={"pauli_path_truncation_threshold": delta}`; API docs require a threshold above 13 qubits, minimum `1e-5`. `pauli_path_circuit_transpilation_level` is 0-3 (default 2); hold it fixed when comparing. Async: `job = bq.run(..., asynchronous=True)`, then `bq.wait(job.job_id)`; `bq.cancel(job.job_id)` requests cancellation. The marketing docs and API reference spell Pauli-path device names differently; follow the released kit and verify at kickoff.

## Repo map

- `tutorials/study/00-05`: linear algebra/order; SDK basics; simulator choice; Pauli paths; OTOC (key notebook); mock challenge.
- `tutorials/study/otoc_tools.py`: exact echoes, Qiskit circuit helpers, CSV checks, local correlation/SNR stand-in (not the official scorer).
- `tutorials/study/offline_sim.py`: local statevector, Aer MPS, and homegrown Pauli-path lookalikes. Finite-threshold results may differ from BlueQubit's transpilation.
- `tutorials/originals/`: BlueQubit BQ 101/201, OTOC, Pauli-path, QAOA, peaked-circuit, T-count/MITM, and AI-assisted-compute tutorials.
- `src/otoc/` currently holds shared client/token config only. `tasks.md` is a proposed prep plan, not proof its pipeline has been implemented.
- Papers: Brian Swingle's OTOC overview (2018); Google's *Observation of constructive interference at the edge of quantum ergodicity* (2025). Google links OTOC(2) to large-loop Pauli interference; it motivates the challenge but gives no challenge-specific parameters.

## Recheck at kickoff

- Challenge: https://app.bluequbit.io/hackathons/2GMaAenu3iSsIC6Z
- SDK: https://app.bluequbit.io/docs and https://app.bluequbit.io/sdk-docs/index.html
- Released kit README, `challenge_tools` signatures/scorer, CSV template, device support, credits, and circuit weights override every local stand-in.
