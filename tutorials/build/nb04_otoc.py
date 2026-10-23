"""The BlueQubit OTOC tutorial, offline, with exercises inserted.

Original cells are read from tutorials/originals/otoc-intro.ipynb so the explanations stay exactly
as BlueQubit wrote them. Part 5 (cloud runs) is replaced by the same experiments on LocalBQ.
"""
import json
from pathlib import Path

from nbbuild import code, ex, md

NAME = "04_otoc_tutorial_offline"

_ORIG = json.loads((Path(__file__).resolve().parents[1] / "originals" / "otoc-intro.ipynb").read_text(encoding="utf-8"))
_C = ["".join(c["source"]) for c in _ORIG["cells"]]


def orig(i):
    kind = _ORIG["cells"][i]["cell_type"]
    return md(_C[i]) if kind == "markdown" else code(_C[i])


_part4_rest, _part5_intro = _C[20].split("---\n# Part 5", 1)

CELLS = [
md("""
> **Offline edition.** This is BlueQubit's *Out-of-time-order correlators (OTOCs): a hands-on tutorial*,
> unchanged except for: (1) Part 5 runs on `LocalBQ` (offline exact / MPS / Pauli-path) instead of the
> cloud, and (2) ✏️ exercises with self-checks after each part. The original is in
> `../originals/otoc-intro.ipynb`. **This is the most important notebook for the hackathon.**
"""),
orig(0),
md("""
---
# Part 0: Setup (offline)

Everything you need is already in this folder: `otoc_tools.py` (BlueQubit's helpers),
`offline_sim.py` (offline simulators) and `checks.py`. Pick the **Python (BluQubit)** kernel and run the cell below.
"""),
code(_C[2] + """

from offline_sim import LocalBQ, z_sum, pauli_path_expectation
import checks
bq = LocalBQ()
"""),
orig(3),
ex("check the OTOC identity numerically",
   """
   Part 1 claims $\\mathcal C = \\tfrac12\\langle [A,M]^\\dagger[A,M]\\rangle = 1 - \\mathrm{Re}\\,F$ with
   $A = B(t) = U^\\dagger B U$ and $F = \\langle A M A M\\rangle$. Verify it on 3 qubits with a random $U$.

   Use full matrices: `U` (8×8), `B` = $X$ on qubit 0, `M` = $Z$ on qubit 2 (Qiskit order:
   `np.kron(Z, np.kron(I, I))` is Z on qubit 2). Set `C_lhs` and `C_rhs` (both real numbers) and
   `F` (complex). Expectation values are taken in $|000\\rangle$ (the vector `e0` below).
   """,
   """
   from scipy.stats import unitary_group
   U = unitary_group.rvs(8, random_state=1)
   I2 = np.eye(2)
   e0 = np.zeros(8); e0[0] = 1
   B = np.kron(I2, np.kron(I2, X))      # X on qubit 0
   M = np.kron(Z, np.kron(I2, I2))      # Z on qubit 2

   F = None       # YOUR CODE
   C_lhs = None
   C_rhs = None
   """,
   """
   from scipy.stats import unitary_group
   U = unitary_group.rvs(8, random_state=1)
   I2 = np.eye(2)
   e0 = np.zeros(8); e0[0] = 1
   B = np.kron(I2, np.kron(I2, X))
   M = np.kron(Z, np.kron(I2, I2))

   A = U.conj().T @ B @ U
   comm = A @ M - M @ A
   F = e0 @ A @ M @ A @ M @ e0
   C_lhs = float(np.real(e0 @ comm.conj().T @ comm @ e0) / 2)
   C_rhs = float(1 - np.real(F))
   """,
   """
   checks.truthy("C_lhs == C_rhs", C_lhs is not None and abs(C_lhs - C_rhs) < 1e-10,
                 hint="A = U^dag B U; C_lhs = <comm^dag comm>/2; C_rhs = 1 - Re F", todo=C_lhs is None)
   checks.truthy("0 <= C <= 2", C_lhs is not None and -1e-12 <= C_lhs <= 2 + 1e-12, todo=C_lhs is None)
   """),
orig(4), orig(5), orig(6), orig(7), orig(8),
ex("run the echo yourself",
   """
   Using only `zero`, `run_U`, `apply1`, `run_Udag`, `expZ` and `X` from `otoc_tools`, compute OTOC(1)
   at every qubit for the circuit `gates` above (n=6, b=0) and store the list in `my_otoc1`.
   The check compares with `exact_otoc1`.
   """,
   """
   my_otoc1 = None   # YOUR CODE: psi = ... ; [expZ(psi, q) for q in range(n)]
   """,
   """
   psi = run_Udag(apply1(run_U(zero(n), gates), X, b), gates)
   my_otoc1 = [expZ(psi, q) for q in range(n)]
   """,
   """
   checks.close("my_otoc1", my_otoc1, exact_otoc1(n, gates, b), tol=1e-10)
   """),
orig(9), orig(10), orig(11),
ex("predict the light cone exactly",
   """
   A qubit $q$ can only show OTOC(1) $\\neq 1$ if the support of $B(t) = U^\\dagger X_b U$ reaches it.
   In the Heisenberg picture $B$ is conjugated by the **last** layer first, so walk the layers
   **backwards**: start with `support = {b}`; for each layer from last to first, every gate on a pair
   $(i, i+1)$ that touches the support adds both qubits.

   Write `light_cone(n, b, depth)` returning that set. Layer $t$ uses pairs starting at $i = t \\bmod 2$
   (see `brickwork` in `otoc_tools.py`). The check also confirms every qubit **outside** your set has
   OTOC(1) exactly 1 on random circuits.
   """,
   """
   def light_cone(n, b, depth):
       raise NotImplementedError   # YOUR CODE
   """,
   """
   def light_cone(n, b, depth):
       support = {b}
       for t in reversed(range(depth)):
           for i in range(t % 2, n - 1, 2):
               if i in support or i + 1 in support:
                   support |= {i, i + 1}
       return support
   """,
   """
   def _ref(n, b, depth):
       s = {b}
       for t in reversed(range(depth)):
           for i in range(t % 2, n - 1, 2):
               if i in s or i + 1 in s: s |= {i, i + 1}
       return s
   cases = [((10, 0, d), _ref(10, 0, d)) for d in (0, 1, 2, 3, 5)] + [((10, 5, d), _ref(10, 5, d)) for d in (1, 2, 4)]
   ok = checks.fn("light_cone", light_cone, cases)
   if ok:
       r = np.random.default_rng(5)
       for (nn, bb, dd) in [(10, 0, 4), (10, 5, 3), (9, 3, 2)]:
           o1 = exact_otoc1(nn, brickwork(nn, dd, r), bb)
           outside = [q for q in range(nn) if q not in light_cone(nn, bb, dd)]
           assert np.allclose(o1[outside], 1), "outside the cone OTOC(1) should be 1"
       print("   and outside the cone OTOC(1) == 1 on random circuits, as predicted")
   """,
   hint="For b=5, depth 1: layer 0 has pairs (0,1),(2,3),(4,5),... so the support becomes {4, 5}."),
orig(12), orig(13), orig(14), orig(15),
ex("build the OTOC(2) echo yourself",
   """
   Write `my_otoc2(n, gates, b, q)` with the statevector helpers: run the OTOC(1) echo, apply $Z_q$,
   run the echo again, and return $\\langle Z_q\\rangle$. Compare with `exact_otoc2`.
   """,
   """
   def my_otoc2(n, gates, b, q):
       raise NotImplementedError   # YOUR CODE
   """,
   """
   def my_otoc2(n, gates, b, q):
       echo = lambda psi: run_Udag(apply1(run_U(psi, gates), X, b), gates)
       psi = echo(zero(n))
       psi = apply1(psi, Z, q)
       return expZ(echo(psi), q)
   """,
   """
   r = np.random.default_rng(9)
   cases = []
   for (nn, dd, bb, qq) in [(6, 4, 0, 3), (8, 6, 2, 7), (7, 5, 0, 1)]:
       g = brickwork(nn, dd, r)
       cases.append(((nn, g, bb, qq), exact_otoc2(nn, g, bb, qq)))
   checks.fn("my_otoc2", my_otoc2, cases, tol=1e-10)
   """),
ex("the butterfly's Pauli weights are probabilities",
   """
   Part 3 says: write $B(t) = \\sum_P a_P P$; then the $a_P^2$ add up to 1, like probabilities.
   For $n=6$, depth 3, $b=0$, build the matrix $B(t) = U^\\dagger X_0 U$ (use `qiskit.quantum_info.Operator(to_qiskit(n, g)).data`)
   and decompose it with `SparsePauliOp.from_operator`. Set:

   - `total_weight` = $\\sum_P a_P^2$ (expect 1),
   - `reached` = a list, for each qubit $q$, of the total weight $\\sum a_P^2$ over strings with $X$ or $Y$ on $q$:
     "how much of the butterfly has reached $q$ (in a way $Z_q$ can detect)". It should be 0 outside the light cone.
   """,
   """
   from qiskit.quantum_info import Operator, SparsePauliOp
   n6, g6 = 6, brickwork(6, 3, np.random.default_rng(3))
   total_weight = None   # YOUR CODE
   reached = None
   """,
   """
   from qiskit.quantum_info import Operator, SparsePauliOp
   n6, g6 = 6, brickwork(6, 3, np.random.default_rng(3))
   Umat = Operator(to_qiskit(n6, g6)).data
   Xb = SparsePauliOp("I" * 5 + "X").to_matrix()
   Bt = SparsePauliOp.from_operator(Umat.conj().T @ Xb @ Umat)
   a2 = np.abs(Bt.coeffs) ** 2
   labels = [p.to_label() for p in Bt.paulis]
   total_weight = float(a2.sum())
   reached = [float(sum(w for w, L in zip(a2, labels) if L[n6 - 1 - q] in "XY")) for q in range(n6)]
   """,
   """
   checks.close("total_weight", total_weight, 1.0, tol=1e-9)
   checks.truthy("reached is 0 outside the light cone",
                 reached is not None and all(abs(reached[q]) < 1e-9 for q in range(6) if q not in _ref(6, 0, 3)),
                 hint="label character for qubit q is L[n-1-q]", todo=reached is None)
   if reached: print("weight that reached each qubit:", np.round(reached, 3))
   """),
orig(16), orig(17), orig(18), orig(19),
md(_part4_rest),
md("""
---
# Part 5: Running the simulators (offline edition)

BlueQubit offers `cpu`/`gpu` (exact statevector), `mps.cpu`/`mps.gpu` (option `mps_bond_dimension`)
and `pauli-path` (option `pauli_path_truncation_threshold`, smallest allowed `1e-5`). Here `LocalBQ`
plays all three with the same call. On the real platform `cpu`, `mps.cpu` and `pauli-path` are free;
GPU jobs use credits.

> **Note: qubit order.** BlueQubit and Qiskit write Pauli labels with qubit 0 as the **rightmost**
> character, so $Z_0$ on 3 qubits is `"IIZ"`. Getting this backwards gives you the value for the wrong
> qubit without any error message. Use `z_label(q, n)` and you never have to think about it.

The cells below use a 16-qubit circuit built right here, small enough for an exact answer. First,
check that the "platform" gives the same answers as `otoc_tools`' exact simulator.
"""),
code("""
def bq_expz(bq, circuit, q, device="cpu", **options):
    # <Z_q> on the (offline) platform. Same code works with bq = bluequbit.init(token).
    r = bq.run(circuit, device=device, pauli_sum=[(z_label(q, circuit.num_qubits), 1.0)], options=options or None)
    ev = r.expectation_value
    return float(ev[0] if isinstance(ev, (list, tuple)) else ev)

n, d, b, q = 16, 12, 0, 7
g = brickwork(n, d, np.random.default_rng(16))
U = to_qiskit(n, g)
tests = [("OTOC1", echo_circuit(U, b, order=1), float(exact_otoc1(n, g, b)[q])),
         ("OTOC2", echo_circuit(U, b, q, order=2), exact_otoc2(n, g, b, q))]
for kind, qc, exact in tests:
    print(f"{kind} at q={q}: exact {exact:+.6f}   platform cpu {bq_expz(bq, qc, q):+.6f}")
"""),
md("""
Now MPS at several bond dimensions (BlueQubit's version of this cell cost about $5 of GPU credits; offline it's free).
"""),
code("""
import time
chis = [2, 4, 8, 16, 32, 64, 128]
t0 = time.time()
for kind, qc, exact in tests:
    est = [bq_expz(bq, qc, q, device="mps.cpu", mps_bond_dimension=c) for c in chis]
    plt.semilogx(chis, est, "o-", base=2, label=f"{kind} MPS estimate")
    plt.axhline(exact, ls=":", color=plt.gca().lines[-1].get_color(), label=f"{kind} exact")
plt.xlabel("bond dimension chi"); plt.ylabel("<Z_q>"); plt.title("MPS vs exact (16 qubits, depth 12)"); plt.legend(); plt.show()
print(f"{time.time() - t0:.0f}s")
"""),
md("""
Compare with the figure from BlueQubit's real run (saved with the tutorial):
"""),
code("""
from IPython.display import Image, display
display(Image(filename="otoc_bluequbit_plots/mps_vs_exact.png", width=520))
"""),
md("""
Now Pauli paths at several thresholds, on the random circuit and on a **near-Clifford** circuit
(mostly Clifford gates plus a few $R_z$ rotations), where Pauli paths are expected to do well.
"""),
code("""
q_nc = 5
U_nc = near_clifford_circuit(n, d, np.random.default_rng(3), p=0.25)
tests_nc = [("OTOC1", echo_circuit(U_nc, b, order=1)), ("OTOC2", echo_circuit(U_nc, b, q_nc, order=2))]
tests_nc = [(kind, qc, simulate_expz(qc, q_nc)) for kind, qc in tests_nc]       # exact, by statevector

thresholds = [1e-1, 3e-2, 1e-2, 1e-3]    # smaller keeps more Pauli terms: slower, more accurate
fig, axes = plt.subplots(1, 2, figsize=(11, 3.8), sharey=True)
for ax, title, cases, qq in [(axes[0], "Random circuit (from above)", tests, q),
                             (axes[1], "Near-Clifford circuit", tests_nc, q_nc)]:
    for kind, qc, exact in cases:
        est = [bq_expz(bq, qc, qq, device="pauli-path", pauli_path_truncation_threshold=t) for t in thresholds]
        ax.semilogx(thresholds, est, "o-", label=f"{kind} Pauli-path estimate")
        ax.axhline(exact, ls=":", color=ax.lines[-1].get_color(), label=f"{kind} exact")
    ax.invert_xaxis()
    ax.set(xlabel="truncation threshold", title=title); ax.legend(fontsize=8)
axes[0].set_ylabel("<Z_q>"); plt.tight_layout(); plt.show()
display(Image(filename="otoc_bluequbit_plots/pauli_path_vs_exact.png", width=700))
"""),
orig(25),
ex("calibrate a method on a known circuit, then apply it",
   """
   This is the hackathon workflow in miniature. On the **near-Clifford** circuit `U_nc` (n=16, b=0):

   1. compute the exact OTOC(2) at every check qubit $q$ (`simulate_expz(echo_circuit(U_nc, b, q, order=2), q)`), store as `truth_nc`;
   2. estimate the same with Pauli paths at threshold `1e-2`, store as `est_nc`;
   3. score with `score(est_nc, truth_nc)` and store the dict in `sc_nc`.

   You should find a high correlation $r$. Then try MPS with $\\chi = 8$ on the same 16 checks if you like.
   """,
   """
   truth_nc = None   # YOUR CODE
   est_nc = None
   sc_nc = None
   """,
   """
   truth_nc = [simulate_expz(echo_circuit(U_nc, b, qq, order=2), qq) for qq in range(n)]
   est_nc = [bq_expz(bq, echo_circuit(U_nc, b, qq, order=2), qq, device="pauli-path", pauli_path_truncation_threshold=1e-2)
             for qq in range(n)]
   sc_nc = score(est_nc, truth_nc)
   """,
   """
   checks.truthy("truth_nc has 16 values", truth_nc is not None and len(truth_nc) == 16, todo=truth_nc is None)
   checks.truthy("Pauli paths track the near-Clifford OTOC(2) (r > 0.9)", sc_nc is not None and sc_nc["r"] > 0.9,
                 hint="threshold 1e-2 on device='pauli-path'", todo=sc_nc is None)
   if sc_nc: print({k: round(v, 3) for k, v in sc_nc.items()})
   """),
orig(26), orig(27), orig(28),
ex("what the score rewards",
   """
   Using `truth` from the cell above (40 exact OTOC(2) values), build three estimate arrays and score them:

   - `est_affine` = `0.3 * truth + 0.5` (wrong scale **and** offset),
   - `est_flipped` = `-truth`,
   - `est_rank` = the **ranks** of `truth` (0 for the smallest, 39 for the largest; `np.argsort(np.argsort(truth))`).

   Store `score(...)` dicts as `sc_affine`, `sc_flipped`, `sc_rank`. Predict first: which gets $r = 1$?
   Which gets SNR 0? (Negative $r$ counts as 0.)
   """,
   """
   sc_affine = None   # YOUR CODE
   sc_flipped = None
   sc_rank = None
   """,
   """
   sc_affine = score(0.3 * truth + 0.5, truth)
   sc_flipped = score(-truth, truth)
   sc_rank = score(np.argsort(np.argsort(truth)), truth)
   """,
   """
   checks.close("affine r", None if sc_affine is None else sc_affine["r"], 1.0, tol=1e-9,
                hint="correlation ignores scale and offset")
   checks.close("flipped snr", None if sc_flipped is None else sc_flipped["snr"], 0.0, tol=1e-9,
                hint="negative r counts as 0")
   checks.truthy("rank-only estimate scores well (r > 0.8)", sc_rank is not None and sc_rank["r"] > 0.8, todo=sc_rank is None)
   """),
md("""
## Takeaways for the hackathon

1. **What you submit:** OTOC(2) $=\\langle Z_q\\rangle$ at the end of the echo U, X_b, U†, Z_q, U, X_b, U†, one number per check qubit.
2. **Where the signal is:** just behind the butterfly's front. Far ahead it's exactly 1, far behind ≈ 0.
   Your `light_cone()` tells you which qubits are trivially 1 **for free**.
3. **Score = correlation:** scale and offset don't matter; ordering does. Getting the *trivial* qubits right
   (exact 1s vs ≈0s) already buys correlation. Spend compute on the band in between.
4. **Methods fail differently:** MPS needs $\\chi\\approx 2^S$ at the most entangled point of the echo;
   Pauli paths collapse to 0 on random circuits but shine on near-Clifford ones. Calibrate both on the
   samples (which come with exact answers) before trusting either on hidden circuits.

**Next:** `05_mock_challenge.ipynb`, a full dress rehearsal with hidden circuits, a budget, and a CSV to score.
"""),
]
