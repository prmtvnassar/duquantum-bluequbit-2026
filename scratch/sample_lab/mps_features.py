"""Local quimb MPS feature extraction for the public samples (S2, S3), $0, no BlueQubit client.

For every sample ID and every bond cap chi this builds the final MPS exactly like
``src/bluequbit_samples/engines.py::run_mps`` (CircuitMPS, swap+split, cutoff 0,
complex128) and records, from the final state:

* all single-site <Z_j>, <X_j>, <Y_j> (normalized expectation values),
* the un-normalized norm^2 (quimb's fidelity_estimate: product of kept weights),
* the bipartite entanglement entropy at every cut and the actual max bond,
* wall time per (ID, chi).

Output: one JSON per sample under scratch/sample_lab/features_<sample>.json.

Usage (from repo root, PYTHONPATH=src):
    .venv312/Scripts/python.exe scratch/sample_lab/mps_features.py --sample S2 --chis 4 8 16 32 64
    .venv312/Scripts/python.exe scratch/sample_lab/mps_features.py --sample S3 --chis 8 16 32 64 --ids 14 0
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from bluequbit_samples.inputs import parse_qasm  # noqa: E402

SAMPLE_DIRS = {
    "S2": ROOT / "problems" / "02_sample_S2" / "circuits",
    "S3": ROOT / "problems" / "03_sample_S3" / "circuits",
}
PAULIS = {
    "X": np.array([[0, 1], [1, 0]], dtype=np.complex128),
    "Y": np.array([[0, -1j], [1j, 0]], dtype=np.complex128),
    "Z": np.array([[1, 0], [0, -1]], dtype=np.complex128),
}


def load_circuit(sample, qubit):
    path = SAMPLE_DIRS[sample] / f"Duke_{sample}_{qubit}.qasm"
    return parse_qasm(path.read_text())


def mps_features(circuit, chi):
    import quimb.tensor as qtn
    n = circuit.num_qubits
    mps = qtn.CircuitMPS(n, max_bond=chi, cutoff=0.0, gate_contract="swap+split", dtype="complex128")
    for instruction in circuit.data:
        if instruction.operation.name == "barrier":
            continue
        sites = [circuit.find_bit(q).index for q in instruction.qubits]
        matrix = np.asarray(instruction.operation.to_matrix(), dtype=np.complex128)
        mps.apply_gate_raw(matrix, tuple(sites))
    psi = mps.psi
    norm_squared = float(np.real(psi.norm() ** 2))
    psi.normalize()
    out = {"norm_squared": norm_squared, "max_bond_actual": int(psi.max_bond() or 1)}
    for name, matrix in PAULIS.items():
        vals = []
        for j in range(n):
            v = psi.local_expectation_canonical(matrix, (j,), normalized=True)
            vals.append(float(np.real(v)))
        out[name] = vals
    out["entropy"] = [float(psi.entropy(i)) for i in range(1, n)]
    return out


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--sample", required=True, choices=sorted(SAMPLE_DIRS))
    parser.add_argument("--chis", type=int, nargs="+", required=True)
    parser.add_argument("--ids", type=int, nargs="*", default=None)
    parser.add_argument("--out", default=None)
    parser.add_argument("--threads", type=int, default=4)
    args = parser.parse_args()
    for var in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
        os.environ.setdefault(var, str(args.threads))
    np.random.seed(20261024)

    ids = args.ids
    if ids is None:
        ids = sorted(int(p.stem.split("_")[-1]) for p in SAMPLE_DIRS[args.sample].glob("*.qasm"))
    out_path = Path(args.out) if args.out else Path(__file__).with_name(f"features_{args.sample}.json")
    data = {}
    if out_path.exists():
        data = json.loads(out_path.read_text())
    for qubit in ids:
        circuit = load_circuit(args.sample, qubit)
        key = f"Duke_{args.sample}_{qubit}"
        entry = data.setdefault(key, {"qubit": qubit, "num_qubits": circuit.num_qubits, "chi": {}})
        for chi in args.chis:
            if str(chi) in entry["chi"]:
                continue
            t0 = time.perf_counter()
            feats = mps_features(circuit, chi)
            feats["seconds"] = time.perf_counter() - t0
            entry["chi"][str(chi)] = feats
            print(f"{key} chi={chi:3d} Zq={feats['Z'][qubit]:+.4f} meanZ={np.mean(feats['Z']):+.4f} "
                  f"norm2={feats['norm_squared']:.4f} maxS={max(feats['entropy']):.3f} "
                  f"t={feats['seconds']:.1f}s", flush=True)
            out_path.write_text(json.dumps(data, indent=1))
    print("wrote", out_path)


if __name__ == "__main__":
    main()
