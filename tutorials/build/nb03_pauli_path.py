from nbbuild import code, ex, md

NAME = "03_pauli_path_simulation"

CELLS = [
md("""
# 03 · Pauli-path simulation, from the inside

Based on BlueQubit's *Pauli-Path Simulation of Quantum Circuits*. You'll derive the one rule the
method rests on, build a small Pauli-path simulator yourself, then use truncation on circuits
too big for a statevector, including a 1D version of IBM's "utility" kicked-Ising experiment.

**Why you care for the hackathon:** OTOCs are expectation values, and `pauli-path` is one of the
two approximate methods BlueQubit gives you. Knowing *when* it fails (it does fail on random OTOC(2)
echoes) is worth as much as knowing how to call it.
"""),
code("""
import time
import numpy as np
import matplotlib.pyplot as plt
from qiskit import QuantumCircuit
from qiskit.circuit.library import n_local
from qiskit.quantum_info import Operator, Statevector, SparsePauliOp
from offline_sim import LocalBQ, z_sum, pauli_path_expectation, conjugation_table
import checks

bq = LocalBQ()
plt.rcParams.update({"figure.dpi": 100, "axes.grid": True, "grid.alpha": .3})
I2 = np.eye(2); X = np.array([[0, 1], [1, 0]]); Y = np.array([[0, -1j], [1j, 0]]); Z = np.diag([1, -1])
P1 = {"I": I2, "X": X, "Y": Y, "Z": Z}
print("ready")
"""),
md("""
## 1. Two pictures, same number

**Schrödinger:** evolve the state, $|\\psi\\rangle = U|0\\rangle$, then compute $\\langle\\psi|O|\\psi\\rangle$.

**Heisenberg:** evolve the observable, $O \\to U^\\dagger O U$, then evaluate it on $|0\\rangle$:
$\\langle O\\rangle = \\langle 0|U^\\dagger O U|0\\rangle$.

For a circuit $U = G_K\\cdots G_2G_1$ ($G_1$ first), $U^\\dagger O U = G_1^\\dagger\\cdots G_K^\\dagger\\,O\\,G_K\\cdots G_1$:
the observable walks through the circuit **backwards, one gate at a time**.

Evaluating on $|0\\cdots0\\rangle$ at the end is easy: a Pauli string has expectation **1** there if
it contains only $I$ and $Z$, and **0** if it contains any $X$ or $Y$. So
$\\langle O\\rangle = $ sum of the coefficients of the all-$I$/$Z$ strings.
"""),
ex("evaluate a Pauli sum on |0...0>",
   """
   Write `eval_on_zero(obs)` for `obs` a dict `{label: coeff}` (e.g. `{"ZI": 0.5, "XZ": 2.0}`):
   return the sum of coefficients of labels made only of `I` and `Z`.
   """,
   """
   def eval_on_zero(obs):
       raise NotImplementedError   # YOUR CODE
   """,
   """
   def eval_on_zero(obs):
       return float(sum(c for lab, c in obs.items() if set(lab) <= {"I", "Z"}))
   """,
   """
   checks.fn("eval_on_zero", eval_on_zero,
             [(({"ZI": 0.5, "XZ": 2.0},), 0.5), (({"II": 1.0, "ZZ": -0.25, "YI": 9.0},), 0.75), (({"X": 1.0},), 0.0)])
   """),
md("""
## 2. The branching rule

Write each rotation gate as $U_\\sigma(\\theta) = e^{-i\\theta\\sigma/2} = \\cos\\frac\\theta2\\,I - i\\sin\\frac\\theta2\\,\\sigma$
for a Pauli $\\sigma$ ($R_Z$ has $\\sigma = Z$, $R_X$ has $\\sigma = X$, $R_{ZZ}$ has $\\sigma = Z\\otimes Z$).
Then for a Pauli $P$:

$$U_\\sigma^\\dagger P\\, U_\\sigma = \\begin{cases} P & \\text{if } P \\text{ commutes with } \\sigma\\\\ \\cos\\theta\\, P + i\\sin\\theta\\,\\sigma P & \\text{if they anticommute.}\\end{cases}$$

So each rotation either leaves a Pauli string alone or **splits it into two**. After $k$ rotations,
up to $2^k$ strings: that's the "paths". Clifford gates (H, S, CNOT, CZ) never split: one Pauli in,
one (±) Pauli out.
"""),
ex("the rule for Rz",
   """
   Using the rule (with $ZX = iY$ and $ZY = -iX$), write `rz_rule(P, theta)` for a single-qubit Pauli
   label `P` in `"IXYZ"`, returning the dict `{label: coeff}` of $R_Z(\\theta)^\\dagger P R_Z(\\theta)$.
   The check compares with brute-force matrix multiplication.
   """,
   """
   def rz_rule(P, theta):
       # YOUR CODE: I and Z commute with Z; X and Y split into two terms
       raise NotImplementedError
   """,
   """
   def rz_rule(P, theta):
       c, s = np.cos(theta), np.sin(theta)
       return {"I": {"I": 1.0}, "Z": {"Z": 1.0},
               "X": {"X": c, "Y": -s},          # i sin(theta) * (ZX = iY)  ->  -sin(theta) Y
               "Y": {"Y": c, "X": s}}[P]        # i sin(theta) * (ZY = -iX) -> +sin(theta) X
   """,
   """
   def brute(P, theta):
       Rz = np.diag([np.exp(-1j * theta / 2), np.exp(1j * theta / 2)])
       M = Rz.conj().T @ P1[P] @ Rz
       return [float(np.real(np.trace(P1[L] @ M) / 2)) for L in "IXYZ"]
   as_vec = lambda d: [d.get(L, 0.0) for L in "IXYZ"]
   checks.fn("rz_rule", lambda P, t: as_vec(rz_rule(P, t)),
             [((P, t), brute(P, t)) for P in "IXYZ" for t in (0.3, 1.2, -2.0)])
   """),
ex("Clifford gates move Paulis without splitting",
   """
   `conjugation_table(G)` (from `offline_sim`) returns how a 1- or 2-qubit gate maps each local Pauli.
   Use brute force or the table to answer, in **Qiskit order** (qubit 0 rightmost):

   - `cz_x0`: the label of $CZ^\\dagger X_0\\, CZ$ (X on qubit 0 through a CZ). Expect a single string.
   - `cx_z1`: the label of $CX^\\dagger Z_1\\, CX$ for a CNOT with control 0, target 1.

   Store plain labels like `"ZX"` (ignore signs; both come out +1 here).
   """,
   """
   cz_x0 = None   # YOUR CODE
   cx_z1 = None
   """,
   """
   def heis(G, label):
       M = G.conj().T @ SparsePauliOp(label).to_matrix() @ G
       return SparsePauliOp.from_operator(M).simplify()
   qc = QuantumCircuit(2); qc.cz(0, 1); CZ = Operator(qc).data
   qc = QuantumCircuit(2); qc.cx(0, 1); CX = Operator(qc).data
   cz_x0 = heis(CZ, "IX").paulis[0].to_label()
   cx_z1 = heis(CX, "ZI").paulis[0].to_label()
   """,
   """
   checks.equal("cz_x0", cz_x0, "ZX", hint="CZ turns X_0 into X_0 Z_1")
   checks.equal("cx_z1", cx_z1, "ZZ", hint="Z on the target spreads back onto the control")
   """),
md("""
## 3. Build your own Pauli-path simulator

Below is a helper `gate_map(G)` that turns a gate matrix into a lookup:
`local label in → {local label out: coefficient}` (labels in Qiskit order over the gate's own qubits).
Your job is the main loop.
"""),
code("""
from itertools import product

def gate_map(G):
    k = int(np.log2(G.shape[0]))
    labels = ["".join(p) for p in product("IXYZ", repeat=k)]      # Qiskit order within the gate
    mats = {L: SparsePauliOp(L).to_matrix() for L in labels}
    out = {}
    for Lin in labels:
        M = G.conj().T @ mats[Lin] @ G
        out[Lin] = {Lout: float(np.real(np.trace(mats[Lout] @ M))) / 2 ** k
                    for Lout in labels if abs(np.trace(mats[Lout] @ M)) > 1e-12}
    return out

def gates_of(qc):
    "(matrix, [qubits]) for each gate, in circuit order."
    return [(Operator(ins.operation).data, [qc.find_bit(b).index for b in ins.qubits]) for ins in qc.data]

def get_local(label, qubits):
    "Local label of `label` on `qubits` (Qiskit order: the gate's first qubit is the rightmost character)."
    n = len(label)
    return "".join(label[n - 1 - q] for q in reversed(qubits))

def set_local(label, qubits, local):
    n = len(label); chars = list(label)
    for q, ch in zip(reversed(qubits), local):
        chars[n - 1 - q] = ch
    return "".join(chars)

print(get_local("XYZ", [0]), get_local("XYZ", [0, 2]), set_local("III", [0, 2], "XZ"))
"""),
ex("the Pauli-path main loop",
   """
   Write `my_pauli_path(qc, obs, threshold=0.0)`:

   1. go through `gates_of(qc)` **in reverse** order;
   2. for each term `(label, c)` of the current dict, look up `gate_map(G)[get_local(label, qubits)]`,
      and for each `(local_out, m)` add `c * m` to the new dict at `set_local(label, qubits, local_out)`;
   3. after each gate drop terms with `abs(coeff) < threshold`;
   4. at the end return `eval_on_zero(...)`.

   (Cache `gate_map` results in a dict keyed by `G.tobytes()` if it feels slow.)
   """,
   """
   def my_pauli_path(qc, obs, threshold=0.0):
       raise NotImplementedError   # YOUR CODE
   """,
   """
   def my_pauli_path(qc, obs, threshold=0.0):
       cache = {}
       cur = dict(obs)
       for G, qubits in reversed(gates_of(qc)):
           gm = cache.setdefault(G.tobytes(), gate_map(G))
           new = {}
           for label, c in cur.items():
               for local_out, m in gm[get_local(label, qubits)].items():
                   key = set_local(label, qubits, local_out)
                   new[key] = new.get(key, 0.0) + c * m
           cur = {k: v for k, v in new.items() if abs(v) >= max(threshold, 1e-15)}
       return eval_on_zero(cur)
   """,
   """
   qc = QuantumCircuit(3); qc.h([0, 1, 2]); qc.ry(0.3, 0); qc.rz(0.6, 1); qc.rx(0.7, 2); qc.cx(0, 2); qc.rzz(0.4, 1, 2)
   obs = {"XYZ": 0.5, "XXX": 0.2, "XII": 0.3, "III": 0.4}
   exact = float(np.real(Statevector(qc).expectation_value(SparsePauliOp.from_list(list(obs.items())))))
   checks.fn("my_pauli_path (exact)", lambda: my_pauli_path(qc, obs), [((), exact)], tol=1e-9)
   qc2 = n_local(5, "ry", "cx", reps=2, entanglement="linear").assign_parameters(np.linspace(0.1, 1, 15)).decompose()
   checks.fn("my_pauli_path vs offline_sim", lambda: my_pauli_path(qc2, {"IIZII": 1.0}),
             [((), pauli_path_expectation(qc2, [("IIZII", 1.0)])[0])], tol=1e-9)
   """),
md("""
## 4. Truncation: trading accuracy for memory

Exact Pauli paths blow up: on BlueQubit's 8-qubit example the operator ends up spread over almost
all $4^8$ strings. The fix: after every gate, **drop terms with $|c| < \\delta$**. Unitarity bounds
the number of survivors by $\\|O\\|^2/\\delta^2$, and for random circuits halving $\\delta$ roughly
quadruples the count.

This is the exact circuit from the BlueQubit tutorial (their exact answer: **0.11541958**).
"""),
code("""
qc8 = n_local(8, rotation_blocks="ry", entanglement_blocks="cx", reps=4, entanglement="circular")
qc8.assign_parameters(np.random.default_rng(101).random(qc8.num_parameters)[::-1], inplace=True)
qc8 = qc8.decompose()
obs8 = [("ZZ" + "I" * 6, 0.5), ("I" * 6 + "XX", -1.5)]

exact8 = bq.run(qc8, "cpu", obs8).expectation_value
print(f"statevector exact: {exact8:.8f}   (BlueQubit tutorial: 0.11541958)")
deltas = [2.0 ** -k for k in range(2, 15)]
vals, terms = [], []
for d in deltas:
    v, st = pauli_path_expectation(qc8, obs8, d)
    vals.append(v); terms.append(st["max_terms"])
fig, ax = plt.subplots(1, 2, figsize=(11, 3.6))
ax[0].semilogx(deltas, vals, "o-"); ax[0].axhline(exact8, color="k", ls="--", label="exact")
ax[0].invert_xaxis(); ax[0].set(xlabel="delta", ylabel="estimate", title="estimate vs threshold"); ax[0].legend()
ax[1].loglog(deltas, terms, "o-", label="max terms held")
ax[1].loglog(deltas, [min(4**8, 2.0 / d**2) for d in deltas], ":", label="bound ||O||^2/delta^2 (capped at 4^8)")
ax[1].invert_xaxis(); ax[1].set(xlabel="delta", ylabel="Pauli terms", title="memory vs threshold"); ax[1].legend()
plt.tight_layout(); plt.show()
"""),
ex("how fast do terms grow?",
   """
   Fit a straight line to `log(terms)` vs `log(1/delta)` over the **middle** of the sweep
   (`deltas[3:9]`, before the count saturates at $4^8$) and store the slope in `growth_exponent`.
   The bound predicts at most 2 ("halve delta, 4x terms"). On this small, structured 8-qubit
   circuit expect noticeably less than 2: the bound is a worst case, reached by large random circuits.
   """,
   """
   growth_exponent = None   # YOUR CODE (np.polyfit(x, y, 1)[0] gives the slope)
   """,
   """
   x = np.log(1 / np.array(deltas[3:9])); y = np.log(np.array(terms[3:9]))
   growth_exponent = float(np.polyfit(x, y, 1)[0])
   """,
   """
   checks.truthy("growth_exponent between 0.5 and 2.2", growth_exponent is not None and 0.5 < growth_exponent < 2.2,
                 hint="np.polyfit(np.log(1/d), np.log(terms), 1)[0]", todo=growth_exponent is None)
   if growth_exponent: print(f"terms ~ (1/delta)^{growth_exponent:.2f}")
   """),
md("""
## 5. A 1D kicked-Ising "utility" experiment, offline

IBM's 127-qubit experiment repeated a Trotter step: $R_{ZZ}(-\\pi/2)$ on every edge, then $R_X(\\theta)$ on
every qubit, and measured $\\langle Z_{62}\\rangle$. Pauli paths reproduced it classically. We do the same
on a 20-qubit chain, where a statevector can still check us.

**Notice:** $R_{ZZ}(-\\pi/2)$ is a Clifford gate. Only the $R_X(\\theta)$ gates split Pauli strings, so at
$\\theta = 0$ and $\\theta = \\pi/2$ everything is Clifford, and Pauli paths are exact and instant.
"""),
code("""
def kicked_ising(n, steps, theta):
    qc = QuantumCircuit(n)
    for _ in range(steps):
        for i in range(n - 1):
            qc.rzz(-np.pi / 2, i, i + 1)
        for i in range(n):
            qc.rx(theta, i)
    return qc

n_ki, steps, q_ki = 20, 5, 10
thetas = [0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 1.0, np.pi / 2]
ex_vals, pp_vals = [], []
t0 = time.time()
for th in thetas:
    qc = kicked_ising(n_ki, steps, th)
    ex_vals.append(bq.run(qc, "cpu", z_sum(q_ki, n_ki)).expectation_value)
    pp_vals.append(bq.run(qc, "pauli-path", z_sum(q_ki, n_ki), options={"pauli_path_truncation_threshold": 1e-3}).expectation_value)
print(f"done in {time.time() - t0:.0f}s")
plt.plot(thetas, ex_vals, "o-", label="statevector (exact)")
plt.plot(thetas, pp_vals, "s--", mfc="none", label="pauli-path, delta=1e-3")
plt.xlabel("theta_X"); plt.ylabel(f"<Z_{q_ki}>"); plt.title(f"{n_ki}-qubit kicked Ising, {steps} steps"); plt.legend(); plt.show()
"""),
ex("choose a threshold from data",
   """
   For $\\theta = 0.7$ (the hardest-looking point), run Pauli paths at
   `cands = [1e-1, 3e-2, 1e-2, 3e-3, 1e-3, 3e-4]` and set `delta_needed` to the **largest** threshold
   whose error against the exact value `ex_vals[thetas.index(0.7)]` is below 0.01.
   This is exactly the calibration you'll do on the challenge's sample circuits.
   """,
   """
   cands = [1e-1, 3e-2, 1e-2, 3e-3, 1e-3, 3e-4]
   delta_needed = None   # YOUR CODE
   """,
   """
   cands = [1e-1, 3e-2, 1e-2, 3e-3, 1e-3, 3e-4]
   target = ex_vals[thetas.index(0.7)]
   qc = kicked_ising(n_ki, steps, 0.7)
   errs = {d: abs(pauli_path_expectation(qc, z_sum(q_ki, n_ki), d)[0] - target) for d in cands}
   delta_needed = max(d for d, e in errs.items() if e < 0.01)
   """,
   """
   target = ex_vals[thetas.index(0.7)]
   qcc = kicked_ising(n_ki, steps, 0.7)
   ref = max(d for d in [1e-1, 3e-2, 1e-2, 3e-3, 1e-3, 3e-4]
             if abs(pauli_path_expectation(qcc, z_sum(q_ki, n_ki), d)[0] - target) < 0.01)
   checks.equal("delta_needed", delta_needed, ref)
   """),
md("""
## 6. Where Pauli paths break: the echo (preview of the OTOC notebook)

An OTOC echo runs $U$, a tiny kick, then $U^\\dagger$. Exactly, the operator spreads out through one
half and **refocuses** through the other. With truncation, terms that look small midway, and get
dropped, are precisely the ones that would have refocused. On random circuits the estimate collapses
to 0. On near-Clifford circuits (few splitting gates) it survives. You'll see this in notebook 04.

**Extra knob on BlueQubit's GPU device:** `pauli_path_weight_cutoff` also drops strings acting on too
many qubits (`options={"pauli_path_truncation_threshold": d, "pauli_path_weight_cutoff": w}`).

## Recap

- Heisenberg picture: push $O$ backwards; at the end, sum the coefficients of all-$I$/$Z$ strings.
- Rotations split a Pauli string in two when they anticommute; Cliffords just relabel it.
- Truncation $\\delta$ bounds memory by $\\|O\\|^2/\\delta^2$; always calibrate $\\delta$ against exact small cases.
- Pauli paths love near-Clifford/shallow circuits and hate deep random echoes.

**Next:** `04_otoc_tutorial_offline.ipynb`, the main event.
"""),
]
