import sys, numpy as np
from qiskit import QuantumCircuit
from qiskit.quantum_info import Statevector
path=sys.argv[1]
lines=open(path).read().splitlines()
n=int([l for l in lines if l.startswith('qreg')][0].split('[')[1].split(']')[0])
body=lines[3:]
marks=[i for i,l in enumerate(body) if l.startswith(('x ','z ','y '))]
print('n',n,'marks',[(i,body[i]) for i in marks])
blocks=[]; prev=0
for m in marks+[len(body)]:
    blocks.append(body[prev:m]); prev=m+1
def qc(bl):
    return QuantumCircuit.from_qasm_str('OPENQASM 2.0;\ninclude "qelib1.inc";\nqreg q[%d];\n'%n+'\n'.join(bl))
C=[qc(b) for b in blocks]
print('2q counts',[c.count_ops().get('cz',0) for c in C])
rng=np.random.default_rng(0); v=rng.normal(size=2**n)+1j*rng.normal(size=2**n); v/=np.linalg.norm(v)
s=Statevector(v)
for a in range(len(C)):
    for b in range(len(C)):
        if a<b:
            f=abs(np.vdot(v,s.evolve(C[a]).evolve(C[b]).data))
            if f>0.99: print(f'block{b} = inverse(block{a})  overlap {f:.6f}')
            g=abs(np.vdot(s.evolve(C[a]).data,s.evolve(C[b]).data))
            if g>0.99: print(f'block{b} = block{a}  overlap {g:.6f}')
