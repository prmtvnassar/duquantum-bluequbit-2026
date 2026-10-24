"""Explicitly synthetic numerical checks; never official sample substitutes."""

import math

from .inputs import sample_from_text
from .models import RunConfig
from .runtime import execute


def synthetic_cases():
    import numpy as np
    from qiskit import QuantumCircuit, qasm2
    from qiskit.quantum_info import Statevector, Pauli
    cases = []
    zero = QuantumCircuit(3)
    cases.append(("zero_state", zero, 0, 1.0))
    last = QuantumCircuit(3)
    last.x(2)
    cases.append(("x_last_qubit", last, 2, -1.0))
    asymmetric = QuantumCircuit(3)
    asymmetric.x(0)
    cases.append(("asymmetric_order", asymmetric, 2, 1.0))
    rotation = QuantumCircuit(1)
    rotation.u(0.73, 0.42, -0.19, 0)
    cases.append(("complex_rotation", rotation, 0, math.cos(0.73)))
    nonlocal_cz = QuantumCircuit(3)
    nonlocal_cz.u(math.pi / 2, 0, math.pi, 0)
    nonlocal_cz.u(math.pi / 2, 0, math.pi, 2)
    nonlocal_cz.cz(0, 2)
    nonlocal_cz.u(math.pi / 2, 0, math.pi, 0)
    cases.append(("nonadjacent_cz", nonlocal_cz, 0, 0.0))
    rng = np.random.default_rng(20261024)
    random = QuantumCircuit(4)
    for _ in range(3):
        for q in range(4):
            random.u(*rng.uniform(-2, 2, 3), q)
        random.cz(0, 3)
        random.cz(1, 2)
    cases.append(("seeded_random", random, 1, None))
    tiny = QuantumCircuit(1)
    tiny.u(1e-10, 0.4, -0.2, 0)
    tiny.u(0.91, 0.2, 0.6, 0)
    cases.append(("near_zero_coefficient", tiny, 0, None))
    results = []
    for name, circuit, q, analytic in cases:
        if analytic is None:
            label = "I" * (circuit.num_qubits - q - 1) + "Z" + "I" * q
            analytic = float(Statevector.from_instruction(circuit).expectation_value(Pauli(label)).real)
        sample = sample_from_text(f"CHECK_{name}", qasm2.dumps(circuit), "built-in synthetic correctness check",
                                  dataset_kind="synthetic", sample="SYNTHETIC_CHECKS", qubit=q)
        results.append((name, sample, analytic))
    return results


def run_checks(output_dir="results/validation", config=None, progress=False):
    import pandas as pd
    from .provenance import atomic_json
    config = config or RunConfig(walltime_seconds=180)
    rows, records = [], []
    for name, sample, expected in synthetic_cases():
        for method, parameter, atol in [("exact", {}, 1e-10), ("mps", {"chi": None}, 1e-10),
                                         ("pps", {"eta": 0.0}, 1e-7)]:
            record = execute(sample, method, parameter, config, output_dir)
            records.append(record)
            delta = abs(record.estimate - expected) if record.succeeded else None
            rows.append(dict(case=name, method=method, expected=expected, estimate=record.estimate,
                             abs_error=delta, atol=atol, status=record.status,
                             passed=record.succeeded and delta <= atol,
                             wall_seconds=record.wall_seconds, peak_rss=record.peak_rss,
                             dataset_kind="synthetic"))
            if progress:
                print(name, method, record.status, delta, flush=True)
    result = pd.DataFrame(rows)
    from pathlib import Path
    path = Path(output_dir)
    result.to_csv(path / "checks.csv", index=False, float_format="%.17g")
    atomic_json(path / "check_records.json", [r.to_dict() for r in records])
    return result
