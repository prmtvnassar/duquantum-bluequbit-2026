"""LOO evaluation of geometry priors on depth-16 proxy instances; G4 prediction vectors."""
import json, glob, itertools, numpy as np
CYCLE = ["H0", "V0", "H1", "V1"]
def layout(R, C, extra):           # extra: dict q->(r,c) for the partial row (G4: 36->(6,0), 37->(6,1))
    pos = {r*C+c: (r, c) for r in range(R) for c in range(C)}; pos.update(extra); return pos
def pairs(kind, pos):
    inv = {v: k for k, v in pos.items()}; out = []
    for q, (r, c) in pos.items():
        if kind == "H0" and c % 2 == 0 and (r, c+1) in inv: out.append((q, inv[(r, c+1)]))
        if kind == "H1" and c % 2 == 1 and (r, c+1) in inv: out.append((q, inv[(r, c+1)]))
        if kind == "V0" and r % 2 == 0 and (r+1, c) in inv: out.append((q, inv[(r+1, c)]))
        if kind == "V1" and r % 2 == 1 and (r+1, c) in inv: out.append((q, inv[(r+1, c)]))
    return out
def slack(pos, depth, butterfly=0):
    S = {butterfly}; first = {}
    for k, t in enumerate(reversed(range(depth)), start=1):      # X_0 is conjugated by the last layer first
        new = set()
        for a, b in pairs(CYCLE[t % 4], pos):
            if (a in S) != (b in S): new.add(b if a in S else a)
        for q in new: first.setdefault(q, k)
        S |= new
    return {q: (depth - first[q] if q in first else -1) for q in pos}
G4 = layout(6, 6, {36: (6, 0), 37: (6, 1)}); G4S = slack(G4, 16)
ref = {0:16,1:12,2:10,3:8,4:6,5:4,6:13,7:12,8:10,9:8,10:6,11:4,12:11,13:11,14:10,15:8,16:6,17:4,18:9,19:9,20:9,21:8,22:6,23:4,24:7,25:7,26:7,27:7,28:6,29:4,30:5,31:5,32:5,33:5,34:5,35:4,36:3,37:3}
print("G4 slack map matches proxy-lab table:", G4S == ref)
inst = []
for f in sorted(glob.glob("scratch/proxy_lab/data/exact_*_d16_s*.json")):
    d = json.load(open(f)); pos = layout(d["rows"], d["cols"], {}); s = slack(pos, d["depth"])
    inst.append({"name": f.split("exact_")[1][:-5], "v": np.array(d["exact"]), "slack": np.array([s[q] for q in range(d["num_qubits"])]),
                 "dist": np.array(d["manhattan"], float)})
def score(x, y):
    x, y = np.asarray(x, float), np.asarray(y, float)
    if x.std() < 1e-12: return 0.0
    return 1000 * np.corrcoef(x, y)[0, 1] ** 2
def table_from(others):
    pool = {}
    for o in others:
        for s, v in zip(o["slack"], o["v"]): pool.setdefault(int(s), []).append(v)
    return {s: float(np.mean(v)) for s, v in pool.items()}
def apply_table(tab, sl):
    keys = sorted(tab); return np.array([tab[int(s)] if int(s) in tab else tab[min(keys, key=lambda k: abs(k-int(s)))] for s in sl])
z = lambda a: (a - a.mean()) / (a.std() + 1e-12)
priors = {
  "table_signed_LOO": lambda i, oth: apply_table(table_from(oth), i["slack"]),
  "-slack": lambda i, oth: -i["slack"].astype(float),
  "dist": lambda i, oth: i["dist"], "dist^2": lambda i, oth: i["dist"]**2,
  "-exp(-slack/2)": lambda i, oth: -np.exp(-i["slack"]/2.0), "-exp(-slack/3)": lambda i, oth: -np.exp(-i["slack"]/3.0),
  "-exp(-slack/4)": lambda i, oth: -np.exp(-i["slack"]/4.0), "-exp(-slack/6)": lambda i, oth: -np.exp(-i["slack"]/6.0),
  "blend z(table)+z(-slack)": lambda i, oth: z(apply_table(table_from(oth), i["slack"])) + z(-i["slack"].astype(float)),
  "blend z(table)+z(dist^2)": lambda i, oth: z(apply_table(table_from(oth), i["slack"])) + z(i["dist"]**2),
  "blend z(-exp(-s/3))+z(dist^2)": lambda i, oth: z(-np.exp(-i["slack"]/3.0)) + z(i["dist"]**2),
}
print(f"{'prior':32s} mean  min  max | per instance ({[i['name'] for i in inst]})")
for name, fn in priors.items():
    sc = [score(fn(i, [o for o in inst if o is not i]), i["v"]) for i in inst]
    print(f"{name:32s} {np.mean(sc):5.0f} {min(sc):4.0f} {max(sc):4.0f} | {' '.join(f'{s:4.0f}' for s in sc)}")
# G4 prediction vectors
g4 = {"slack": np.array([G4S[q] for q in range(38)]), "dist": np.array([abs(G4[q][0])+abs(G4[q][1]) for q in range(38)], float)}
tab = table_from(inst); print("pooled d16 table:", {k: round(v, 4) for k, v in sorted(tab.items())})
out = {name: fn(g4, inst).tolist() for name, fn in priors.items()}
out["slack"] = g4["slack"].tolist(); out["dist"] = g4["dist"].tolist()
json.dump(out, open("scratch/g4_prior_vectors.json", "w"), indent=1)
print("G4 table_signed vector:", [round(x, 3) for x in out["table_signed_LOO"]])
