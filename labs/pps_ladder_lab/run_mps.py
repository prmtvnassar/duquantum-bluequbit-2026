"""Local quimb MPS (run_mps, swap+split, no svd cutoff) chi32/chi64 on every row of a 4x6 proxy (or pg4c, seed -1).
Usage: python run_mps.py R C seed --chi=32,64 --workers=2  -> data/mps_{name}.json"""
import json, os, sys, time
os.environ.setdefault("OMP_NUM_THREADS", "1"); os.environ.setdefault("MKL_NUM_THREADS", "1")
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "src")); sys.path.insert(0, os.path.join(ROOT, "labs", "proxy_lab")); sys.path.insert(0, HERE)
from common import build_u_block, echo_circuit, instance_name
DATA = os.path.join(HERE, "data")

def task(args):
    R, C, seed, q, chi = args
    from qiskit import qasm2
    from bluequbit_samples.inputs import sample_from_text
    from bluequbit_samples.engines import run_mps
    U = build_u_block(R, C, 16, seed) if seed >= 0 else __import__("pg4c_reconstruct").build_U("A")
    s = sample_from_text(f"proxy_{q}", qasm2.dumps(echo_circuit(U, 0, q)), "lab", dataset_kind="synthetic", sample="proxy", qubit=q)
    rec = run_mps(s, chi=chi)
    return q, chi, rec.estimate, rec.compute_seconds, rec.error

def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    opts = dict(a[2:].split("=", 1) for a in sys.argv[1:] if a.startswith("--"))
    R, C, seed = int(args[0]), int(args[1]), int(args[2])
    chis = [int(c) for c in opts.get("chi", "32,64").split(",")]; workers = int(opts.get("workers", "2"))
    name = instance_name(R, C, 16, seed) if seed >= 0 else "pg4c"; path = os.path.join(DATA, f"mps_{name}.json")
    out = json.load(open(path)) if os.path.exists(path) else {"mps": {}, "seconds": {}}
    n = R * C if seed >= 0 else 32
    tasks = [(R, C, seed, q, chi) for chi in chis for q in range(n) if str(q) not in out["mps"].get(str(chi), {})]
    print(f"{name}: {len(tasks)} tasks", flush=True)
    from multiprocessing import Pool
    with Pool(workers) as pool:
        for q, chi, v, secs, err in pool.imap_unordered(task, tasks):
            out["mps"].setdefault(str(chi), {})[str(q)] = v; out["seconds"].setdefault(str(chi), {})[str(q)] = secs
            json.dump(out, open(path, "w"))
            print(f"  chi{chi} q{q:2d}: {v} {secs:.0f}s {err or ''}", flush=True)

if __name__ == "__main__":
    main()
