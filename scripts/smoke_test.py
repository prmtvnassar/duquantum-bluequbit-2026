"""Smoke test: one tiny statevector job + one Pauli-path vs MPS comparison (SDK docs example 7)."""
import time

import qiskit

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
pauli_sum = [("XYZ", 0.5), ("XXX", 0.2), ("XII", 0.3), ("III", 0.4)]
pp = bq.run(qc, device="pauli-path", pauli_sum=pauli_sum, options={"pauli_path_truncation_threshold": 0.1})
mps = bq.run(qc, device="mps.cpu", pauli_sum=pauli_sum)
print("pauli-path:", pp.expectation_value, " mps (exact):", mps.expectation_value)
