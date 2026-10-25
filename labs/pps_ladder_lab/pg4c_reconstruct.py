"""Attempt to reconstruct Kevin's PG4c circuit (make_proxy.py PG4c --grid 5 6 --extra 2 --layers 16 --butterfly 0 --seed 5)
from the historical scripts/make_proxy.py (commit e6707fa) plus a guessed --extra rule, then run local coefficient PPS
on chosen rows / eps and compare with the native values in labs/pg4c/pg4c.csv.
Usage: python pg4c_reconstruct.py <variant> <eps> <cap> q[,q...]
variant: A = rows=6 colour lists filtered to qubits <30 or in {30,31}  (common.g4_layers style, H0,H1,V0,V1 order)
         B = same but colour order H0,V0,H1,V1 (common.py order)
"""
import csv, os, sys, time
os.environ.setdefault("OMP_NUM_THREADS", "1")
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "src"))
import numpy as np

def edges(rows, cols, layers, order):
    idx = lambda r, c: r * cols + c
    H0 = [(idx(r, c), idx(r, c + 1)) for r in range(rows) for c in range(0, cols - 1, 2)]
    H1 = [(idx(r, c), idx(r, c + 1)) for r in range(rows) for c in range(1, cols - 1, 2)]
    V0 = [(idx(r, c), idx(r + 1, c)) for r in range(0, rows - 1, 2) for c in range(cols)]
    V1 = [(idx(r, c), idx(r + 1, c)) for r in range(1, rows - 1, 2) for c in range(cols)]
    colors = {"A": [H0, H1, V0, V1], "B": [H0, V0, H1, V1]}[order]
    return [colors[k % 4] for k in range(layers)]

def build_U(variant, seed=5, layers=16):
    from qiskit import QuantumCircuit, transpile
    from qiskit.quantum_info import random_unitary
    rng = np.random.default_rng(seed)
    n = 32
    U = QuantumCircuit(n)
    keep = lambda p: all(q < 30 or q in (30, 31) for q in p)
    for layer in edges(6, 6, layers, variant):
        for a, b in layer:
            if not keep((a, b)):
                continue
            s = int(rng.integers(2**31))
            U.unitary(random_unitary(4, seed=s), [a, b])
    return transpile(U, basis_gates=["u3", "cz"], optimization_level=1, seed_transpiler=0)

def echo(U, b, q):
    from qiskit import QuantumCircuit
    Ud = U.inverse(); qc = QuantumCircuit(U.num_qubits)
    qc.compose(U, inplace=True); qc.x(b); qc.compose(Ud, inplace=True); qc.z(q)
    qc.compose(U, inplace=True); qc.x(b); qc.compose(Ud, inplace=True)
    return qc

if __name__ == "__main__":
    variant, eps, cap = sys.argv[1], float(sys.argv[2]), int(float(sys.argv[3]))
    qs = [int(v) for v in sys.argv[4].split(",")]
    native = {int(r["q"]): r for r in csv.DictReader(open(os.path.join(ROOT, "labs", "pg4c", "pg4c.csv")))}
    from qiskit import qasm2
    from bluequbit_samples.inputs import sample_from_text
    from bluequbit_samples.coefficient_pps import propagate
    U = build_U(variant)
    print("variant", variant, U.count_ops(), flush=True)
    for q in qs:
        s = sample_from_text(f"pg4c_{q}", qasm2.dumps(echo(U, 0, q)), "lab", dataset_kind="synthetic", sample="pg4c", qubit=q)
        t0 = time.perf_counter(); v, d = propagate(s, eps, cap, level=3)
        print(f"q{q} eps{eps:g} local={v} native1e-4={native[q]['pps1e4L3']} native1e-3={native[q]['pps1e3L3']} exact={native[q]['exact']} peak={d['peak_num_paulis']} {time.perf_counter()-t0:.0f}s", flush=True)
