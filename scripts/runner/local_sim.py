"""Local (free) simulators for tuning: exact statevector, MPS, and Pauli-path.

The Pauli-path propagator below comes from the team's earlier tutorial helper
(tutorials/study/offline_sim.py, removed from main in f6e8c33): Heisenberg picture,
dropping terms with |coefficient| < threshold after every gate, like BlueQubit's
pauli_path_truncation_threshold. Supports up to 31 qubits.
"""

from __future__ import annotations

import numpy as np

_P1 = {
    (0, 0): np.eye(2, dtype=complex),
    (1, 0): np.array([[0, 1], [1, 0]], dtype=complex),
    (0, 1): np.array([[1, 0], [0, -1]], dtype=complex),
    (1, 1): np.array([[0, -1j], [1j, 0]], dtype=complex),
}


def _local_paulis(k: int):
    """All 4^k local Paulis as (index, x_bits, z_bits, matrix) in Qiskit order (local qubit 0 = rightmost factor)."""
    out = []
    for idx in range(4 ** k):
        xs, zs, mat = [], [], np.array([[1.0 + 0j]])
        for j in range(k):                       # local qubit j uses 2 bits of idx
            x, z = (idx >> (2 * j)) & 1, (idx >> (2 * j + 1)) & 1
            xs.append(x); zs.append(z)
            mat = np.kron(_P1[(x, z)], mat)      # qubit j becomes the more significant factor
        out.append((idx, xs, zs, mat))
    return out


_LOCAL = {1: _local_paulis(1), 2: _local_paulis(2)}


def conjugation_table(G: np.ndarray) -> np.ndarray:
    """M[out, in] = Tr(P_out  G^dag P_in G) / 2^k : how a gate maps each local Pauli (Heisenberg picture)."""
    k = int(round(np.log2(G.shape[0])))
    basis = _LOCAL[k]
    M = np.zeros((4 ** k, 4 ** k))
    Gd = G.conj().T
    for i, _, _, Pin in basis:
        evolved = Gd @ Pin @ G
        for o, _, _, Pout in basis:
            c = np.trace(Pout @ evolved) / 2 ** k
            if abs(c.imag) > 1e-9:
                raise ValueError("non-real Pauli coefficient: gate is not unitary?")
            M[o, i] = c.real
    M[np.abs(M) < 1e-13] = 0.0
    return M


def _gate_list(qc):
    """(matrix, [qubit indices]) for every gate of a Qiskit circuit, transpiling if needed."""
    from qiskit import transpile
    from qiskit.quantum_info import Operator

    gates = []
    for ins in qc.data:
        name = ins.operation.name
        if name in ("barrier", "measure", "save_expectation_value"):
            continue
        idx = [qc.find_bit(b).index for b in ins.qubits]
        if len(idx) > 2:
            sub = transpile(qc.__class__(len(idx)).compose(ins.operation, range(len(idx))),
                            basis_gates=["u3", "cx"], optimization_level=0)
            for m, sidx in _gate_list(sub):
                gates.append((m, [idx[s] for s in sidx]))
            continue
        gates.append((Operator(ins.operation).data, idx))
    return gates


def pauli_path_expectation(qc, pauli_sum, threshold: float = 0.0, max_terms: int = 5_000_000):
    """<0|U^dag O U|0> by pushing O = sum c_P P backwards through the circuit.

    After each gate, terms with |c| < threshold are dropped.  Returns (value, stats).
    """
    n = qc.num_qubits
    if n > 31:
        raise ValueError("this offline Pauli-path supports up to 31 qubits")
    # terms as parallel arrays
    xs, zs, cs = [], [], []
    for label, coeff in pauli_sum:
        label = label.upper()
        if len(label) != n:
            raise ValueError(f"label {label!r} has length {len(label)}, circuit has {n} qubits")
        x = z = 0
        for q in range(n):
            ch = label[n - 1 - q]                # qubit 0 is the rightmost character
            if ch in "XY": x |= 1 << q
            if ch in "ZY": z |= 1 << q
        xs.append(x); zs.append(z); cs.append(float(np.real(coeff)))
    X = np.array(xs, dtype=np.int64); Z = np.array(zs, dtype=np.int64); C = np.array(cs)
    X, Z, C = _merge(X, Z, C, n)

    tables = {}
    max_seen, n_gates = len(C), 0
    for G, idx in reversed(_gate_list(qc)):     # Heisenberg: last gate first
        if len(C) == 0:                          # truncation threw everything away: the estimate is 0
            break
        key = (G.tobytes(), len(idx))
        M = tables.get(key)
        if M is None:
            M = tables[key] = conjugation_table(G)
        X, Z, C = _apply_table(X, Z, C, M, idx)
        X, Z, C = _merge(X, Z, C, n)
        if threshold > 0:
            keep = np.abs(C) >= threshold
            X, Z, C = X[keep], Z[keep], C[keep]
        max_seen = max(max_seen, len(C)); n_gates += 1
        if len(C) > max_terms:
            raise MemoryError(f"more than {max_terms:,} Pauli terms: raise the threshold")
    value = float(C[X == 0].sum())              # only I/Z strings survive <0...0|.|0...0>, each worth +1
    return value, {"max_terms": int(max_seen), "final_terms": int(len(C)), "gates": n_gates}


def _apply_table(X, Z, C, M, idx):
    k = len(idx)
    loc = np.zeros(len(C), dtype=np.int64)
    for j, q in enumerate(idx):
        loc |= ((X >> q) & 1) << (2 * j)
        loc |= ((Z >> q) & 1) << (2 * j + 1)
    clear = 0
    for q in idx:
        clear |= 1 << q
    Xb, Zb = X & ~clear, Z & ~clear
    outX, outZ, outC = [], [], []
    for i in range(4 ** k):
        sel = loc == i
        if not sel.any():
            continue
        col = M[:, i]
        for o in np.nonzero(col)[0]:
            xo = zo = 0
            for j, q in enumerate(idx):
                xo |= ((o >> (2 * j)) & 1) << q
                zo |= ((o >> (2 * j + 1)) & 1) << q
            outX.append(Xb[sel] | xo); outZ.append(Zb[sel] | zo); outC.append(C[sel] * col[o])
    return np.concatenate(outX), np.concatenate(outZ), np.concatenate(outC)


def _merge(X, Z, C, n):
    keys = (X << n) | Z
    uniq, inv = np.unique(keys, return_inverse=True)
    Cm = np.bincount(inv, weights=C, minlength=len(uniq))
    nz = np.abs(Cm) > 1e-15
    uniq, Cm = uniq[nz], Cm[nz]
    return uniq >> n, uniq & ((1 << n) - 1), Cm




# ---------------------------------------------------------------- front end used by the sweep tools

def z_label(q: int, n: int) -> str:
    return "I" * (n - 1 - q) + "Z" + "I" * q


def reduce(qc):
    """Cancel the echo's forward/backward gate pairs (same result, far fewer gates)."""
    from qiskit import transpile

    return transpile(qc, basis_gates=["u3", "cz"], optimization_level=3, seed_transpiler=0)


def exact_z(qc, q: int, precision: str = "single", threads: int = 0) -> float:
    from qiskit.quantum_info import SparsePauliOp
    from qiskit_aer import AerSimulator

    c = reduce(qc)
    c.save_expectation_value(SparsePauliOp(z_label(q, c.num_qubits)), list(range(c.num_qubits)), label="z")
    sim = AerSimulator(method="statevector", precision=precision, max_parallel_threads=threads)
    return float(sim.run(c, shots=1).result().data()["z"])


def mps_z(qc, q: int, chi: int, threads: int = 1) -> float:
    from qiskit.quantum_info import SparsePauliOp
    from qiskit_aer import AerSimulator

    c = reduce(qc)
    c.save_expectation_value(SparsePauliOp(z_label(q, c.num_qubits)), list(range(c.num_qubits)), label="z")
    sim = AerSimulator(method="matrix_product_state", matrix_product_state_max_bond_dimension=int(chi),
                       max_parallel_threads=threads)
    return float(sim.run(c, shots=1).result().data()["z"])


def pps_z(qc, q: int, eps: float) -> float:
    c = reduce(qc)
    value, _ = pauli_path_expectation(c, [(z_label(q, c.num_qubits), 1.0)], threshold=float(eps))
    return value
