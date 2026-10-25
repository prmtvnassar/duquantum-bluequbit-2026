import sys
from qiskit import QuantumCircuit
lines=open(sys.argv[1]).read().splitlines(); body=lines[3:]
marks=[i for i,l in enumerate(body) if l.startswith(('x ','z '))]
blk=body[:marks[0]]
pairs=[]
for l in blk:
    if l.startswith('cz'):
        a,b=[int(t.split('[')[1].rstrip('];,')) for t in l[3:].split(',')]
        p=tuple(sorted((a,b)))
        if not pairs or pairs[-1]!=p: pairs.append(p)
# collapse consecutive repeats (3 CZ per Haar gate) then greedy layering
layers=[];busy={}
for p in pairs:
    t=max(busy.get(p[0],-1),busy.get(p[1],-1))+1
    while len(layers)<=t: layers.append([])
    layers[t].append(p); busy[p[0]]=busy[p[1]]=t
print('distinct 2q gates',len(pairs),'layers',len(layers))
for i,L in enumerate(layers): print(i,sorted(L))
