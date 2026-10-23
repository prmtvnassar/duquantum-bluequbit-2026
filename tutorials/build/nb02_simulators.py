from nbbuild import code, ex, md

NAME = "02_choosing_a_simulator"

CELLS = [
md("""
# 02 · Choosing a simulator (BQ 201, offline)

Based on BlueQubit's *BQ 201: Choosing a Quantum Circuit Simulator*. Their headline:

> **Entanglement structure, not qubit count, should drive simulator choice.**

You'll measure that yourself on small circuits, then read BlueQubit's own cloud benchmark numbers
(quoted from the tutorial) to calibrate what to expect on the real platform during the hackathon.

| | stores | cost driven by | fails when |
|---|---|---|---|
| **statevector** (`cpu`/`gpu`) | $2^n$ amplitudes | $n$ | $n \\gtrsim 34$ |
| **MPS** (`mps.cpu`/`mps.gpu`) | $n$ tensors, bond dim $\\chi$ | $\\chi$ | entanglement grows |
| **Pauli path** (`pauli-path`) | surviving Pauli terms | threshold $\\delta$ | terms proliferate |
"""),
code("""
import time
import numpy as np
import matplotlib.pyplot as plt
from qiskit import QuantumCircuit
from offline_sim import LocalBQ, z_sum, pauli_path_expectation
from otoc_tools import brickwork, to_qiskit, near_clifford_circuit
import checks

bq = LocalBQ()
rng = np.random.default_rng(7)
plt.rcParams.update({"figure.dpi": 100, "axes.grid": True, "grid.alpha": .3})

def half_entropy(psi):
    n = int(np.log2(len(psi)))
    s2 = np.linalg.svd(np.asarray(psi).reshape(2 ** (n // 2), -1), compute_uv=False) ** 2
    s2 = s2[s2 > 1e-12]
    return float(-(s2 * np.log2(s2)).sum())
print("ready")
"""),
md("""
## 1. The statevector wall

Each amplitude is a complex number of 16 bytes. Every extra qubit doubles the memory. Hardware buys
you a few qubits, never an order of magnitude.
"""),
ex("how many qubits fit?",
   """
   Write `sv_bytes(n)` (memory of an $n$-qubit statevector in bytes) and set `max_qubits_16gb` to the
   largest $n$ whose statevector fits in 16 GB ($16\\times 1024^3$ bytes) and `max_qubits_80gb` for an 80 GB GPU.
   """,
   """
   def sv_bytes(n):
       raise NotImplementedError   # YOUR CODE

   max_qubits_16gb = None
   max_qubits_80gb = None
   """,
   """
   def sv_bytes(n):
       return 16 * 2 ** n

   max_qubits_16gb = max(n for n in range(64) if sv_bytes(n) <= 16 * 1024 ** 3)
   max_qubits_80gb = max(n for n in range(64) if sv_bytes(n) <= 80 * 1024 ** 3)
   """,
   """
   checks.fn("sv_bytes", sv_bytes, [((1,), 32), ((30,), 16 * 2 ** 30)])
   checks.equal("max_qubits_16gb", max_qubits_16gb, 30)
   checks.equal("max_qubits_80gb", max_qubits_80gb, 32, hint="5x more memory buys only log2(5) ~ 2 qubits")
   """),
md("""
## 2. Entanglement grows with depth

We use the same random **brickwork** circuits as the OTOC tutorial: layers of random two-qubit gates
on neighbouring pairs. The cell measures the entanglement across the middle of a 12-qubit row after
each depth. The maximum possible is $n/2 = 6$ bits, which would need $\\chi = 2^6 = 64$.
"""),
code("""
n = 12
depths = range(0, 13)
S = []
for d in depths:
    S.append(np.mean([half_entropy(bq.run(to_qiskit(n, brickwork(n, d, np.random.default_rng(100 * d + k)))).get_statevector())
                      for k in range(3)]))
plt.plot(list(depths), S, "o-")
plt.axhline(n / 2, color="gray", ls=":", label="maximum n/2")
plt.xlabel("brickwork depth"); plt.ylabel("half-chain entropy S (bits)"); plt.legend()
plt.title("Entanglement across the middle cut"); plt.show()
print("chi needed ~ 2^S:", [int(round(2 ** s)) for s in S])
"""),
md("""
Entanglement grows by roughly a bit per layer, then saturates near the maximum. So: **shallow → MPS
is cheap and exact; deep → MPS needs $\\chi$ near $2^{n/2}$, which is no cheaper than a statevector.**

## 3. MPS accuracy vs bond dimension, shallow vs deep

Same 16-qubit row, one shallow circuit (depth 4) and one deep (depth 16). We estimate $\\langle Z_q\\rangle$
on every qubit with MPS at several $\\chi$ and compare with the exact answer.
"""),
code("""
n = 16
chis = [1, 2, 4, 8, 16, 32, 64, 128, 256]   # 256 = 2^(16/2) is always exact for 16 qubits
results = {}
for d in (4, 16):
    U = to_qiskit(n, brickwork(n, d, np.random.default_rng(42 + d)))
    exact = np.array([bq.run(U, "cpu", z_sum(q, n)).expectation_value for q in range(n)])
    errs = []
    for chi in chis:
        est = np.array([bq.run(U, "mps.cpu", z_sum(q, n), options={"mps_bond_dimension": chi}).expectation_value
                        for q in range(n)])
        errs.append(np.max(np.abs(est - exact)))
    results[d] = errs
    plt.semilogy(chis, np.maximum(errs, 1e-16), "o-", label=f"depth {d}")
plt.xscale("log", base=2); plt.xlabel("bond dimension chi"); plt.ylabel("max |error| over qubits")
plt.title("MPS error vs chi (16 qubits)"); plt.legend(); plt.show()
for d, errs in results.items():
    print(f"depth {d:>2}:", "  ".join(f"chi={c}:{e:.1e}" for c, e in zip(chis, errs)))
"""),
ex("pick chi from data",
   """
   From `results` above, set `chi_shallow` and `chi_deep` to the **smallest** $\\chi$ in `chis` whose
   max error is below `1e-6`, for depth 4 and depth 16. (Compute them, don't type numbers.)
   The gap between the two is the entire BQ 201 lesson in one line.
   """,
   """
   chi_shallow = None   # YOUR CODE
   chi_deep = None
   """,
   """
   chi_shallow = min(c for c, e in zip(chis, results[4]) if e < 1e-6)
   chi_deep = min(c for c, e in zip(chis, results[16]) if e < 1e-6)
   """,
   """
   ref_s = min(c for c, e in zip(chis, results[4]) if e < 1e-6)
   ref_d = min(c for c, e in zip(chis, results[16]) if e < 1e-6)
   checks.equal("chi_shallow", chi_shallow, ref_s)
   checks.equal("chi_deep", chi_deep, ref_d, hint="deep circuits need chi close to 2^(n/2) = 256 for exactness")
   if chi_shallow and chi_deep:
       print(f"depth 4 needs chi={chi_shallow}, depth 16 needs chi={chi_deep}: same width, very different cost")
   """),
md("""
## 4. Cost vs bond dimension (on your laptop)

Runtime of MPS grows steeply with $\\chi$ (BlueQubit measured about $\\chi^{2.1}$ on CPU). The cell
times a 30-qubit, depth-10 circuit, far past where we can check exactly, so watch two things:
how the time grows, and whether the answer **stops moving** as $\\chi$ doubles.
"""),
code("""
n30, q30 = 30, 15
U30 = to_qiskit(n30, brickwork(n30, 10, np.random.default_rng(3)))   # 30 qubits, depth 10
rows = []
for chi in [4, 8, 16, 32, 64]:
    t = time.perf_counter()
    v = bq.run(U30, "mps.cpu", z_sum(q30, n30), options={"mps_bond_dimension": chi}).expectation_value
    rows.append((chi, v, time.perf_counter() - t))
    print(f"chi={chi:>4}  <Z_{q30}> = {v:+.5f}   {rows[-1][2]:6.2f} s")
"""),
md("""
## 5. Pauli paths: the threshold is the knob

Pauli-path simulation pushes the measured operator backwards through the circuit as a sum of Pauli
strings and drops terms with $|c| < \\delta$. Smaller $\\delta$ keeps more terms: slower, more accurate.
For generic random circuits, **halving $\\delta$ roughly quadruples the term count** (the bound is
$\\|O\\|^2/\\delta^2$). Near-Clifford circuits barely branch at all.
"""),
code("""
n, d, q = 14, 8, 7
U_rand = to_qiskit(n, brickwork(n, d, np.random.default_rng(11)))
U_nc = near_clifford_circuit(n, d, np.random.default_rng(11), p=0.15)
deltas = [1e-1, 3e-2, 1e-2, 3e-3, 1e-3]
fig, ax = plt.subplots(1, 2, figsize=(11, 3.6))
for U, name in [(U_rand, "random brickwork"), (U_nc, "near-Clifford")]:
    exact = bq.run(U, "cpu", z_sum(q, n)).expectation_value
    terms, errs = [], []
    for dl in deltas:
        v, st = pauli_path_expectation(U, z_sum(q, n), dl)
        terms.append(st["max_terms"]); errs.append(abs(v - exact))
    ax[0].loglog(deltas, terms, "o-", label=name); ax[1].loglog(deltas, np.maximum(errs, 1e-16), "o-", label=name)
for a, yl in zip(ax, ["max Pauli terms held", "|error|"]):
    a.invert_xaxis(); a.set_xlabel("truncation threshold delta"); a.set_ylabel(yl); a.legend()
plt.tight_layout(); plt.show()
"""),
md("""
## 6. BlueQubit's cloud numbers (quoted from BQ 201)

You can't benchmark their GPUs offline, so here are the measured medians from the tutorial
(Mazumder et al. 2026, *Benchmarking Zero-Setup Quantum Circuit Simulators*). Use them to budget time
and credits on challenge day.
"""),
code("""
# MPS, quantum-volume circuit n=40, d=10, 1 shot: run time (s) vs bond dimension
BOND_CPU_S = {32: 21.2, 64: 59.8, 128: 152.2, 256: 721.4, 384: 2007.2, 512: 4524.2, 768: 13009.1, 1024: 28111.3}
BOND_GPU_S = {32: 32.6, 64: 63.0, 128: 144.9, 256: 355.3, 384: 661.8, 512: 1141.4, 768: 2373.2, 1024: 4250.3,
              1280: 6357.2, 1536: 9271.6}
# Pauli path, 127-qubit kicked Ising, <Z_62>: run time (s) vs threshold
PPS_DELTA = [1e-2, 5e-3, 1e-3, 5e-4, 1e-4, 5e-5, 2.5e-5]
PPS_CPU_S = [0.78, 0.92, 4.13, 13.77, 323.50, 1295.07, 5710.51]
PPS_GPU_S = [1.71, 0.73, 0.92, 0.96, 1.21, 1.58, 3.52]

fig, ax = plt.subplots(1, 2, figsize=(11, 3.8))
ax[0].loglog(list(BOND_CPU_S), list(BOND_CPU_S.values()), "o-", label="mps.cpu")
ax[0].loglog(list(BOND_GPU_S), list(BOND_GPU_S.values()), "s--", label="mps.gpu")
ax[0].set(xlabel="bond dimension chi", ylabel="run time (s)", title="MPS (n=40, d=10)"); ax[0].legend()
ax[1].loglog(PPS_DELTA, PPS_CPU_S, "o-", label="pauli-path (CPU)")
ax[1].loglog(PPS_DELTA, PPS_GPU_S, "s--", label="pauli-path.gpu")
ax[1].invert_xaxis(); ax[1].set(xlabel="threshold delta", ylabel="run time (s)", title="Pauli path (127q kicked Ising)"); ax[1].legend()
plt.tight_layout(); plt.show()
"""),
md("""
**Decision rules from BQ 201** (thresholds are BlueQubit's measurements):

| question | rule |
|---|---|
| need the full state? | statevector only up to $n \\approx 34$; `cpu` below $n\\approx20$, `gpu` above |
| MPS, which device? | $\\chi \\lesssim 128$: `mps.cpu`; $\\chi \\gtrsim 256$: `mps.gpu` (2× at 256, ~7× at 1024) |
| very large $\\chi$? | $\\chi > 1024$: only `mps.gpu` finishes |
| expectation values only? | `pauli-path`; CPU for $\\delta \\gtrsim 10^{-3}$, GPU below |

Remember from the OTOC tutorial: on BlueQubit, `cpu`, `mps.cpu` and `pauli-path` jobs are **free**;
GPU jobs cost credits. (Your free account also refused multi-term `pauli_sum` on `pauli-path` until
the balance is ≥ $25.)
"""),
ex("which device would you pick?",
   """
   Fill `picks` with one device string per scenario, from
   `"cpu"`, `"gpu"`, `"mps.cpu"`, `"mps.gpu"`, `"pauli-path"`, `"pauli-path.gpu"`, using the table.
   """,
   """
   picks = {
       "16-qubit circuit, need exact <Z_q>": None,
       "28-qubit circuit, need exact <Z_q>": None,
       "40-qubit shallow 1D circuit, chi ~ 32 is enough": None,
       "40-qubit circuit needing chi ~ 2048": None,
       "100-qubit near-Clifford circuit, one <Z_q>, delta = 1e-2": None,
   }
   """,
   """
   picks = {
       "16-qubit circuit, need exact <Z_q>": "cpu",
       "28-qubit circuit, need exact <Z_q>": "gpu",
       "40-qubit shallow 1D circuit, chi ~ 32 is enough": "mps.cpu",
       "40-qubit circuit needing chi ~ 2048": "mps.gpu",
       "100-qubit near-Clifford circuit, one <Z_q>, delta = 1e-2": "pauli-path",
   }
   """,
   """
   answer = ["cpu", "gpu", "mps.cpu", "mps.gpu", "pauli-path"]
   for (k, v), a in zip(picks.items(), answer):
       checks.equal(k, v, a)
   """),
md("""
## 7. Trusting an approximate answer

An approximate simulator can finish fast and hand you a **wrong number with no warning**. BQ 201's
three habits:

1. **Sweep the knob until the answer stops moving.** Run $\\chi$, then $2\\chi$. If it moved, you weren't converged.
2. **Anchor against something exact.** Check your settings on a small instance you *can* solve exactly.
   Two approximate methods agreeing is *consistency*, not correctness.
3. **Don't expect monotonic convergence.** Their Pauli-path run on the 127-qubit circuit got *worse*
   from $\\delta=10^{-2}$ to $5\\times10^{-5}$ before recovering.
"""),
code("""
PPS_EXPECTATION = [0.2580, 0.2805, 0.2492, 0.2183, 0.1562, 0.1520, 0.1714]   # BQ 201, <Z_62> vs delta
O_EXACT = 0.2955
plt.semilogx(PPS_DELTA, PPS_EXPECTATION, "o-", label="pauli-path estimate")
plt.axhline(O_EXACT, color="k", ls="--", label="converged value")
plt.gca().invert_xaxis(); plt.xlabel("delta"); plt.ylabel("<Z_62>"); plt.legend()
plt.title("Tighter threshold, worse answer (for a while)"); plt.show()
"""),
ex("a convergence sweep you can reuse in the hackathon",
   """
   Write `sweep(run, settings, tol)`: call `run(s)` for each setting in order (e.g. increasing $\\chi$)
   and return `(setting, value)` for the **first** setting whose value differs from the previous
   one by less than `tol`. If none converge, return the last `(setting, value)`.
   Then use it on the 30-qubit circuit `U30` from section 4 (probe qubit `q30`) with `chis = [4, 8, 16, 32, 64, 128]`, `tol=1e-3`,
   and store the result in `converged`.
   """,
   """
   def sweep(run, settings, tol):
       raise NotImplementedError   # YOUR CODE

   converged = None   # YOUR CODE: sweep(lambda chi: ..., [4, 8, 16, 32, 64, 128], 1e-3)
   """,
   """
   def sweep(run, settings, tol):
       prev = None
       for s in settings:
           v = run(s)
           if prev is not None and abs(v - prev) < tol:
               return s, v
           prev = v
       return s, v

   converged = sweep(lambda chi: bq.run(U30, "mps.cpu", z_sum(q30, n30), options={"mps_bond_dimension": chi}).expectation_value,
                     [4, 8, 16, 32, 64, 128], 1e-3)
   """,
   """
   fake = {1: 0.5, 2: 0.3, 4: 0.31, 8: 0.3101}
   checks.fn("sweep", lambda: sweep(fake.get, [1, 2, 4, 8], 0.05), [((), (4, 0.31))])
   checks.fn("sweep (never converges)", lambda: sweep(fake.get, [1, 2], 0.01), [((), (2, 0.3))])
   checks.truthy("converged on the 30-qubit circuit", converged is not None and len(converged) == 2,
                 hint="pass a lambda that runs mps.cpu with mps_bond_dimension=chi", todo=converged is None)
   if converged: print("converged at chi =", converged[0], "value", round(converged[1], 5))
   """),
md("""
## Recap

- Statevector: exact, memory-bound ($n\\lesssim 34$).
- MPS: cost set by $\\chi$; needs $\\chi\\approx 2^S$; great for shallow/1D/low-entanglement, hopeless for deep scrambling.
- Pauli path: cost set by $\\delta$ (halve $\\delta$ → ~4× terms); great when the operator stays small (near-Clifford, shallow).
- **Always** sweep to convergence and anchor on exact small cases.

**Next:** `03_pauli_path_simulation.ipynb`, how Pauli paths work inside.
"""),
]
