"""Exact (statevector) single-site <X_j>,<Y_j>,<Z_j> of the final state for S2 (16 qubits).

Reference for what the MPS features *should* look like; S3 (30 qubits) is too large
for a dense statevector here and is not attempted.

    .venv312/Scripts/python.exe labs/sample_lab/exact_features.py
"""

import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from mps_features import SAMPLE_DIRS, load_circuit  # noqa: E402


def main():
    from qiskit.quantum_info import Pauli, Statevector
    sample = "S2"
    out = {}
    ids = sorted(int(p.stem.split("_")[-1]) for p in SAMPLE_DIRS[sample].glob("*.qasm"))
    for qubit in ids:
        circuit = load_circuit(sample, qubit)
        n = circuit.num_qubits
        psi = Statevector.from_instruction(circuit)
        feats = {"qubit": qubit, "num_qubits": n}
        for name in "XYZ":
            feats[name] = [float(np.real(psi.expectation_value(Pauli("I" * (n - 1 - j) + name + "I" * j))))
                           for j in range(n)]
        out[f"Duke_{sample}_{qubit}"] = feats
        print(f"Duke_{sample}_{qubit} Zq={feats['Z'][qubit]:+.4f} meanZ={np.mean(feats['Z']):+.4f} "
              f"Z={np.round(feats['Z'], 3).tolist()}", flush=True)
    path = Path(__file__).with_name(f"exact_features_{sample}.json")
    path.write_text(json.dumps(out, indent=1))
    print("wrote", path)


if __name__ == "__main__":
    main()
