"""Exact <Z_q> for sample circuits from their QASM files, computed locally (free).

Each Duke_<C>_q circuit is an echo, so Qiskit's optimizer first cancels most
forward/backward gate pairs; Aer's statevector simulator then runs what is left.
30 qubits need about 9 GB in single precision and take a few minutes each.
Results append to the output CSV as they finish, so an interrupted run resumes.

    python scripts/local_exact.py problems/03_sample_S3/circuits scratch/calib/S3_exact.csv
"""

from __future__ import annotations

import argparse
import csv
import re
import time
from pathlib import Path


def expectation_z(path: Path, q: int, precision: str = "single") -> float:
    from qiskit import qasm2, transpile
    from qiskit.quantum_info import SparsePauliOp
    from qiskit_aer import AerSimulator

    qc = qasm2.load(str(path))
    n = qc.num_qubits
    reduced = transpile(qc, basis_gates=["u3", "cz"], optimization_level=3, seed_transpiler=0)
    reduced.save_expectation_value(SparsePauliOp("I" * (n - 1 - q) + "Z" + "I" * q), list(range(n)), label="z")
    result = AerSimulator(method="statevector", precision=precision).run(reduced, shots=1).result()
    return float(result.data()["z"])


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("circuits", type=Path, help="folder of Duke_<C>_<q>.qasm files")
    ap.add_argument("output", type=Path, help="CSV with circuit_id,value,seconds")
    ap.add_argument("--precision", choices=("single", "double"), default="single")
    args = ap.parse_args()

    files = sorted(args.circuits.glob("Duke_*_*.qasm"), key=lambda p: int(p.stem.rsplit("_", 1)[1]))
    done = set()
    if args.output.exists():
        done = {row["circuit_id"] for row in csv.DictReader(args.output.open())}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    new = not args.output.exists()
    with args.output.open("a", newline="") as f:
        w = csv.writer(f)
        if new:
            w.writerow(["circuit_id", "value", "seconds"])
        for path in files:
            if path.stem in done:
                continue
            q = int(re.fullmatch(r"Duke_\w+?_(\d+)", path.stem).group(1))
            t = time.time()
            value = expectation_z(path, q, args.precision)
            w.writerow([path.stem, repr(value), f"{time.time() - t:.1f}"])
            f.flush()
            print(f"{path.stem}: {value:.8f} ({time.time() - t:.0f}s)", flush=True)


if __name__ == "__main__":
    main()
