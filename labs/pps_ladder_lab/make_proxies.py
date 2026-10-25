"""Seeded 4x6 (or RxC) depth-16 Haar echo proxies with exact Aer vectors -> data/exact_{name}.json.
Usage: python make_proxies.py R C depth seed [seed...] [--threads=N]   ($0, local only)"""
import json, os, sys, time
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "src")); sys.path.insert(0, os.path.join(ROOT, "labs", "proxy_lab"))
import numpy as np
from qiskit import qasm2
from common import build_u_block, exact_vector, instance_name, manhattan, slack
DATA = os.path.join(HERE, "data"); os.makedirs(DATA, exist_ok=True)

def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    threads = next((int(a.split("=")[1]) for a in sys.argv[1:] if a.startswith("--threads=")), 6)
    R, C, depth = int(args[0]), int(args[1]), int(args[2])
    for seed in [int(s) for s in args[3:]]:
        name = instance_name(R, C, depth, seed); path = os.path.join(DATA, f"exact_{name}.json")
        if os.path.exists(path):
            print("exists", path); continue
        t0 = time.perf_counter(); U = build_u_block(R, C, depth, seed)
        print(f"{name}: {U.count_ops()} threads={threads}", flush=True)
        vec, times = exact_vector(U, 0, threads=threads, verbose=True)
        rec = {"rows": R, "cols": C, "depth": depth, "seed": seed, "butterfly": 0, "num_qubits": R * C,
               "u_block_qasm": qasm2.dumps(U), "exact": vec.tolist(), "per_q_seconds": times,
               "manhattan": manhattan(R, C, 0).tolist(), "slack": slack(R, C, depth, 0).tolist(),
               "total_seconds": time.perf_counter() - t0}
        json.dump(rec, open(path, "w"))
        print(f"wrote {path} in {rec['total_seconds']:.0f}s mean|v|={np.abs(vec).mean():.4f}", flush=True)

if __name__ == "__main__":
    main()
