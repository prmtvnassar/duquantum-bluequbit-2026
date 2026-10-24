"""Local sparse Pauli propagation with a coefficient cutoff after each gate.

This implements the cutoff concept used by the workflow. It is an independent
implementation, not BlueQubit's kernel or its rotation-based transpiler.
"""

import numpy as np

from .inputs import parse_qasm


PAULIS = np.array([
    [[1, 0], [0, 1]], [[0, 1], [1, 0]],
    [[1, 0], [0, -1]], [[0, -1j], [1j, 0]],
], dtype=np.complex128)  # index = x + 2*z: I, X, Z, Y


def _merge(x, z, coefficients):
    order = np.lexsort((z, x))
    x, z, coefficients = x[order], z[order], coefficients[order]
    starts = np.r_[0, np.flatnonzero((x[1:] != x[:-1]) | (z[1:] != z[:-1])) + 1]
    return x[starts], z[starts], np.add.reduceat(coefficients, starts)


def propagate(sample, epsilon, max_paulis, level=1, numerical_atol=1e-12):
    from qiskit import transpile

    if not np.isfinite(epsilon) or epsilon < 0 or max_paulis < 1:
        raise ValueError("Invalid Pauli cutoff or term limit")
    if sample.num_qubits > 63:
        raise ValueError("Local bitmask engine supports at most 63 qubits")
    if level not in (0, 1, 2, 3):
        raise ValueError("Qiskit optimization level must be 0, 1, 2 or 3")
    circuit = parse_qasm(sample.qasm_text)
    circuit = transpile(circuit, basis_gates=["u3", "cz"], optimization_level=level,
                        seed_transpiler=20261024)
    x = np.array([0], dtype=np.uint64)
    z = np.array([1 << sample.qubit], dtype=np.uint64)
    coefficients = np.array([1.0])
    peak, discarded_l1, processed = 1, 0.0, 0
    transfer_cache = {}
    gates = [g for g in circuit.data if g.operation.name != "barrier"]
    for instruction in reversed(gates):
        sites = [circuit.find_bit(q).index for q in instruction.qubits]
        if len(sites) == 2:
            if instruction.operation.name != "cz":
                raise ValueError("Only CZ two-qubit gates are supported")
            a, b = sites
            xa, xb = (x >> a) & 1, (x >> b) & 1
            za, zb = (z >> a) & 1, (z >> b) & 1
            sign = (xa & xb & (za ^ zb)).astype(np.int8)
            coefficients *= 1 - 2 * sign
            z ^= (xb << a) | (xa << b)
        elif len(sites) == 1:
            site = sites[0]
            mask = np.uint64(1 << site)
            matrix = np.asarray(instruction.operation.to_matrix(), dtype=np.complex128)
            key = matrix.tobytes()
            transfer = transfer_cache.get(key)
            if transfer is None:
                transfer = np.array([[np.trace(po @ matrix.conj().T @ pi @ matrix).real / 2
                                      for pi in PAULIS] for po in PAULIS])
                transfer[np.abs(transfer) < numerical_atol] = 0.0
                transfer[np.abs(transfer - 1) < numerical_atol] = 1.0
                transfer[np.abs(transfer + 1) < numerical_atol] = -1.0
                transfer_cache[key] = transfer
            labels = (((x >> site) & 1) + 2 * ((z >> site) & 1)).astype(np.int8)
            if np.all(np.count_nonzero(transfer, axis=0) == 1):
                mapped = np.argmax(np.abs(transfer), axis=0)[labels]
                coefficients *= transfer[mapped, labels]
                x = (x & ~mask) | ((mapped.astype(np.uint64) & 1) << site)
                z = (z & ~mask) | (((mapped.astype(np.uint64) >> 1) & 1) << site)
            else:
                xs, zs, cs = [], [], []
                for output in range(4):
                    factors = transfer[output, labels]
                    keep = factors != 0
                    if not keep.any():
                        continue
                    xs.append((x[keep] & ~mask) | (np.uint64(output & 1) << np.uint64(site)))
                    zs.append((z[keep] & ~mask) | (np.uint64(output >> 1) << np.uint64(site)))
                    cs.append(coefficients[keep] * factors[keep])
                x, z, coefficients = _merge(np.concatenate(xs), np.concatenate(zs), np.concatenate(cs))
        else:
            raise ValueError("Unexpected gate arity")
        keep = (np.abs(coefficients) >= epsilon) & (coefficients != 0)
        discarded_l1 += float(np.abs(coefficients[~keep]).sum())
        x, z, coefficients = x[keep], z[keep], coefficients[keep]
        peak = max(peak, len(coefficients))
        processed += 1
        if len(coefficients) > max_paulis:
            break
        if not len(coefficients):
            processed = len(gates)
            break
    diagnostics = {
        "epsilon_semantics": "coefficient magnitude cutoff after gate and duplicate merging",
        "transpilation_semantics": "Qiskit u3/CZ optimization, not BlueQubit rotation transpilation",
        "transpilation_level": level, "numerical_atol": numerical_atol,
        "total_gates": len(gates), "propagated_gates": processed,
        "peak_num_paulis": peak, "final_num_paulis": len(coefficients),
        "discarded_l1_sum": discarded_l1, "max_paulis": max_paulis,
        "complete": processed == len(gates) and len(coefficients) <= max_paulis,
    }
    if not diagnostics["complete"]:
        diagnostics["incomplete_reason"] = "Pauli term limit reached"
        return None, diagnostics
    return float(coefficients[x == 0].sum()), diagnostics
