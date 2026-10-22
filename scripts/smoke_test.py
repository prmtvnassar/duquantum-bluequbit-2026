"""Smoke test: statevector job, then Pauli-path vs MPS on a small circuit (SDK docs example 7).

Multi-term Pauli sums on `pauli-path` need an account balance of at least $25 (NOT_ENOUGH_FUNDS
otherwise), so the free-tier check uses a single-term sum and the multi-term check is optional.
"""
import time

import qiskit
from bluequbit.exceptions import BQJobNotCompleteError

from otoc.config import get_client

bq = get_client()

qc = qiskit.QuantumCircuit(2)
qc.h(0)
qc.x(1)
t = time.time()
print("statevector:", bq.run(qc, job_name="smoke_sv").get_statevector(), f"({time.time() - t:.1f}s)")

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
    except BQJobNotCompleteError as e:
        print(f"{label}: SKIPPED -> {e}")
        return
    print(f"{label}: pauli-path={pp.expectation_value}  mps(exact)={mps.expectation_value}")


compare([("XII", 1.0)], "single-term")
compare([("XYZ", 0.5), ("XXX", 0.2), ("XII", 0.3), ("III", 0.4)], "multi-term (needs $25 balance)")
