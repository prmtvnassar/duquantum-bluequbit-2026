"""Generate small stand-in circuits shaped like the hidden ones, for free local tuning.

Same construction as the challenge files: per probe qubit q, the echo
U, X_b, U^dag, Z_q, U, X_b, U^dag in u3 + cz gates, saved as Duke_<name>_<q>.qasm.
U is a brickwork of two-qubit gates on a chain or grid:
  haar     Haar-random two-qubit gates            (G1, G2: chain;  G4: grid)
  clifford random two-qubit Cliffords, each replaced by a Haar gate with probability p
           ("mostly Clifford", like S3 and G3)

    python scripts/make_proxy.py PG4 --grid 4 6 --layers 16 --butterfly 0 --gates haar --seed 4
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np


def edges_by_layer(rows: int, cols: int, layers: int) -> list[list[tuple[int, int]]]:
    """Edge sets cycled per layer: chain = even/odd bonds; grid = 4 colors (H even, H odd, V even, V odd)."""
    idx = lambda r, c: r * cols + c
    if rows == 1:
        colors = [[(i, i + 1) for i in range(s, cols - 1, 2)] for s in (0, 1)]
    else:
        colors = [
            [(idx(r, c), idx(r, c + 1)) for r in range(rows) for c in range(0, cols - 1, 2)],
            [(idx(r, c), idx(r, c + 1)) for r in range(rows) for c in range(1, cols - 1, 2)],
            [(idx(r, c), idx(r + 1, c)) for r in range(0, rows - 1, 2) for c in range(cols)],
            [(idx(r, c), idx(r + 1, c)) for r in range(1, rows - 1, 2) for c in range(cols)],
        ]
    return [colors[k % len(colors)] for k in range(layers)]


def build_U(rows: int, cols: int, layers: int, gates: str, p: float, rng):
    from qiskit import QuantumCircuit, transpile
    from qiskit.quantum_info import random_clifford, random_unitary

    n = rows * cols
    U = QuantumCircuit(n)
    for layer in edges_by_layer(rows, cols, layers):
        for a, b in layer:
            seed = int(rng.integers(2**31))
            if gates == "haar" or rng.random() < p:
                U.unitary(random_unitary(4, seed=seed), [a, b])
            else:
                U.append(random_clifford(2, seed=seed).to_instruction(), [a, b])
    return transpile(U, basis_gates=["u3", "cz"], optimization_level=1, seed_transpiler=0)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("name", help="problem label, e.g. PG4 (files are Duke_<name>_<q>.qasm)")
    shape = ap.add_mutually_exclusive_group(required=True)
    shape.add_argument("--chain", type=int, metavar="N")
    shape.add_argument("--grid", type=int, nargs=2, metavar=("ROWS", "COLS"))
    ap.add_argument("--layers", type=int, required=True)
    ap.add_argument("--butterfly", type=int, required=True)
    ap.add_argument("--gates", choices=("haar", "clifford"), default="haar")
    ap.add_argument("--p", type=float, default=0.15, help="Haar probability for --gates clifford")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--out", type=Path, default=Path("scratch/proxies"))
    args = ap.parse_args()

    from qiskit import QuantumCircuit, qasm2

    rows, cols = (1, args.chain) if args.chain else args.grid
    U = build_U(rows, cols, args.layers, args.gates, args.p, np.random.default_rng(args.seed))
    Ud = U.inverse()
    n = U.num_qubits
    folder = args.out / args.name
    folder.mkdir(parents=True, exist_ok=True)
    for q in range(n):
        qc = QuantumCircuit(n)
        qc.compose(U, inplace=True); qc.x(args.butterfly); qc.compose(Ud, inplace=True)
        qc.z(q)
        qc.compose(U, inplace=True); qc.x(args.butterfly); qc.compose(Ud, inplace=True)
        (folder / f"Duke_{args.name}_{q}.qasm").write_text(qasm2.dumps(qc))
    cz = sum(1 for i in U.data if i.operation.name == "cz")
    print(f"{args.name}: {n} qubits, {args.layers} layers, butterfly q{args.butterfly}, {cz} cz per U -> {folder}")


if __name__ == "__main__":
    main()
