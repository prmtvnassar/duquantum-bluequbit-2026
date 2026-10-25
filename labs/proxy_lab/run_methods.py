"""Run local approximate methods on the proxy instances ($0, local only).
Usage: python run_methods.py <instance-name-pattern> [--chi=8,16,32,64,128] [--eps=1e-2,1e-3,1e-4]
                             [--workers=4] [--skip-pps] [--skip-mps] [--level=3]
Writes/updates data/methods_{instance}.json with per-q MPS values per chi and PPS values per eps."""
import json
import os
import sys
import time

os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")

import numpy as np

from common import DATA, echo_qasm, load_instances


def _sample(inst, q):
    from bluequbit_samples.inputs import sample_from_text
    text = echo_qasm(inst["u_block_qasm"], inst["num_qubits"], inst["butterfly"], q)
    return sample_from_text(f"proxy_{q}", text, "proxy_lab", dataset_kind="synthetic",
                            sample="proxy", qubit=q)


def mps_task(args):
    inst, q, chi = args
    from bluequbit_samples.engines import run_mps
    rec = run_mps(_sample(inst, q), chi=chi)
    return q, chi, rec.estimate, rec.status, rec.compute_seconds, rec.error


def pps_task(args):
    inst, q, eps, level, max_paulis = args
    from bluequbit_samples.coefficient_pps import propagate
    t0 = time.perf_counter()
    try:
        value, diag = propagate(_sample(inst, q), eps, max_paulis, level)
        err = None
    except Exception as exc:  # keep going; record the failure
        value, diag, err = None, {}, f"{type(exc).__name__}: {exc}"
    return q, eps, value, {k: diag.get(k) for k in ("complete", "peak_num_paulis", "final_num_paulis",
                                                      "discarded_l1_sum", "incomplete_reason")}, \
        time.perf_counter() - t0, err


def main():
    pattern = [a for a in sys.argv[1:] if not a.startswith("--")]
    pattern = pattern[0] if pattern else None
    opts = dict(a[2:].split("=", 1) if "=" in a else (a[2:], "1") for a in sys.argv[1:] if a.startswith("--"))
    chis = [int(c) for c in opts.get("chi", "8,16,32,64,128").split(",")]
    epss = [float(e) for e in opts.get("eps", "1e-2,1e-3,1e-4").split(",")]
    workers = int(opts.get("workers", "4"))
    level = int(opts.get("level", "3"))
    max_paulis = int(opts.get("max-paulis", "200000"))
    from multiprocessing import Pool
    for name, inst in load_instances(pattern).items():
        path = os.path.join(DATA, f"methods_{name}.json")
        out = json.load(open(path)) if os.path.exists(path) else {"mps": {}, "mps_seconds": {}, "pps": {},
                                                                  "pps_diag": {}, "pps_seconds": {}}
        n = inst["num_qubits"]
        todo_chi = [c for c in chis if str(c) not in out["mps"]] if "skip-mps" not in opts else []
        todo_eps = [e for e in epss if repr(e) not in out["pps"]] if "skip-pps" not in opts else []
        print(f"{name}: n={n} chi todo {todo_chi} eps todo {todo_eps}", flush=True)
        with Pool(workers) as pool:
            if todo_chi:
                t0 = time.perf_counter()
                res = {}
                tasks = [(inst, q, c) for c in sorted(todo_chi, reverse=True) for q in range(n)]
                for q, chi, v, status, secs, err in pool.imap_unordered(mps_task, tasks):
                    res.setdefault(chi, {})[q] = (v, secs)
                    if err:
                        print(f"  MPS chi{chi} q{q} {status}: {err}", flush=True)
                for chi in todo_chi:
                    out["mps"][str(chi)] = [res[chi][q][0] for q in range(n)]
                    out["mps_seconds"][str(chi)] = [res[chi][q][1] for q in range(n)]
                    print(f"  chi{chi}: mean {np.mean(out['mps_seconds'][str(chi)]):.1f}s/q, "
                          f"score vs exact {1000*np.corrcoef(out['mps'][str(chi)], inst['exact'])[0,1]**2:.0f}", flush=True)
                print(f"  MPS wall {time.perf_counter()-t0:.0f}s", flush=True)
                json.dump(out, open(path, "w"))
            if todo_eps:
                t0 = time.perf_counter()
                res = {}
                tasks = [(inst, q, e, level, max_paulis) for e in sorted(todo_eps, reverse=True) for q in range(n)]
                for q, eps, v, diag, secs, err in pool.imap_unordered(pps_task, tasks):
                    res.setdefault(eps, {})[q] = (v, diag, secs)
                    if err:
                        print(f"  PPS eps{eps} q{q}: {err}", flush=True)
                for eps in todo_eps:
                    out["pps"][repr(eps)] = [res[eps][q][0] for q in range(n)]
                    out["pps_diag"][repr(eps)] = [res[eps][q][1] for q in range(n)]
                    out["pps_seconds"][repr(eps)] = [res[eps][q][2] for q in range(n)]
                    vals = out["pps"][repr(eps)]
                    filled = [0.0 if v is None else v for v in vals]
                    sc = 0.0 if np.std(filled) == 0 else 1000*np.corrcoef(filled, inst["exact"])[0,1]**2
                    print(f"  eps{eps}: mean {np.mean(out['pps_seconds'][repr(eps)]):.1f}s/q, "
                          f"{sum(v is None for v in vals)} incomplete, max|v|={max(abs(x) for x in filled):.4f}, "
                          f"score vs exact {sc:.0f}", flush=True)
                print(f"  PPS wall {time.perf_counter()-t0:.0f}s", flush=True)
                json.dump(out, open(path, "w"))


if __name__ == "__main__":
    main()
