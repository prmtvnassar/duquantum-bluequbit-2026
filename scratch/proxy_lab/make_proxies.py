"""Generate seeded Haar echo proxies and their exact OTOC(2) vectors.
Usage: python make_proxies.py R C depth seed [seed ...] [--threads N]
Writes data/exact_{R}x{C}_d{depth}_s{seed}.json ($0, local Aer only)."""
import json
import os
import sys
import time

import numpy as np
from qiskit import qasm2

from common import DATA, build_u_block, exact_vector, instance_name, manhattan, geometric_cone


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    threads = 6
    for a in sys.argv[1:]:
        if a.startswith("--threads="):
            threads = int(a.split("=")[1])
    R, C, depth = int(args[0]), int(args[1]), int(args[2])
    seeds = [int(s) for s in args[3:]]
    butterfly = 0
    for seed in seeds:
        name = instance_name(R, C, depth, seed)
        path = os.path.join(DATA, f"exact_{name}.json")
        if os.path.exists(path):
            print("exists", path); continue
        t0 = time.perf_counter()
        U = build_u_block(R, C, depth, seed)
        print(f"{name}: U has {U.count_ops()} ; computing exact vector with {threads} threads", flush=True)
        vec, times = exact_vector(U, butterfly, threads=threads, verbose=True)
        cone = geometric_cone(R, C, depth, butterfly)
        rec = {
            "rows": R, "cols": C, "depth": depth, "seed": seed, "butterfly": butterfly,
            "num_qubits": R * C, "u_block_qasm": qasm2.dumps(U),
            "cz_per_block": int(U.count_ops().get("cz", 0)),
            "exact": vec.tolist(), "per_q_seconds": times,
            "manhattan": manhattan(R, C, butterfly).tolist(),
            "inside_geometric_cone": [int(q in cone) for q in range(R * C)],
            "total_seconds": time.perf_counter() - t0,
        }
        with open(path, "w") as fh:
            json.dump(rec, fh)
        print(f"wrote {path} in {rec['total_seconds']:.1f}s; mean|v|={np.abs(vec).mean():.3f} "
              f"min={vec.min():+.3f} max={vec.max():+.3f}", flush=True)


if __name__ == "__main__":
    main()
