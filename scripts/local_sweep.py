"""Run MPS / Pauli-path / exact locally on a folder of Duke_*.qasm files (free).

Results append to a CSV (circuit_id,method,setting,value,seconds,status), so reruns
skip finished work. Compare against exact values with scripts/calibrate.py.

    python scripts/local_sweep.py problems/03_sample_S3/circuits --method pps --settings 0.01 0.003 0.001 \
        --out scratch/calib/S3_sweep.csv --workers 4
"""

from __future__ import annotations

import argparse
import csv
import re
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

FIELDS = ["circuit_id", "method", "setting", "value", "seconds", "status"]


def run_one(path: str, method: str, setting: float) -> dict:
    from qiskit import qasm2

    from runner.local_sim import exact_z, mps_z, pps_z

    stem = Path(path).stem
    q = int(re.fullmatch(r".+_(\d+)", stem).group(1))
    t = time.time()
    try:
        qc = qasm2.load(path)
        if method == "exact":
            value = exact_z(qc, q, threads=1)
        elif method == "mps":
            value = mps_z(qc, q, int(setting))
        else:
            value = pps_z(qc, q, setting)
        status = "ok"
    except MemoryError as exc:  # Pauli-path term explosion at this threshold
        value, status = float("nan"), f"too many terms: {exc}"
    return {"circuit_id": stem, "method": method, "setting": repr(setting), "value": repr(value),
            "seconds": f"{time.time() - t:.2f}", "status": status}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("circuits", type=Path, help="folder of Duke_<C>_<q>.qasm files")
    ap.add_argument("--method", choices=("mps", "pps", "exact"), required=True)
    ap.add_argument("--settings", type=float, nargs="+", default=[0.0], help="χ for mps, ε for pps")
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--qubits", type=int, nargs="+", help="only these qubit indices")
    args = ap.parse_args()

    files = sorted(args.circuits.glob("*.qasm"), key=lambda p: int(p.stem.rsplit("_", 1)[1]))
    if args.qubits:
        files = [f for f in files if int(f.stem.rsplit("_", 1)[1]) in set(args.qubits)]
    done = set()
    if args.out.exists():
        done = {(r["circuit_id"], r["method"], float(r["setting"])) for r in csv.DictReader(args.out.open())}
    todo = [(str(f), args.method, s) for s in args.settings for f in files
            if (f.stem, args.method, float(s)) not in done]
    print(f"{len(todo)} runs ({len(done)} already in {args.out})", flush=True)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    new = not args.out.exists()
    with args.out.open("a", newline="") as f, ProcessPoolExecutor(args.workers) as pool:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        if new:
            w.writeheader()
        for fut in as_completed([pool.submit(run_one, *t) for t in todo]):
            row = fut.result()
            w.writerow(row)
            f.flush()
            print(f"{row['circuit_id']} {row['method']} {row['setting']}: {row['value']} ({row['seconds']}s) {row['status']}",
                  flush=True)


if __name__ == "__main__":
    main()
