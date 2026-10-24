"""Offline package and numerical smoke test; no cloud jobs or credits."""
import qiskit


def main() -> None:
    import importlib
    from qiskit.quantum_info import Statevector
    for module in ("otoc", "bluequbit", "qiskit", "qiskit_aer", "quimb",
                   "qiskit_addon_obp", "qiskit_addon_utils"):
        importlib.import_module(module)
        print(f"{module}: import OK")
    circuit = qiskit.QuantumCircuit(2)
    circuit.h(0)
    circuit.cx(0, 1)
    assert abs(Statevector(circuit).probabilities()[0] - .5) < 1e-12
    print("Bell-state numerical check OK; no cloud jobs submitted")


if __name__ == "__main__":
    main()
