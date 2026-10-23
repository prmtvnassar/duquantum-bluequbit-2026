# Offline study notebooks: BlueQubit OTOC(2) challenge prep

Everything here runs **without internet**: no BlueQubit account, no credits, no data downloads.

## Start

```powershell
cd D:\BluQubit
.\.venv\Scripts\activate
jupyter lab tutorials\study
```

Pick the kernel **Python (BluQubit)**. Work through the notebooks in order. Each ✏️ exercise has a
check cell under it that prints ✅ PASS / ❌ FAIL (with a hint) / ⏳ TODO. Worked solutions are in
`study/solutions/*_solved.ipynb`. Try first, peek second.

| # | Notebook | Based on | Time | You'll be able to |
|---|---|---|---|---|
| 00 | `00_linear_algebra_warmup` | new | 1-1.5 h | states, gates, expectation values, qubit order, commutators, Pauli decomposition |
| 01 | `01_bq101_offline` | BQ 101 | 45 min | run circuits, shots vs statevector, GHZ on 40 qubits with MPS, entanglement entropy |
| 02 | `02_choosing_a_simulator` | BQ 201 | 1 h | pick statevector / MPS / Pauli path from structure, sweep to convergence |
| 03 | `03_pauli_path_simulation` | Pauli-Path Simulation | 1-1.5 h | write your own Pauli-path simulator, choose a truncation threshold |
| 04 | `04_otoc_tutorial_offline` | **OTOC tutorial** (the key one) | 2 h | OTOC(1)/(2), echoes, light cones, why OTOC(2) is hard, scoring |
| 05 | `05_mock_challenge` | new | 1-1.5 h | the full hackathon workflow on hidden circuits, with a budget and a scored CSV |

Short on time? Do **04 → 05**, then 03 and 02.

## What's in `study/`

- `offline_sim.py`: `LocalBQ`, an offline look-alike of `bluequbit.init(...)` with the same
  `run(circuit, device=..., pauli_sum=..., options=...)` call. Devices: `cpu` (exact statevector),
  `mps.cpu` (qiskit-aer MPS, option `mps_bond_dimension`), `pauli-path` (our own implementation,
  option `pauli_path_truncation_threshold`). Code you write against it ports to the real platform by
  swapping `LocalBQ()` for `bluequbit.init(token)`.
- `otoc_tools.py`: BlueQubit's helper file shipped with the OTOC tutorial (circuits, exact OTOCs,
  CSV I/O, `score()`). Likely close to the real kit's `challenge_tools`.
- `mock_challenge.py`: hidden circuits by ID, sample circuits with exact answers, a budget, a scorer.
- `checks.py`: the exercise checks.

**Checked against BlueQubit's published numbers:** exact 0.11541958 on the Pauli-path tutorial circuit,
OTOC(1) = +0.506305 and OTOC(2) = +0.007352 on the OTOC tutorial's 16-qubit test circuit, and the same
Pauli-path behaviour (collapse to 0 on random echoes, convergence on near-Clifford ones).

## Other folders

- `originals/`: the original BlueQubit tutorial notebooks (non-premium ones), downloaded for offline
  reading. They still contain cloud calls, so they need a token to *run*. The study notebooks above
  cover the four relevant to OTOCs; the others (QAOA, T-count, peaked circuits, AI agents) are here for
  reference only.
- `build/`: the scripts that generate the study notebooks (`python tutorials/build/verify.py` rebuilds and
  tests all of them; solved notebooks must pass every check).
