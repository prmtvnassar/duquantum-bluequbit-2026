"""Shared helpers for the G4 proxy lab: grid layering rule, seeded Haar echo circuits,
exact OTOC(2) vectors, and scoring utilities.  $0: nothing here touches BlueQubit.

Geometry (verified against problems/03_sample_S3/circuits/Duke_S3_0.qasm, 5x6 grid):
  one period = [H0, V0, H1, V1] where
    H0 = (r,c)-(r,c+1) for even c,   V0 = (r,c)-(r+1,c) for even r,
    H1 = (r,c)-(r,c+1) for odd c,    V1 = (r,c)-(r+1,c) for odd r,
  qubit = row*C + col.  16 layers = 4 periods (196 gates on 5x6, 1 Haar gate = 3 CZ).
Echo (verified: block2 == block0 and block3 == block1 textually, block1 = reverse of block0):
  circuit(q) = U, X_b, U^dag, Z_q, U, X_b, U^dag, then measure Z_q.
"""
import json
import os
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
os.makedirs(DATA, exist_ok=True)


def grid_layers(R, C):
    idx = lambda r, c: r * C + c
    H0 = [(idx(r, c), idx(r, c + 1)) for r in range(R) for c in range(0, C - 1, 2)]
    V0 = [(idx(r, c), idx(r + 1, c)) for r in range(0, R - 1, 2) for c in range(C)]
    H1 = [(idx(r, c), idx(r, c + 1)) for r in range(R) for c in range(1, C - 1, 2)]
    V1 = [(idx(r, c), idx(r + 1, c)) for r in range(1, R - 1, 2) for c in range(C)]
    if R == 1:  # chain (S2 rule): even pairs, odd pairs alternating
        return [H0, H1]
    return [H0, V0, H1, V1]


def gate_sequence(R, C, depth):
    L = grid_layers(R, C)
    return [(t, p) for t in range(depth) for p in L[t % len(L)]]


def manhattan(R, C, butterfly=0):
    br, bc = divmod(butterfly, C)
    return np.array([abs(q // C - br) + abs(q % C - bc) for q in range(R * C)])


def geometric_cone(R, C, depth, butterfly=0):
    """Qubits inside the causal cone of the butterfly after `depth` layers of U."""
    S = {butterfly}
    for _, (a, b) in gate_sequence(R, C, depth):
        if a in S or b in S:
            S |= {a, b}
    return S


def build_u_block(R, C, depth, seed):
    """Seeded Haar-random brickwork U as a u3+cz QuantumCircuit (3 CZ per Haar gate)."""
    from scipy.stats import unitary_group
    from qiskit import QuantumCircuit
    from qiskit.circuit.library import CZGate
    from qiskit.synthesis import TwoQubitBasisDecomposer
    rng = np.random.default_rng([seed, R, C, depth])
    dec = TwoQubitBasisDecomposer(CZGate(), basis_fidelity=1.0, euler_basis="U3")
    U = QuantumCircuit(R * C)
    for _, (a, b) in gate_sequence(R, C, depth):
        g = dec(unitary_group.rvs(4, random_state=rng))
        U.compose(g, qubits=[a, b], inplace=True)
    return U


def echo_circuit(U, butterfly, q):
    from qiskit import QuantumCircuit
    n = U.num_qubits
    Ud = U.inverse()
    qc = QuantumCircuit(n)
    qc.compose(U, inplace=True); qc.x(butterfly)
    qc.compose(Ud, inplace=True); qc.z(q)
    qc.compose(U, inplace=True); qc.x(butterfly)
    qc.compose(Ud, inplace=True)
    return qc


def echo_qasm(U_qasm, n, butterfly, q):
    """Rebuild the target-q echo circuit text from the stored U-block QASM (same as the samples)."""
    from qiskit import qasm2
    U = qasm2.loads(U_qasm)
    return qasm2.dumps(echo_circuit(U, butterfly, q))


def exact_vector(U, butterfly, threads=6, verbose=False):
    """Exact <Z_q> for every target q with Aer statevector (one run per q)."""
    from qiskit import transpile
    from qiskit.quantum_info import Pauli
    from qiskit_aer import AerSimulator
    n = U.num_qubits
    backend = AerSimulator(method="statevector", device="CPU", precision="double",
                           max_parallel_threads=threads, max_parallel_experiments=1)
    values, times = [], []
    for q in range(n):
        t0 = time.perf_counter()
        qc = echo_circuit(U, butterfly, q)
        qc.save_expectation_value(Pauli("I" * (n - 1 - q) + "Z" + "I" * q), range(n), label="z")
        qc = transpile(qc, backend, optimization_level=0, seed_transpiler=1)
        res = backend.run(qc, shots=None).result()
        v = float(np.real(res.data(0)["z"]))
        values.append(v); times.append(time.perf_counter() - t0)
        if verbose:
            print(f"  q{q:2d} {v:+.4f} ({times[-1]:.1f}s)", flush=True)
    return np.array(values), times


def instance_name(R, C, depth, seed):
    return f"{R}x{C}_d{depth}_s{seed}"


def load_instances(pattern=None):
    out = {}
    for f in sorted(os.listdir(DATA)):
        if f.startswith("exact_") and f.endswith(".json") and (pattern is None or pattern in f):
            with open(os.path.join(DATA, f)) as fh:
                out[f[6:-5]] = json.load(fh)
    return out


def pearson2(a, b):
    a, b = np.asarray(a, float), np.asarray(b, float)
    if np.std(a) == 0 or np.std(b) == 0 or not (np.isfinite(a).all() and np.isfinite(b).all()):
        return 0.0
    return float(np.corrcoef(a, b)[0, 1] ** 2)


def score(a, b):
    return 1000.0 * pearson2(a, b)


def g4_layers(depth=16):
    """G4 geometry: 6x6 grid plus q36 under q30 and q37 under q31 (row 6, cols 0-1); same period rule."""
    R, C = 7, 6
    L = grid_layers(R, C)
    keep = lambda p: all(q < 36 or q in (36, 37) for q in p)
    idx = lambda r, c: r * C + c
    return [[p for p in layer if keep(p)] for layer in L]


def contact_layer(layers, depth, butterfly=0, n=None):
    """Layer index (1-based) at which each qubit enters the support of W = U^dag X_b U.
    The operator X_b is conjugated by the layers of U in reverse order (last layer first),
    so the cone is grown through layers depth-1, depth-2, ..., 0.  Never reached -> inf."""
    n = n or (1 + max(q for layer in layers for p in layer for q in p))
    tc = np.full(n, np.inf)
    tc[butterfly] = 0
    S = {butterfly}
    for k in range(depth):
        t = depth - 1 - k  # layer of U being conjugated at step k
        for a, b in layers[t % len(layers)]:
            if a in S or b in S:
                for q in (a, b):
                    if q not in S:
                        tc[q] = k + 1
                S |= {a, b}
    return tc


def slack(R, C, depth, butterfly=0):
    """depth - contact layer: number of layers a qubit has been inside W's support (negative = never)."""
    tc = contact_layer(grid_layers(R, C), depth, butterfly, R * C)
    return np.where(np.isfinite(tc), depth - tc, -1)
