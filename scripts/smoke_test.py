"""Opt-in live SDK smoke test; it submits BlueQubit jobs and may use credits.

Multi-term Pauli sums on `pauli-path` may require additional account balance,
so the multi-term check requires --include-multi-term.
"""
import argparse
import time

import qiskit
from bluequbit.exceptions import BQJobNotCompleteError

from otoc.config import get_client


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--include-multi-term", action="store_true", help="Submit the optional multi-term PPS job")
    args = parser.parse_args()
    bq = get_client()

    qc = qiskit.QuantumCircuit(2)
    qc.h(0)
    qc.x(1)
    started = time.time()
    result = bq.run(qc, job_name="smoke_sv")
    print("statevector:", result.get_statevector(), f"({time.time() - started:.1f}s)")

    qc = qiskit.QuantumCircuit(3)
    qc.h([0, 1, 2])
    qc.ry(0.3, 0)
    qc.rz(0.6, 1)
    qc.rx(0.7, 2)

    def compare(pauli_sum, label):
        try:
            pp = bq.run(qc, device="pauli-path", pauli_sum=pauli_sum,
                        options={"pauli_path_truncation_threshold": 0.1})
            mps = bq.run(qc, device="mps.cpu", pauli_sum=pauli_sum)
        except BQJobNotCompleteError as exc:
            print(f"{label}: SKIPPED -> {exc}")
            return
        print(f"{label}: pauli-path={pp.expectation_value}  mps={mps.expectation_value}")

    compare([("XII", 1.0)], "single-term")
    if args.include_multi_term:
        compare([("XYZ", 0.5), ("XXX", 0.2), ("XII", 0.3), ("III", 0.4)], "multi-term")


if __name__ == "__main__":
    main()
