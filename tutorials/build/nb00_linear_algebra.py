from nbbuild import code, ex, md

NAME = "00_linear_algebra_warmup"

CELLS = [
md("""
# 00 · Linear algebra warm-up for quantum circuits

**Goal:** get comfortable with the handful of linear-algebra moves that everything else in this
hackathon uses. No prior quantum knowledge needed beyond "a qubit is like a bit".

What you'll be able to do by the end:

1. treat a quantum state as a list of numbers (a vector) and turn it into measurement probabilities,
2. treat a gate as a grid of numbers (a matrix) and apply it,
3. compute an **expectation value**, the one number per qubit the challenge asks for,
4. build multi-qubit operators with the **tensor product**, and get the **qubit order** right,
5. check whether two operators **commute**, and move an operator through a gate (**conjugation**),
6. write any 2×2 or 4×4 matrix as a sum of **Pauli matrices**.

Everything runs offline. Each ✏️ exercise has a check cell under it that prints ✅ / ❌ / ⏳.
Stuck? Open the hint, or peek at `solutions/00_linear_algebra_warmup_solved.ipynb`.
"""),
code("""
import numpy as np
import checks
np.set_printoptions(precision=3, suppress=True)

# The four single-qubit Pauli matrices, plus Hadamard. Memorise these four little grids.
I = np.eye(2, dtype=complex)
X = np.array([[0, 1], [1, 0]], dtype=complex)      # bit flip
Y = np.array([[0, -1j], [1j, 0]], dtype=complex)
Z = np.array([[1, 0], [0, -1]], dtype=complex)     # sign flip on |1>
H = np.array([[1, 1], [1, -1]], dtype=complex) / np.sqrt(2)

ket0 = np.array([1, 0], dtype=complex)   # |0>
ket1 = np.array([0, 1], dtype=complex)   # |1>
print("ready")
"""),
md("""
## 1. A state is a vector

One qubit is described by two complex numbers (**amplitudes**): $|\\psi\\rangle = a|0\\rangle + b|1\\rangle$,
stored as the vector `[a, b]`.

- Measuring gives 0 with probability $|a|^2$ and 1 with probability $|b|^2$.
- The probabilities must add to 1, so a valid state has length 1: $|a|^2 + |b|^2 = 1$.

$n$ qubits need $2^n$ amplitudes, one per bitstring. That doubling is the whole reason big circuits
are hard to simulate.
"""),
ex("probabilities from amplitudes",
   """
   Write `probabilities(psi)` that returns the measurement probabilities $|\\psi_x|^2$ for every entry.
   Then try it on the "plus" state $(|0\\rangle + |1\\rangle)/\\sqrt2$: you should get `[0.5, 0.5]`.
   """,
   """
   def probabilities(psi):
       # YOUR CODE: return an array of |amplitude|^2
       raise NotImplementedError
   """,
   """
   def probabilities(psi):
       return np.abs(np.asarray(psi)) ** 2
   """,
   """
   plus = (ket0 + ket1) / np.sqrt(2)
   checks.fn("probabilities", probabilities,
             [((plus,), [0.5, 0.5]), ((ket1,), [0, 1]), ((np.array([0.6, 0.8j]),), [0.36, 0.64])],
             hint="np.abs(z)**2 works for complex numbers")
   """,
   hint="`np.abs` of a complex number is its length. Square it."),
md("""
## 2. A gate is a matrix

Applying a gate = multiplying its matrix by the state vector: `new_state = G @ state`.

Gates in quantum computing are **unitary**: they rotate the vector without changing its length, so
probabilities still add to 1. The undo of a gate $U$ is $U^\\dagger$ (say "U dagger"): the
**conjugate transpose**, i.e. flip it across the diagonal and flip the sign of every imaginary part.
In numpy: `U.conj().T`. Unitary means $U^\\dagger U = I$.
"""),
code("""
print("X|0> =", X @ ket0, "  (bit flip: |0> becomes |1>)")
print("Z|1> =", Z @ ket1, "  (sign flip)")
print("H|0> =", H @ ket0, "  (equal superposition, the 'plus' state)")
print("H dagger =\\n", H.conj().T)
"""),
ex("is it unitary?",
   """
   Write `is_unitary(M)` returning `True` if $M^\\dagger M = I$ (up to rounding), else `False`.
   """,
   """
   def is_unitary(M):
       # YOUR CODE (np.allclose is handy)
       raise NotImplementedError
   """,
   """
   def is_unitary(M):
       M = np.asarray(M)
       return bool(np.allclose(M.conj().T @ M, np.eye(M.shape[0])))
   """,
   """
   checks.fn("is_unitary", is_unitary,
             [((X,), True), ((H,), True), ((np.array([[1, 1], [0, 1]]),), False), ((2 * Z,), False)])
   """),
ex("Pauli algebra (from BQ 101)",
   """
   Use numpy to confirm these facts. Each name below should hold a `True`/`False` you **computed**.

   1. `squares_are_identity`: $X^2 = Y^2 = Z^2 = H^2 = I$
   2. `xy_is_iz`: $XY = iZ$
   3. `x_z_anticommute`: $XZ = -ZX$
   4. `hxh_is_z`: $H X H = Z$ (H is its own dagger, so this is $H^\\dagger X H$)
   """,
   """
   squares_are_identity = None   # YOUR CODE
   xy_is_iz = None
   x_z_anticommute = None
   hxh_is_z = None
   """,
   """
   squares_are_identity = all(np.allclose(P @ P, I) for P in (X, Y, Z, H))
   xy_is_iz = np.allclose(X @ Y, 1j * Z)
   x_z_anticommute = np.allclose(X @ Z, -Z @ X)
   hxh_is_z = np.allclose(H @ X @ H, Z)
   """,
   """
   for nm in ["squares_are_identity", "xy_is_iz", "x_z_anticommute", "hxh_is_z"]:
       checks.equal(nm, globals()[nm], True, hint="all four facts are true; compute them with np.allclose")
   """),
md("""
## 3. Expectation values: one number per qubit

The challenge asks for **expectation values**. For a state $\\psi$ and an observable $M$ (a Hermitian
matrix, e.g. a Pauli), the expectation value is

$$\\langle M \\rangle = \\psi^\\dagger M \\psi .$$

**Intuition for $Z$:** measure, write +1 for a 0 and -1 for a 1, average over many shots. So
$\\langle Z\\rangle = P(0) - P(1)$: +1 means "certainly 0", -1 "certainly 1", 0 "fair coin".
"""),
ex("expectation value",
   """
   Write `expval(psi, M)` = $\\psi^\\dagger M \\psi$ as a real float. Check your intuition:
   $\\langle Z\\rangle$ on $|0\\rangle$ is +1, on the plus state it's 0, and $\\langle X\\rangle$ on the plus state is +1.
   """,
   """
   def expval(psi, M):
       # YOUR CODE: psi.conj() @ M @ psi, then take the real part
       raise NotImplementedError
   """,
   """
   def expval(psi, M):
       psi = np.asarray(psi)
       return float(np.real(psi.conj() @ M @ psi))
   """,
   """
   plus = (ket0 + ket1) / np.sqrt(2)
   checks.fn("expval", expval,
             [((ket0, Z), 1.0), ((ket1, Z), -1.0), ((plus, Z), 0.0), ((plus, X), 1.0),
              ((np.array([np.cos(0.3), np.sin(0.3)]), Z), np.cos(0.6))])
   """,
   hint="For psi = [cos t, sin t], <Z> = cos^2 t - sin^2 t = cos 2t."),
md("""
## 4. Several qubits: the tensor product, and qubit order

Two qubits live in a 4-dimensional space with basis $|00\\rangle, |01\\rangle, |10\\rangle, |11\\rangle$.
An operator acting on one qubit and doing nothing to the other is a **tensor (Kronecker) product**,
`np.kron(A, B)`.

**Qubit order (this bites everyone).** Qiskit and BlueQubit are *little-endian*: qubit 0 is the
**rightmost** symbol, both in bitstrings and in Pauli labels.

- bitstring `'01'` means qubit 1 = 0, qubit 0 = 1;
- label `"IZ"` means Z on qubit 0; `"ZI"` means Z on qubit 1;
- matrix: `np.kron(A_on_q1, B_on_q0)`, i.e. the highest qubit goes on the left.

The OTOC tutorial warns: get this backwards and you silently get the value for the wrong qubit.
"""),
code("""
from qiskit.quantum_info import Pauli
print('Pauli("IZ") is Z on qubit 0 ->', np.allclose(Pauli("IZ").to_matrix(), np.kron(I, Z)))
print('Pauli("ZI") is Z on qubit 1 ->', np.allclose(Pauli("ZI").to_matrix(), np.kron(Z, I)))
"""),
ex("Z on qubit q of n",
   """
   Write `z_on(q, n)`: the $2^n \\times 2^n$ matrix of $Z$ on qubit `q`, identity elsewhere, in Qiskit's
   order. Also write `z_label(q, n)`, the Pauli label string (e.g. `z_label(0, 3) == "IIZ"`).
   """,
   """
   def z_on(q, n):
       # YOUR CODE: kron together n 2x2 matrices, highest qubit first
       raise NotImplementedError

   def z_label(q, n):
       # YOUR CODE
       raise NotImplementedError
   """,
   """
   def z_on(q, n):
       M = np.array([[1.0 + 0j]])
       for k in reversed(range(n)):          # qubit n-1 first (leftmost), qubit 0 last
           M = np.kron(M, Z if k == q else I)
       return M

   def z_label(q, n):
       return "".join("Z" if k == q else "I" for k in reversed(range(n)))
   """,
   """
   checks.fn("z_on", z_on, [((q, n), Pauli("".join("Z" if k == q else "I" for k in reversed(range(n)))).to_matrix())
                            for (q, n) in [(0, 1), (0, 3), (2, 3), (1, 4)]],
             hint="loop k from n-1 down to 0 and kron Z when k == q")
   checks.fn("z_label", z_label, [((0, 3), "IIZ"), ((2, 3), "ZII"), ((1, 4), "IIZI")])
   """),
ex("<Z_q> from a statevector",
   """
   For two qubits write the state as $a|00\\rangle + b|01\\rangle + c|10\\rangle + d|11\\rangle$ (vector `[a, b, c, d]`).
   Predict, then compute: $\\langle Z_0\\rangle = |a|^2 - |b|^2 + |c|^2 - |d|^2$ and
   $\\langle Z_1\\rangle = |a|^2 + |b|^2 - |c|^2 - |d|^2$.

   Set `zq` to the list `[<Z_0>, <Z_1>]` for the state below, computed with your `expval` and `z_on`.
   """,
   """
   psi = np.array([0.5, 0.5j, -0.5, 0.5], dtype=complex)   # a, b, c, d
   zq = None   # YOUR CODE: [<Z_0>, <Z_1>]
   """,
   """
   psi = np.array([0.5, 0.5j, -0.5, 0.5], dtype=complex)
   zq = [expval(psi, z_on(0, 2)), expval(psi, z_on(1, 2))]
   """,
   """
   checks.close("zq", zq, [0.0, 0.0], hint="all |amplitudes|^2 are 0.25 here, so both should be 0")
   psi2 = np.array([0.8, 0, 0, 0.6])
   checks.close("Z0 on [0.8,0,0,0.6]", None if zq is None else expval(psi2, z_on(0, 2)), 0.64 - 0.36)
   """),
md("""
## 5. Commutators and moving an operator through a gate

The **commutator** $[A, B] = AB - BA$ asks: does the order matter? If it's the zero matrix, $A$ and
$B$ **commute**.

- Operators on **different** qubits always commute.
- Different Paulis on the **same** qubit don't (they *anticommute*: $XZ = -ZX$).

**Conjugation** $U^\\dagger P U$ is how an operator looks after the circuit $U$ (the *Heisenberg
picture*). The OTOC's "butterfly" is exactly this: $B(t) = U^\\dagger B U$. For Clifford gates
(H, S, CNOT, CZ) a Pauli goes in and a single Pauli comes out; for other gates it spreads into a sum.
"""),
ex("commutators",
   """
   Write `commutator(A, B)`. Then set `pairs_that_commute` to a set containing the names (from
   `"XZ_same_qubit"`, `"X0_Z1"`, `"ZZ_same_qubit"`) of the pairs that commute.
   Use 2-qubit matrices: `X0 = np.kron(I, X)`, `Z1 = np.kron(Z, I)` etc.
   """,
   """
   def commutator(A, B):
       raise NotImplementedError   # YOUR CODE

   pairs_that_commute = None      # YOUR CODE, e.g. {"X0_Z1"}
   """,
   """
   def commutator(A, B):
       return A @ B - B @ A

   X0, Z0, Z1 = np.kron(I, X), np.kron(I, Z), np.kron(Z, I)
   tests = {"XZ_same_qubit": (X0, Z0), "X0_Z1": (X0, Z1), "ZZ_same_qubit": (Z0, Z0)}
   pairs_that_commute = {k for k, (A, B) in tests.items() if np.allclose(commutator(A, B), 0)}
   """,
   """
   checks.fn("commutator", commutator, [((X, Z), X @ Z - Z @ X), ((Z, Z), np.zeros((2, 2)))])
   checks.equal("pairs_that_commute", pairs_that_commute, {"X0_Z1", "ZZ_same_qubit"},
                hint="different qubits always commute; a Pauli commutes with itself")
   """),
ex("conjugation through gates",
   """
   Compute these and set each variable to the matching matrix (use `.conj().T` for dagger):

   - `hzh` = $H^\\dagger Z H$ (expect $X$)
   - `sxs` = $S^\\dagger X S$ with $S = \\mathrm{diag}(1, i)$ (expect $-Y$; a Clifford maps a Pauli to ± a Pauli)
   - `cx_x0` = $CX^\\dagger (X \\text{ on qubit } 0) CX$ for a CNOT with control 0, target 1 (expect $X_0X_1$:
     an X on the control **spreads** to the target. This is how the butterfly grows.)
   """,
   """
   S = np.diag([1, 1j])
   # CNOT, control qubit 0, target qubit 1, in Qiskit order (basis |q1 q0>)
   CX = np.array([[1,0,0,0],[0,0,0,1],[0,0,1,0],[0,1,0,0]], dtype=complex)
   hzh = None   # YOUR CODE
   sxs = None
   cx_x0 = None
   """,
   """
   S = np.diag([1, 1j])
   CX = np.array([[1,0,0,0],[0,0,0,1],[0,0,1,0],[0,1,0,0]], dtype=complex)
   hzh = H.conj().T @ Z @ H
   sxs = S.conj().T @ X @ S
   cx_x0 = CX.conj().T @ np.kron(I, X) @ CX
   """,
   """
   checks.close("hzh", hzh, X)
   checks.close("sxs", sxs, -Y, hint="S^dag X S: S^dag = diag(1, -i)")
   checks.close("cx_x0", cx_x0, np.kron(X, X), hint="X on qubit 0 is np.kron(I, X) in Qiskit order")
   """),
md("""
## 6. Every matrix is a sum of Paulis

The 4 Paulis $\\{I, X, Y, Z\\}$ are a basis for 2×2 matrices (and their tensor products for bigger
ones). The coefficient of Pauli $P$ in a $2^n\\times 2^n$ matrix $M$ is

$$c_P = \\frac{\\mathrm{Tr}(P M)}{2^n}.$$

This is what Pauli-path simulators track: an operator as a list of (Pauli string, coefficient).
"""),
ex("Pauli decomposition",
   """
   Write `pauli_coeffs(M)` for a 2×2 matrix returning the dict `{"I": cI, "X": cX, "Y": cY, "Z": cZ}`
   (real numbers for Hermitian M). The IBM cost-function example: $\\begin{pmatrix}-1&2\\\\2&1\\end{pmatrix} = 2X - Z$.
   """,
   """
   def pauli_coeffs(M):
       raise NotImplementedError   # YOUR CODE
   """,
   """
   def pauli_coeffs(M):
       return {name: float(np.real(np.trace(P @ M) / 2)) for name, P in zip("IXYZ", (I, X, Y, Z))}
   """,
   """
   Hm = np.array([[-1, 2], [2, 1]], dtype=complex)
   checks.fn("pauli_coeffs", lambda M: list(pauli_coeffs(M).values()),
             [((Hm,), [0, 2, 0, -1]), ((H,), [0, 1/np.sqrt(2), 0, 1/np.sqrt(2)])])
   """),
ex("an expectation value two ways",
   """
   With $H_m = 2X - Z$ and the plus state, compute `direct` $=\\psi^\\dagger H_m\\psi$ and
   `from_terms` $= 2\\langle X\\rangle - \\langle Z\\rangle$. They must agree (expect 2). This
   "sum of Pauli terms" trick is exactly how `pauli_sum=[("X", 2.0), ("Z", -1.0)]` works on BlueQubit.
   """,
   """
   plus = (ket0 + ket1) / np.sqrt(2)
   Hm = np.array([[-1, 2], [2, 1]], dtype=complex)
   direct = None       # YOUR CODE
   from_terms = None
   """,
   """
   plus = (ket0 + ket1) / np.sqrt(2)
   Hm = np.array([[-1, 2], [2, 1]], dtype=complex)
   direct = expval(plus, Hm)
   from_terms = 2 * expval(plus, X) - expval(plus, Z)
   """,
   """
   checks.close("direct", direct, 2.0)
   checks.close("from_terms", from_terms, 2.0)
   """),
md("""
## Recap

| Idea | numpy | Where it shows up |
|---|---|---|
| state = vector, $2^n$ amplitudes | `psi` | statevector simulator, memory wall |
| gate = unitary matrix | `G @ psi`, `G.conj().T` | every circuit; $U^\\dagger$ = run backward |
| expectation $\\psi^\\dagger M\\psi$ | `psi.conj() @ M @ psi` | **the numbers you submit** |
| tensor product, little-endian | `np.kron(on_q1, on_q0)` | Pauli labels like `"IIZ"` |
| commutator | `A@B - B@A` | OTOC = "does the butterfly still commute with the check?" |
| conjugation $U^\\dagger P U$ | | Heisenberg picture, butterfly $B(t)$, Pauli paths |
| Pauli coefficients $\\mathrm{Tr}(PM)/2^n$ | | Pauli-path simulation |

**Next:** `01_bq101_offline.ipynb`, circuits and simulators.
"""),
]
