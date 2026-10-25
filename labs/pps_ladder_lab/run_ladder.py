"""Local coefficient-PPS eps ladder (qiskit level 3) on the 4x6 proxies, every row, with a large term cap.
Usage: python run_ladder.py <R> <C> <seed> --eps=1e-3,3e-4,1e-4 --cap=2e7 --workers=4 [--rows=all|rim]
Writes data/ladder_{name}.json: {eps: {q: value|None}}, diag (peak terms, complete), seconds.   $0, local."""
import json, os, sys, time
os.environ.setdefault("OMP_NUM_THREADS", "1"); os.environ.setdefault("MKL_NUM_THREADS", "1")
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "src")); sys.path.insert(0, os.path.join(ROOT, "labs", "proxy_lab"))
import numpy as np
from common import build_u_block, echo_circuit, instance_name, slack
DATA = os.path.join(HERE, "data"); os.makedirs(DATA, exist_ok=True)

sys.path.insert(0, HERE)

def pg4c_slack():
    from common import grid_layers, contact_layer
    L = [[p for p in l if all(q < 30 or q in (30, 31) for q in p)] for l in grid_layers(6, 6)]
    tc = contact_layer(L, 16, 0, 32)
    return np.where(np.isfinite(tc), 16 - tc, -1)

def task(args):
    R, C, seed, q, eps, cap = args
    from qiskit import qasm2
    from bluequbit_samples.inputs import sample_from_text
    from bluequbit_samples.coefficient_pps import propagate
    U = build_u_block(R, C, 16, seed) if seed >= 0 else __import__("pg4c_reconstruct").build_U("A")
    s = sample_from_text(f"proxy_{q}", qasm2.dumps(echo_circuit(U, 0, q)), "lab", dataset_kind="synthetic", sample="proxy", qubit=q)
    t0 = time.perf_counter()
    try:
        v, d = propagate(s, eps, cap, level=3); err = None
    except Exception as exc:
        v, d, err = None, {}, f"{type(exc).__name__}: {exc}"
    return q, eps, v, {k: d.get(k) for k in ("complete", "peak_num_paulis", "final_num_paulis", "discarded_l1_sum")}, time.perf_counter() - t0, err

def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    opts = dict(a[2:].split("=", 1) for a in sys.argv[1:] if a.startswith("--"))
    R, C, seed = int(args[0]), int(args[1]), int(args[2])
    epss = [float(e) for e in opts.get("eps", "1e-3,3e-4,1e-4").split(",")]
    cap = int(float(opts.get("cap", "2e7"))); workers = int(opts.get("workers", "4"))
    name = instance_name(R, C, 16, seed) if seed >= 0 else "pg4c"; path = os.path.join(DATA, f"ladder_{name}.json")
    out = json.load(open(path)) if os.path.exists(path) else {"pps": {}, "diag": {}, "seconds": {}}
    sl = slack(R, C, 16, 0) if seed >= 0 else pg4c_slack()
    rows = list(range(R * C if seed >= 0 else 32)) if opts.get("rows", "all") == "all" else [int(q) for q in np.flatnonzero((sl >= 3) & (sl <= 7))]
    # rim rows first (slack ascending) so the interesting rows finish early
    rows = sorted(rows, key=lambda q: (sl[q] if sl[q] >= 0 else 99))
    tasks = [(R, C, seed, q, e, cap) for e in epss for q in rows if str(q) not in out["pps"].get(repr(e), {})]
    print(f"{name}: {len(tasks)} tasks, workers {workers}, cap {cap}", flush=True)
    from multiprocessing import Pool
    with Pool(workers) as pool:
        for q, e, v, d, secs, err in pool.imap_unordered(task, tasks):
            out["pps"].setdefault(repr(e), {})[str(q)] = v
            out["diag"].setdefault(repr(e), {})[str(q)] = d
            out["seconds"].setdefault(repr(e), {})[str(q)] = secs
            json.dump(out, open(path, "w"))
            print(f"  q{q:2d} slack {sl[q]:2.0f} eps {e:g}: {v} peak {d.get('peak_num_paulis')} complete {d.get('complete')} {secs:.0f}s {err or ''}", flush=True)

if __name__ == "__main__":
    main()
