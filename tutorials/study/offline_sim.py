"""offline_sim.py: an offline stand-in for the three BlueQubit simulators.

    bq = LocalBQ()
    r = bq.run(qc, device="cpu")                                    # exact statevector
    r = bq.run(qc, device="mps.cpu", pauli_sum=[("IIZ", 1.0)],
               options={"mps_bond_dimension": 16})                  # approximate MPS (qiskit-aer)
    r = bq.run(qc, device="pauli-path", pauli_sum=[("IIZ", 1.0)],
               options={"pauli_path_truncation_threshold": 1e-3})   # approximate Pauli paths (ours)
    r.expectation_value, r.get_counts(), r.get_statevector(), r.run_time_ms

The call signature mirrors `bluequbit.init(...).run(...)`, so code you write here ports to the
real platform by swapping `LocalBQ()` for `bluequbit.init(token)`.

Pauli labels follow Qiskit / BlueQubit: qubit 0 is the RIGHTMOST character ("IIZ" = Z on qubit 0).

The Pauli-path simulator here is our own implementation of the method described in the BlueQubit
Pauli-path tutorial (Heisenberg picture, drop terms with |coeff| < threshold after every gate).
It is exact when the threshold is 0. It will not match BlueQubit's numbers digit for digit at a
finite threshold (they transpile to a different gate set first), but it behaves the same way.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field

import numpy as np

# ---------------------------------------------------------------------------------------------
# Result object
# ---------------------------------------------------------------------------------------------


@dataclass
class LocalResult:
    device: str
    expectation_value: float | None = None
    run_time_ms: float = 0.0
    _counts: dict | None = None
    _statevector: np.ndarray | None = None
    stats: dict = field(default_factory=dict)

    def get_counts(self):
        if self._counts is None:
            raise ValueError("No counts: pass shots=... and leave out pauli_sum.")
        return self._counts

    def get_statevector(self):
        if self._statevector is None:
            raise ValueError("No statevector: only device='cpu' without shots returns one.")
        return self._statevector


# ---------------------------------------------------------------------------------------------
# Pauli-path propagation (Heisenberg picture), vectorised with numpy
# ---------------------------------------------------------------------------------------------
# A Pauli string on n qubits is two bitmasks (x, z): bit q of x / z says whether qubit q carries
# an X / Z part.  I=(0,0)  X=(1,0)  Z=(0,1)  Y=(1,1).  Every term has a REAL coefficient, because
# U^dag O U stays Hermitian and the Hermitian Paulis are a real basis for Hermitian matrices.

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


# ---------------------------------------------------------------------------------------------
# The BlueQubit-shaped front end
# ---------------------------------------------------------------------------------------------


def _sparse_op(pauli_sum):
    from qiskit.quantum_info import SparsePauliOp

    return SparsePauliOp.from_list([(lab, c) for lab, c in pauli_sum])


class LocalBQ:
    """Offline look-alike of `bluequbit.init(...)`.  Devices: cpu, mps.cpu, pauli-path.

    sv_qubit_limit mimics the statevector memory wall so you can practise the real decision.
    """

    def __init__(self, sv_qubit_limit: int = 26, seed: int = 1234):
        self.sv_qubit_limit = sv_qubit_limit
        self.seed = seed
        self.log = []                            # one dict per run, like a job history

    def run(self, circuit, device: str = "cpu", pauli_sum=None, shots=None, options=None, job_name=None):
        options = dict(options or {})
        device = device.replace(".gpu", ".cpu") if device.startswith("mps") else device
        t0 = time.perf_counter()
        if device == "cpu":
            res = self._run_sv(circuit, pauli_sum, shots)
        elif device == "mps.cpu":
            res = self._run_mps(circuit, pauli_sum, shots, options.get("mps_bond_dimension", 64))
        elif device in ("pauli-path", "pauli-path.gpu"):
            if not pauli_sum:
                raise ValueError("pauli-path only returns expectation values: pass pauli_sum")
            thr = options.get("pauli_path_truncation_threshold", 0.0)
            val, stats = pauli_path_expectation(circuit, pauli_sum, thr)
            res = LocalResult("pauli-path", expectation_value=val, stats=stats)
        else:
            raise ValueError(f"unknown device {device!r}: use 'cpu', 'mps.cpu' or 'pauli-path'")
        res.run_time_ms = 1000 * (time.perf_counter() - t0)
        self.log.append({"job_name": job_name, "device": device, "options": options, "qubits": circuit.num_qubits,
                         "expectation_value": res.expectation_value, "run_time_ms": round(res.run_time_ms, 1),
                         **res.stats})
        return res

    # -- exact statevector ------------------------------------------------------------------
    def _run_sv(self, qc, pauli_sum, shots):
        from qiskit.quantum_info import Statevector

        if qc.num_qubits > self.sv_qubit_limit:
            raise MemoryError(f"{qc.num_qubits} qubits is past the statevector limit "
                              f"({self.sv_qubit_limit}) of this machine: use mps.cpu or pauli-path")
        qc2 = qc.remove_final_measurements(inplace=False)
        sv = Statevector.from_instruction(qc2)
        res = LocalResult("cpu")
        if pauli_sum:
            res.expectation_value = float(np.real(sv.expectation_value(_sparse_op(pauli_sum))))
        elif shots:
            sv.seed(self.seed)
            res._counts = dict(sv.sample_counts(shots))
        else:
            res._statevector = np.asarray(sv.data)
        return res

    # -- MPS via qiskit-aer ----------------------------------------------------------------
    def _run_mps(self, qc, pauli_sum, shots, chi):
        from qiskit import transpile
        from qiskit_aer import AerSimulator

        sim = AerSimulator(method="matrix_product_state", matrix_product_state_max_bond_dimension=int(chi),
                           seed_simulator=self.seed)
        res = LocalResult("mps.cpu", stats={"bond_dimension": int(chi)})
        if pauli_sum:
            qc2 = qc.remove_final_measurements(inplace=False)
            qc2.save_expectation_value(_sparse_op(pauli_sum), list(range(qc2.num_qubits)), label="ev")
            out = sim.run(transpile(qc2, sim, optimization_level=0)).result()
            res.expectation_value = float(np.real(out.data(0)["ev"]))
        else:
            qc2 = qc.copy()
            if qc2.num_clbits == 0:
                qc2.measure_all()
            out = sim.run(transpile(qc2, sim, optimization_level=0), shots=shots or 1024).result()
            res._counts = dict(out.get_counts())
        return res


def z_sum(q: int, n: int):
    """pauli_sum for Z on qubit q (qubit 0 = rightmost character)."""
    return [("".join("Z" if k == n - 1 - q else "I" for k in range(n)), 1.0)]
