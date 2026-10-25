"""Does Qiskit optimisation collapse the U X U^dag Z U X U^dag echo? (local, $0)"""
import sys, time
from qiskit import QuantumCircuit, transpile
basis = ['rx','ry','rz','cx','cz','rzz','h','x','y','z','s','sdg','sx','u','u3']
for path in sys.argv[1:]:
    qc = QuantumCircuit.from_qasm_file(path)
    out = [path.split('/')[-1], qc.num_qubits, qc.count_ops().get('cz',0)]
    for lvl in (0,1,2,3):
        t=time.time(); tq = transpile(qc, basis_gates=['rx','ry','rz','cz'], optimization_level=lvl, seed_transpiler=1)
        ops=tq.count_ops(); out.append(f"L{lvl}:2q={ops.get('cz',0)} ({time.time()-t:.1f}s)")
    print(*out)
