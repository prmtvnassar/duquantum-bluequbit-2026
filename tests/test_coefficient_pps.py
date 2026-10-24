import unittest
import numpy as np
from qiskit import QuantumCircuit, qasm2
from qiskit.quantum_info import Pauli, Statevector

from bluequbit_samples.coefficient_pps import propagate
from bluequbit_samples.engines import pauli_z_label
from bluequbit_samples.inputs import sample_from_text


class CoefficientPPSTests(unittest.TestCase):
    def test_untruncated_matches_independent_statevector(self):
        for seed in range(4):
            rng = np.random.default_rng(seed)
            circuit = QuantumCircuit(3)
            for _ in range(4):
                for q in range(3):
                    circuit.u(*rng.uniform(-np.pi, np.pi, 3), q)
                circuit.cz(0, 1)
                circuit.cz(1, 2)
                circuit.cz(2, 0)
            state = Statevector.from_instruction(circuit)
            for q in range(3):
                sample = sample_from_text(f"synthetic_{seed}_{q}", qasm2.dumps(circuit), "test",
                                          dataset_kind="synthetic", sample="TEST", qubit=q)
                for level in (0, 1):
                    value, diagnostic = propagate(sample, 0.0, 1000, level)
                    exact = state.expectation_value(Pauli(pauli_z_label(3, q))).real
                    self.assertTrue(diagnostic["complete"])
                    self.assertAlmostEqual(value, exact, places=10)

    def test_term_limit_does_not_return_partial_estimate(self):
        circuit = QuantumCircuit(2)
        circuit.u(0.5, 0.7, 0.2, 0)
        circuit.cz(0, 1)
        circuit.u(0.6, 0.3, 0.9, 1)
        sample = sample_from_text("synthetic", qasm2.dumps(circuit), "test",
                                  dataset_kind="synthetic", sample="TEST", qubit=1)
        value, diagnostic = propagate(sample, 0.0, 1, 0)
        self.assertIsNone(value)
        self.assertFalse(diagnostic["complete"])


if __name__ == "__main__":
    unittest.main()
