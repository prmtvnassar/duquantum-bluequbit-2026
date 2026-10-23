"""otoc_tools.py: small helpers for the OTOC tutorial (otoc_intro.ipynb).

Everything here works on a laptop: a pure-numpy statevector simulator for small
echo circuits, Qiskit builders and pictures of the same circuits, CSV files of
estimates, and the correlation / SNR used to judge them.

Conventions
-----------
* Circuits are 1D "brickwork": layer t applies random two-qubit gates on pairs
  (i, i+1) with i = t % 2, t % 2 + 2, ...  Layer 0 is applied first.
* B ("butterfly") = X on qubit b.  M ("measurement") = Z on qubit q.
* OTOC(1) at q = <Z_q> after   U, B, U^dag
  OTOC(2) at q = <Z_q> after   U, B, U^dag, M, U, B, U^dag      (M = Z_q)
  both starting from |0...0>.
* BlueQubit / Qiskit Pauli labels are big-endian: qubit 0 is the RIGHTMOST
  character.  Use z_label(q, n) and you never have to think about it.
"""
from __future__ import annotations

import csv
import math

import numpy as np

X = np.array([[0, 1], [1, 0]], dtype=complex)
Z = np.array([[1, 0], [0, -1]], dtype=complex)


# ---------- random circuits ---------------------------------------------------
def haar4(rng: np.random.Generator) -> np.ndarray:
    """A Haar-random 4x4 unitary (a random two-qubit gate)."""
    z = (rng.normal(size=(4, 4)) + 1j * rng.normal(size=(4, 4))) / np.sqrt(2)
    q, r = np.linalg.qr(z)
    return q * (np.diag(r) / abs(np.diag(r)))


def brickwork(n: int, depth: int, rng: np.random.Generator) -> list:
    """List of (layer, i, G): G acts on qubits (i, i+1); layer 0 is applied first."""
    return [(t, i, haar4(rng)) for t in range(depth) for i in range(t % 2, n - 1, 2)]


# ---------- numpy statevector (fine up to ~22 qubits) -------------------------
def zero(n: int) -> np.ndarray:
    psi = np.zeros((2,) * n, complex)
    psi[(0,) * n] = 1
    return psi


def apply1(psi: np.ndarray, P: np.ndarray, q: int) -> np.ndarray:
    return np.moveaxis(np.tensordot(P, psi, axes=([1], [q])), 0, q)


def apply2(psi: np.ndarray, G: np.ndarray, i: int) -> np.ndarray:
    """Apply 4x4 gate G to qubits (i, i+1); G's first tensor factor is qubit i."""
    psi = np.tensordot(G.reshape(2, 2, 2, 2), psi, axes=([2, 3], [i, i + 1]))
    return np.moveaxis(psi, [0, 1], [i, i + 1])


def run_U(psi: np.ndarray, gates: list) -> np.ndarray:
    for _, i, G in gates:
        psi = apply2(psi, G, i)
    return psi


def run_Udag(psi: np.ndarray, gates: list) -> np.ndarray:
    for _, i, G in reversed(gates):
        psi = apply2(psi, G.conj().T, i)
    return psi


def expZ(psi: np.ndarray, q: int) -> float:
    p = np.moveaxis(abs(psi) ** 2, q, 0)
    return float(p[0].sum() - p[1].sum())


def exact_otoc1(n: int, gates: list, b: int) -> np.ndarray:
    """OTOC(1) at every qubit q (one echo gives them all)."""
    psi = run_Udag(apply1(run_U(zero(n), gates), X, b), gates)
    return np.array([expZ(psi, q) for q in range(n)])


def exact_otoc2(n: int, gates: list, b: int, q: int) -> float:
    """OTOC(2) at qubit q (M = Z_q sits in the middle, so one echo per q)."""
    psi = run_Udag(apply1(run_U(zero(n), gates), X, b), gates)
    psi = apply1(psi, Z, q)
    psi = run_Udag(apply1(run_U(psi, gates), X, b), gates)
    return expZ(psi, q)


# ---------- Qiskit circuits ---------------------------------------------------
def to_qiskit(n: int, gates: list):
    """U as a Qiskit circuit in the u3 + cz gate set (what BlueQubit runs)."""
    from qiskit import QuantumCircuit, transpile

    qc = QuantumCircuit(n, name="U")
    for _, i, G in gates:
        # Qiskit is little-endian: the FIRST listed qubit is the matrix's last
        # tensor factor, so list (i+1, i) to make qubit i the first factor.
        qc.unitary(G, [i + 1, i])
    return transpile(qc, basis_gates=["u3", "cz"], optimization_level=1, seed_transpiler=0)


def echo_circuit(U, b: int, q: int | None = None, order: int = 1):
    """The OTOC echo built from U (a Qiskit circuit).

    order=1:  U, X_b, U^dag                       -> measure <Z_q> for any q
    order=2:  U, X_b, U^dag, Z_q, U, X_b, U^dag   -> measure <Z_q>
    """
    from qiskit import QuantumCircuit

    n = U.num_qubits
    qc = QuantumCircuit(n, name=f"OTOC{order}")
    Ud = U.inverse()
    qc.compose(U, inplace=True); qc.x(b); qc.compose(Ud, inplace=True)
    if order == 2:
        if q is None:
            raise ValueError("OTOC(2) needs the measurement qubit q")
        qc.z(q)
        qc.compose(U, inplace=True); qc.x(b); qc.compose(Ud, inplace=True)
    return qc


def near_clifford_circuit(n: int, depth: int, rng: np.random.Generator, p: float = 0.15):
    """U as a Qiskit circuit of h, s, cz and rz only: a brickwork of random two-qubit Clifford
    gates (random H/S words on both qubits, then CZ, then random H/S words again), each followed
    with probability p by Rz(theta), theta uniform in [0, 2 pi), on one of its two qubits.
    Clifford gates map one Pauli string to one Pauli string, so Pauli paths only branch at the
    rz gates.  p = 0 gives a pure Clifford circuit."""
    from qiskit import QuantumCircuit

    qc = QuantumCircuit(n, name="U")

    def local(k):
        for _ in range(3):
            (qc.h if rng.random() < 0.5 else qc.s)(k)

    for t in range(depth):
        for i in range(t % 2, n - 1, 2):
            local(i); local(i + 1)
            qc.cz(i, i + 1)
            local(i); local(i + 1)
            if rng.random() < p:
                qc.rz(float(rng.uniform(0, 2 * np.pi)), i if rng.random() < 0.5 else i + 1)
    return qc


# ---------- Circuit pictures ---------------------------------------------------
# One colour per role, so every diagram in the notebook reads the same way.
CIRCUIT_STYLE = {
    "name": "clifford",
    "fontsize": 13,
    "displaycolor": {
        "U": ["#2F6BF0", "#FFFFFF"],      # the scrambling circuit U (and its gates)
        "G": ["#2F6BF0", "#FFFFFF"],
        "Udg": ["#8A5CF5", "#FFFFFF"],    # U dagger (and its gates)
        "Gdg": ["#8A5CF5", "#FFFFFF"],
        "x": ["#E5484D", "#FFFFFF"],      # the butterfly
        "z": ["#F59E0B", "#000000"],      # the probe
    },
}


def draw(qc, scale: float = 0.8, **kwargs):
    """Draw a Qiskit circuit with matplotlib in the notebook's style. Returns the figure."""
    fig = qc.draw("mpl", style=CIRCUIT_STYLE, fold=-1, scale=scale, initial_state=True, **kwargs)
    # Qiskit numbers the wires inside every multi-qubit box (0, 1, ...). Here that is clutter.
    for text in list(fig.axes[0].texts):
        if text.get_text().isdigit():
            text.remove()
    return fig


def echo_schematic(n: int, b: int, q: int, order: int = 1):
    """Block picture of the OTOC echo: U and U^dag as single boxes across all qubits."""
    from qiskit import QuantumCircuit
    from qiskit.circuit import Gate

    U = Gate("U", n, [], label="$U$")
    Ud = Gate("Udg", n, [], label="$U^\\dagger$")
    qc = QuantumCircuit(n, 1)
    qc.append(U, range(n)); qc.x(b); qc.append(Ud, range(n))
    if order == 2:
        qc.z(q); qc.append(U, range(n)); qc.x(b); qc.append(Ud, range(n))
    qc.measure(q, 0)                                  # <Z_q> is read off this qubit
    return qc


def z_label(q: int, n: int) -> str:
    """Pauli label for Z on qubit q. Big-endian: qubit 0 is the rightmost character."""
    return "".join("Z" if k == n - 1 - q else "I" for k in range(n))


def load_qasm(path):
    from qiskit import qasm2

    return qasm2.load(str(path), custom_instructions=qasm2.LEGACY_CUSTOM_INSTRUCTIONS)


def simulate_expz(qc, q: int) -> float:
    """Exact <Z_q> of a Qiskit circuit (or QASM path) from |0...0>, gate by gate with numpy.

    Memory is 2^n complex numbers: fine to ~25 qubits, impossible at ~50.
    """
    from qiskit.quantum_info import Operator

    if not hasattr(qc, "data"):
        qc = load_qasm(qc)
    psi = zero(qc.num_qubits)
    for ins in qc.data:
        idx = [qc.find_bit(b).index for b in ins.qubits]
        M = Operator(ins.operation).data
        if len(idx) == 1:
            psi = apply1(psi, M, idx[0])
        else:  # Qiskit matrices are little-endian: the first listed qubit is the last factor
            psi = np.moveaxis(apply2(np.moveaxis(psi, idx[::-1], [0, 1]), M, 0), [0, 1], idx[::-1])
    return expZ(psi, q)


# ---------- CSV files of estimates, and scoring ---------------------------------
def write_csv(path, values: dict, column: str = "estimate") -> None:
    """values: {(circuit, qubit): number}.  Writes circuit,qubit,<column> rows, sorted."""
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(("circuit", "qubit", column))
        for (c, q), v in sorted(values.items()):
            w.writerow((c, int(q), repr(float(v))))


def read_csv(path, column: str | None = None) -> dict:
    """Read a circuit,qubit,<value> CSV into {(circuit, qubit): float}.  Raises ValueError on a bad file."""
    with open(path, newline="") as f:
        rows = list(csv.reader(f))
    if not rows or len(rows[0]) != 3 or [h.strip() for h in rows[0][:2]] != ["circuit", "qubit"]:
        raise ValueError(f"{path}: the header must be circuit,qubit,{column or '<value>'}")
    if column and rows[0][2].strip() != column:
        raise ValueError(f"{path}: the third column must be called {column!r}, not {rows[0][2]!r}")
    out = {}
    for k, row in enumerate(rows[1:], start=2):
        if not row:
            continue
        try:
            c, q, v = row[0].strip(), int(row[1]), float(row[2])
        except (ValueError, IndexError):
            raise ValueError(f"{path}, line {k}: expected circuit,qubit,number, got {row}") from None
        if not math.isfinite(v):
            raise ValueError(f"{path}, line {k}: the value must be a finite number, got {row[2]!r}")
        if (c, q) in out:
            raise ValueError(f"{path}, line {k}: {c} qubit {q} appears twice")
        out[c, q] = v
    return out


def score_csv(estimates, exact) -> dict:
    """Compare a CSV of estimates (circuit,qubit,estimate) with a CSV of exact values
    (circuit,qubit,exact); returns score() of the two, plus n.  Both must list the same rows."""
    sub, tru = read_csv(estimates, "estimate"), read_csv(exact, "exact")
    if sub.keys() != tru.keys():
        missing, extra = sorted(tru.keys() - sub.keys()), sorted(sub.keys() - tru.keys())
        raise ValueError(f"{estimates}: {len(missing)} rows missing (e.g. {missing[:3]}), "
                         f"{len(extra)} not in the exact file (e.g. {extra[:3]})")
    keys = sorted(tru)
    return {**score([sub[k] for k in keys], [tru[k] for k in keys]), "n": len(keys)}


def score(pred, truth, families=None) -> dict:
    """Correlation between your estimates and the exact values, plus the matching SNR.

    r = Pearson correlation over all observables;  SNR = r / sqrt(1 - r^2)
    (the signal-to-noise ratio of a linear fit of truth to your estimates);
    bits = 1/2 log2(1 + SNR^2), the same SNR on a log scale.  Negative r counts as 0.

    families: optional list giving each observable's circuit family (observables that
    share one circuit U).  Then both truth and estimates are first centred within each
    family and divided by that family's spread of exact values, so only the differences
    BETWEEN probes of the same circuit count, and every family weighs the same.
    """
    p, t = np.asarray(pred, float), np.asarray(truth, float)
    if families is not None:
        f = np.asarray(families)
        p, t = p.copy(), t.copy()
        for fam in np.unique(f):
            m = f == fam
            sd = t[m].std() or 1.0
            p[m] = (p[m] - p[m].mean()) / sd
            t[m] = (t[m] - t[m].mean()) / sd
    if p.std() == 0 or t.std() == 0:
        return {"r": 0.0, "snr": 0.0, "bits": 0.0}
    r = float(np.corrcoef(p, t)[0, 1])
    rc = max(r, 0.0)
    snr = float(rc / np.sqrt(max(1 - rc ** 2, 1e-12)))
    # The same SNR on a log scale: 1/2 log2(1 + SNR^2) = -1/2 log2(1 - r^2), the information (in bits)
    # the estimates carry about the exact values.  About 0 for guessing, +1.7 bits per 10x smaller error.
    return {"r": r, "snr": snr, "bits": float(0.5 * np.log2(1 + snr ** 2))}
