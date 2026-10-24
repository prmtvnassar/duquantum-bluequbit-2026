"""Find which BlueQubit Pauli-path setting reproduces a known sample value.

BlueQubit's pauli-path returned exactly 0 for every S3/G3 circuit at the default
settings, while local Pauli propagation gives S3's real values. This runs one sample
circuit (default Duke_S3_1, exact ≈ -0.538) under several variants, one job at a time,
canceling any job still running after --max-runtime seconds.

    python scripts/pps_diagnose.py
"""

from __future__ import annotations

import argparse
import sys
import time

from runner.config import ROOT, get_client


def run(bq, circuit, n: int, q: int, eps: float, level: int, max_runtime: float) -> str:
    z = "I" * (n - 1 - q) + "Z" + "I" * q
    options = {"pauli_path_truncation_threshold": eps, "pauli_path_circuit_transpilation_level": level}
    job = bq.run(circuit, device="pauli-path", asynchronous=True, pauli_sum=[(z, 1.0)], options=options)
    start = time.time()
    while True:
        r = bq.get(job.job_id)
        if r.run_status in ("COMPLETED", "FAILED_VALIDATION", "TERMINATED", "CANCELED", "NOT_ENOUGH_FUNDS"):
            break
        if time.time() - start > max_runtime:
            bq.cancel(job.job_id)
            r = bq.get(job.job_id)
            break
        time.sleep(3)
    value = r.expectation_value
    value = value[0] if isinstance(value, list) else value
    return (f"{r.run_status:9} value={value!s:22} run={0 if r.run_time_ms is None else r.run_time_ms/1000:.1f}s "
            f"cost=${r.cost if r.cost is not None else 0}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--circuit", default="S3")
    ap.add_argument("--qubit", type=int, default=1)
    ap.add_argument("--max-runtime", type=float, default=300)
    args = ap.parse_args()

    from qiskit import qasm2

    bq = get_client()
    stored = f"Duke_{args.circuit}_{args.qubit}"
    n = bq.get_circuit_info(stored).num_qubits
    folder = {"S1": "01_sample_S1", "S2": "02_sample_S2", "S3": "03_sample_S3"}[args.circuit]
    uploaded = qasm2.load(str(ROOT / "problems" / folder / "circuits" / f"{stored}.qasm"))

    variants = [("stored ID", stored, 0.01, lvl) for lvl in (2, 0, 1, 3)]
    variants += [("stored ID", stored, eps, 2) for eps in (0.001, 0.0001)]
    variants += [("uploaded QASM", uploaded, 0.01, lvl) for lvl in (2, 0)]
    print(f"{stored}: {n} qubits, probe Z on q{args.qubit}")
    for label, circuit, eps, level in variants:
        try:
            result = run(bq, circuit, n, args.qubit, eps, level, args.max_runtime)
        except Exception as exc:
            result = f"error: {str(exc)[:150]}"
        print(f"  {label:13} eps={eps:<7g} level={level}: {result}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
