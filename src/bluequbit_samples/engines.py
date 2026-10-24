"""Adapters around established numerical engines, with explicit approximation semantics."""

import math
import os
import time
from typing import Callable

from .inputs import parse_qasm
from .models import RunConfig, RunRecord, SampleCircuit
from .provenance import package_versions


def pauli_z_label(n, q):
    if not 0 <= q < n:
        raise ValueError("Target qubit outside the register")
    return "I" * (n - 1 - q) + "Z" + "I" * q


def _record(sample, method, parameters, backend):
    return RunRecord(
        circuit_id=sample.circuit_id, sample=sample.sample, qubit=sample.qubit,
        num_qubits=sample.num_qubits, qasm_sha256=sample.qasm_sha256,
        dataset_kind=sample.dataset_kind, method=method, parameters=parameters,
        status="FAILED", backend=backend, package_versions=package_versions(),
    )


def _finish(record, calculation: Callable):
    started = time.perf_counter()
    try:
        value, diagnostics = calculation()
        record.diagnostics.update(diagnostics)
        if value is None:
            record.status = "INCOMPLETE"
        else:
            value = complex(value)
            if abs(value.imag) > 1e-9 or not math.isfinite(value.real):
                raise ValueError(f"Invalid real expectation value: {value}")
            if abs(value.real) > 1 + 1e-8:
                raise ValueError(f"Expectation outside its physical range: {value.real}")
            record.estimate = float(value.real)  # Never silently clip simulator outputs.
            record.status = "SUCCEEDED"
    except Exception as exc:
        record.status = "FAILED"
        record.error = f"{type(exc).__name__}: {exc}"
    record.compute_seconds = time.perf_counter() - started
    record.wall_seconds = record.compute_seconds
    return record


def run_exact(sample: SampleCircuit, config: RunConfig | None = None):
    """Double-precision, noiseless, non-shot Aer reference; no dense unitary is built."""
    config = config or RunConfig()
    record = _record(sample, "exact", {"precision": "double", "shots": None, "result_zero_threshold": 0.0}, "qiskit_aer.statevector.cpu")
    state_bytes = 16 * 2**sample.num_qubits
    estimated_peak = 3 * state_bytes + 192 * 2**20
    record.diagnostics.update(statevector_bytes=state_bytes, estimated_memory_bytes=estimated_peak)
    if estimated_peak > config.effective_memory_mb() * 2**20:
        record.status = "SKIPPED_RESOURCE"
        record.error = "Statevector plus conservative workspace exceeds the available memory budget"
        return record

    def calculation():
        import numpy as np
        from qiskit import transpile
        from qiskit.quantum_info import Pauli, Statevector
        from qiskit_aer import AerSimulator
        circuit = parse_qasm(sample.qasm_text)
        observable = Pauli(pauli_z_label(sample.num_qubits, sample.qubit))
        executable = circuit.copy()
        executable.save_expectation_value(observable, range(sample.num_qubits), label="target_z")
        backend = AerSimulator(method="statevector", device="CPU", precision="double",
                               zero_threshold=0.0,
                               max_parallel_threads=config.cpu_threads, max_parallel_experiments=1,
                               max_memory_mb=config.effective_memory_mb())
        executable = transpile(executable, backend, optimization_level=0, seed_transpiler=20261024)
        result = backend.run(executable, shots=None).result()
        if not result.success:
            raise RuntimeError(str(result.status))
        value = result.data(0)["target_z"]
        diagnostics = {"reference_status": "EXACT_COMPUTED", "shots_used": False,
                       "observable": observable.to_label(), "device": "CPU"}
        if sample.num_qubits <= config.exact_crosscheck_max_qubits:
            independent = Statevector.from_instruction(circuit)
            check = complex(independent.expectation_value(observable))
            norm = float(np.vdot(independent.data, independent.data).real)
            error = abs(complex(value) - check)
            diagnostics.update(crosscheck_value=check.real, crosscheck_abs_error=error,
                               state_norm_squared=norm, crosscheck_atol=config.check_atol)
            if error > config.check_atol or abs(norm - 1) > config.check_atol:
                raise ValueError(f"Exact-path crosscheck failed: delta={error}, norm={norm}")
            diagnostics["reference_status"] = "EXACT_CROSSCHECKED"
        return value, diagnostics
    return _finish(record, calculation)


def run_mps(sample: SampleCircuit, chi=32, config: RunConfig | None = None):
    """quimb CircuitMPS with a bond cap and no additional singular-value cutoff."""
    config = config or RunConfig()
    if chi is not None and (not isinstance(chi, int) or isinstance(chi, bool) or chi < 1):
        raise ValueError("chi must be a positive integer or None")
    record = _record(sample, "mps", {"chi": chi, "svd_cutoff": 0.0}, "quimb.CircuitMPS.numpy")

    def calculation():
        import numpy as np
        import quimb.tensor as qtn
        circuit = parse_qasm(sample.qasm_text)
        mps = qtn.CircuitMPS(sample.num_qubits, max_bond=chi, cutoff=0.0,
                             gate_contract="swap+split", dtype="complex128")
        for instruction in circuit.data:
            if instruction.operation.name == "barrier":
                continue
            sites = [circuit.find_bit(q).index for q in instruction.qubits]
            # Only the documented one-qubit gates and symmetric CZ are admitted by the loader.
            matrix = np.asarray(instruction.operation.to_matrix(), dtype=np.complex128)
            mps.apply_gate_raw(matrix, tuple(sites))
        psi = mps.psi
        norm_squared = float(np.real(psi.norm() ** 2))
        if not math.isfinite(norm_squared) or norm_squared <= np.finfo(float).tiny:
            raise ValueError(f"Degenerate MPS norm: {norm_squared}")
        # Truncation can make a perfectly representable state very small.
        # Global normalization preserves the normalized expectation value.
        psi.normalize()
        z = np.diag(np.array([1.0, -1.0], dtype=np.complex128))
        # This API divides <psi|Z|psi> by <psi|psi>; a truncated state need not have unit norm.
        value = psi.local_expectation_canonical(z, (sample.qubit,), normalized=True)
        return value, {"max_bond_actual": int(psi.max_bond() or 1),
                       "state_norm_squared": norm_squared, "expectation_normalized": True,
                       "svd_cutoff": 0.0, "target_site": sample.qubit,
                       "routing": "Explicit swap+split; original site order restored"}
    return _finish(record, calculation)


def _single_gate_slices(circuit):
    slices = []
    for instruction in circuit.data:
        if instruction.operation.name == "barrier":
            continue
        piece = circuit.copy_empty_like()
        sites = [circuit.find_bit(q).index for q in instruction.qubits]
        piece.append(instruction.operation.copy(), sites)
        slices.append(piece)
    return slices


def run_coefficient_pps(sample, epsilon=1e-2, level=1, config=None):
    from .coefficient_pps import propagate
    config = config or RunConfig()
    record = _record(sample, "pps_threshold", {"epsilon": float(epsilon), "level": level},
                     "local.numpy.coefficient_pauli")
    return _finish(record, lambda: propagate(sample, epsilon, config.max_paulis, level))


def run_pps(sample: SampleCircuit, eta=1e-3, config: RunConfig | None = None):
    """OBP L1 *total error budget*, not BlueQubit's coefficient-threshold parameter."""
    config = config or RunConfig()
    if not math.isfinite(eta) or eta < 0:
        raise ValueError("eta must be a finite, nonnegative total error budget")
    record = _record(sample, "pps", {"eta": float(eta), "p_norm": 1,
                      "slicing": "one_gate", "simplify_atol": config.pps_simplify_atol,
                      "simplify_rtol": config.pps_simplify_rtol}, "qiskit_addon_obp")

    def calculation():
        import numpy as np
        from qiskit.quantum_info import SparsePauliOp
        from qiskit_addon_obp import backpropagate
        from qiskit_addon_obp.utils.simplify import OperatorBudget
        from qiskit_addon_obp.utils.truncating import setup_budget
        circuit = parse_qasm(sample.qasm_text)
        slices = _single_gate_slices(circuit)
        observable = SparsePauliOp(pauli_z_label(sample.num_qubits, sample.qubit))
        diagnostics = {"total_slices": len(slices), "eta_semantics": "OBP total L1 truncation-error budget",
                       "p_norm": 1, "max_paulis": config.max_paulis,
                       "simplify_atol": config.pps_simplify_atol,
                       "simplify_rtol": config.pps_simplify_rtol,
                       "gate_decomposition_default_atol": float(observable.atol),
                       "gate_decomposition_default_rtol": float(observable.rtol),
                       "note": "Zero active truncation does not remove library numerical simplification."}
        if not slices:
            diagnostics.update(remaining_slices=0, propagated_slices=0, final_num_paulis=1,
                               peak_num_paulis=1, per_slice_num_paulis=[], per_slice_errors=[])
            return 1.0, diagnostics
        operator_budget = OperatorBudget(max_paulis=config.max_paulis, simplify=True,
                                         atol=config.pps_simplify_atol, rtol=config.pps_simplify_rtol)
        error_budget = setup_budget(max_error_total=float(eta), num_slices=len(slices), p_norm=1)
        # Parent-process monitoring supplies a portable timeout (including Windows).
        propagated, remaining, metadata = backpropagate(
            observable, slices, operator_budget=operator_budget, truncation_error_budget=error_budget)
        if isinstance(propagated, list):
            propagated = propagated[0]
        applied = len(slices) - len(remaining)
        history = metadata.backpropagation_history[:applied]
        terms = [int(h.num_paulis[0]) for h in history]
        errors = [float(h.slice_errors[0]) for h in history]
        diagnostics.update(remaining_slices=len(remaining), propagated_slices=applied,
                           final_num_paulis=len(propagated), peak_num_paulis=max(terms, default=1),
                           per_slice_num_paulis=terms, per_slice_errors=errors,
                           accumulated_reported_truncation_error=sum(errors))
        if remaining:
            diagnostics["incomplete_reason"] = "Operator growth limit left an unpropagated circuit prefix"
            return None, diagnostics
        # On |0...0>, precisely the Pauli strings containing only I/Z contribute.
        diagonal = ~propagated.paulis.x.any(axis=1)
        return np.sum(propagated.coeffs[diagonal]), diagnostics
    return _finish(record, calculation)
