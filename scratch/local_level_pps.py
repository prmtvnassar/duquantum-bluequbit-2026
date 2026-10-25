"""Local evidence: Qiskit level-L collapse + coefficient PPS vs exact refs ($0)."""
import sys, time, csv, types, json
import numpy as np
sys.path.insert(0,'src')
from bluequbit_samples.coefficient_pps import propagate
from bluequbit_samples.analysis import correlation_score
prob, n = sys.argv[1], int(sys.argv[2]); levels=[int(x) for x in sys.argv[3].split(',')]; eps=[float(x) for x in sys.argv[4].split(',')]
ref={r['circuit_id']:float(r['value']) for r in csv.DictReader(open(f'submissions/{prob}/attempt-01.csv'))}
d={'S2':'02_sample_S2','S3':'03_sample_S3'}[prob]
out={}
for L in levels:
    for e in eps:
        vals=[];t=time.time()
        for q in range(n):
            s=types.SimpleNamespace(qasm_text=open(f'problems/{d}/circuits/Duke_{prob}_{q}.qasm').read(),num_qubits=n,qubit=q)
            r=propagate(s,e,5_000_000,level=L)
            vals.append(float(r[0]) if r[0] is not None else float("nan"))
        y=[ref[f'Duke_{prob}_{q}'] for q in range(n)]
        rho,score,_=correlation_score(vals,y)
        out[f'L{L}_eps{e}']=vals
        print(f'{prob} L{L} eps={e}: rho={rho} score={score} maxerr={np.max(np.abs(np.array(vals)-y)):.3f} t={time.time()-t:.0f}s', flush=True)
json.dump(out,open(f'scratch/local_level_pps_{prob}.json','w'))
