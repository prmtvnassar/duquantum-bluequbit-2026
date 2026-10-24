# BlueQubit capabilities and challenge constraints

## What exactly do the documented precision controls change?

### Takeaway
The SDK exposes distinct, method-specific controls; neither parameter maps directly to an absolute error tolerance. The backend-specific convergence threshold must be measured on representative circuits.

### Cited Findings
- `mps_bond_dimension` caps the number of Schmidt coefficients retained at each SVD truncation; excess coefficients are discarded. The default `None` imposes no bond cap. It applies to `mps.cpu` and `mps.gpu`. — [BlueQubit SDK API reference](https://app.bluequbit.io/sdk-docs/bluequbit.sdk.html)
- `pauli_path_truncation_threshold` drops Pauli operators whose absolute coefficient falls below the threshold after each propagation step. Smaller thresholds retain more terms, with more runtime, and the documented minimum is `1e-5`. A threshold must be supplied for circuits with more than 13 qubits; `None` is documented as exact for circuits with at most 13 qubits. — [BlueQubit SDK API reference](https://app.bluequbit.io/sdk-docs/bluequbit.sdk.html)
- PPS transpilation level is an integer from 0 to 3, default 2. It changes the conversion to rotation gates; the SDK cautions that levels can produce slightly different expectation values and level 3 may be time consuming. — [BlueQubit SDK API reference](https://app.bluequbit.io/sdk-docs/bluequbit.sdk.html)
- BlueQubit's own discussion says PPS coefficient truncation can accumulate error with circuit depth and that guarantees from the cited Pauli-path literature apply to circuit families rather than every individual run. — [BlueQubit PPS article](https://www.bluequbit.io/blog/pauli-path-simulators)
- The SDK's `BQClient.run` names `mps.cpu`, `mps.gpu`, and `pauli-path`; the general platform device table names `pauli-path.cpu` and `pauli-path.gpu`. — [SDK API reference](https://app.bluequbit.io/sdk-docs/bluequbit.sdk.html); [platform docs](https://app.bluequbit.io/docs)

### Inferences
- A fixed numerical agreement threshold cannot be inferred from `chi` or `epsilon` alone. For OTOC, the team must test whether each parameter genuinely changes the output through the challenge wrapper and estimate task-specific errors on exact samples.
- Different PPS transpilation levels provide an extra sensitivity diagnostic, but their spread is not an error bar or an accuracy guarantee.

### Gaps
- Whether the challenge wrapper forwards these settings and which PPS device name it accepts is not documented in publicly accessible SDK material.
- No task-specific typical MPS–PPS divergence on the OTOC challenge was found.

## What error, cost, status, and cancellation information does the SDK expose?

### Takeaway
The documented API supports polling and cancellation requests and reports completed-job expectations and costs. It does not document a numerical accuracy certificate, discarded-weight history, or per-qubit streaming output, so a stop decision appears implementable between jobs rather than within a running simulation.

### Cited Findings
- `BQClient.run(..., asynchronous=True)` returns immediately; `wait(job_ids)` waits for completion; `get(job_ids)` retrieves current metadata; `search` can filter by run status, including `PENDING`, `QUEUED`, `RUNNING`, `COMPLETED`, `CANCELED`, and failures. — [BlueQubit SDK API reference](https://app.bluequbit.io/sdk-docs/bluequbit.sdk.html)
- `BQClient.cancel(job_ids)` submits a cancellation request; the API reference does not promise synchronous cancellation. `wait` timeout raises an exception identifying unfinished job IDs; the `run` timeout refers to waiting when `asynchronous=False`. — [BlueQubit SDK API reference](https://app.bluequbit.io/sdk-docs/bluequbit.sdk.html)
- `JobResult` documents `expectation_value` as float or list of floats, `cost` and `estimated_cost` in US dollars, `run_time_ms`, `queue_time_ms`, `estimated_runtime`, status-based `ok`, and `run_results` for supplementary data such as `mps_build_time`. An asynchronous result may initially contain only partial **metadata**, such as job ID. — [BlueQubit SDK API reference](https://app.bluequbit.io/sdk-docs/bluequbit.sdk.html)
- `BQClient.estimate()` is documented only for `cpu`, `gpu`, and `quantum`, and its runtime/cost output is explicitly approximate; MPS/PPS devices are absent from that method's listed support. — [BlueQubit SDK API reference](https://app.bluequbit.io/sdk-docs/bluequbit.sdk.html)
- The general platform docs list standard CPU job limits and prices, including a 15-minute and 1,000-jobs/day free tier for `mps.cpu` and `pauli-path.cpu`; these are platform terms, not published challenge credit terms. — [BlueQubit platform docs](https://app.bluequbit.io/docs)

### Inferences
- For an already running whole-circuit job, agreement among some qubits cannot be assumed to save compute: one can request cancellation of the entire job, but no partial qubit results or proportional refund are documented. Use agreement to decide whether to **launch the next higher-precision job** after this one completes, unless the kit proves incremental output and billing behavior.
- Log actual `cost`, queue time, and run time for completed jobs to estimate marginal cost. Do not plan MPS/PPS refinement solely from `BQClient.estimate()`.

### Gaps
- No publicly documented `JobResult` numerical error bound, MPS discarded Schmidt-weight record, PPS discarded-coefficient mass, or incremental observable output was found in the SDK reference.
- Whether canceled jobs consume credits, whether results from other observables remain available after cancellation, and whether billing is per observable or whole circuit must be tested or learned from the challenge kit.

## What challenge scoring and kit facts are confirmed as of 2026-10-23?

### Takeaway
The public accessible sources establish the event window and a correlation-oriented task, but the precise score formula, sample scorer interface, row count, and execution granularity remain unverified from the current accessible official material.

### Cited Findings
- BlueQubit's company feed advertises a 24-hour Duke challenge beginning October 24 at 11:30 a.m. ET and ending October 25 at 11:30 a.m. ET, with compute credits issued at kickoff. — [BlueQubit LinkedIn company feed](https://www.linkedin.com/company/bluequbit/)
- A BlueQubit company post in that feed describes around 10 hidden circuits, about 50 observable expectation values, circuit-ID submission to the simulator, and signal-to-noise/correlation scoring. This conflicts with the counts in the local October 22 pre-release design document (4 circuits and approximately 140 values). — [BlueQubit LinkedIn company feed](https://www.linkedin.com/company/bluequbit/)
- The BlueQubit SDK documents a `pauli_sum` argument that can be one Pauli sum or a list of them and an `expectation_value` that can be a float or list, but this does not establish that the competition wrapper will execute/bill all requested OTOC qubits as one job. — [BlueQubit SDK API reference](https://app.bluequbit.io/sdk-docs/bluequbit.sdk.html)

### Inferences
- Use the released template, kit README, and scorer as authority when available; do not tune stopping thresholds against a presumed Pearson formula or assume the pre-release row count.
- A per-qubit stop rule is useful only if qubits are executable/billable independently. If a run returns many observables in one job, choose whether to stop at the job or circuit level using score-weighted vector changes and the job's total cost.

### Gaps
- The exact hackathon page URL from the design document could not be opened via the available web tool, and a public release kit was not found in targeted searches. Therefore exact `score_csv` behavior, CSV rows, wrapper signature, option forwarding, and credit policies remain unconfirmed.
