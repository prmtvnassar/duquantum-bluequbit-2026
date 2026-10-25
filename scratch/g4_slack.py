"""G4 light-cone slack from the verified H0,V0,H1,V1 layer cycle on 6x6 + (36,37) under (30,31)."""
R, C = 6, 6
idx = lambda r, c: r * C + c if r < R else 36 + c   # row 6 has cols 0,1 -> q36,q37
def pairs(kind):
    out = []
    if kind == "H0":
        for r in range(R): out += [(idx(r, c), idx(r, c + 1)) for c in range(0, C - 1, 2)]
        out.append((36, 37))
    if kind == "H1":
        for r in range(R): out += [(idx(r, c), idx(r, c + 1)) for c in range(1, C - 1, 2)]
    if kind == "V0":
        for r in range(0, R - 1, 2): out += [(idx(r, c), idx(r + 1, c)) for c in range(C)]
    if kind == "V1":
        for r in range(1, R - 1, 2): out += [(idx(r, c), idx(r + 1, c)) for c in range(C)]
        out += [(30, 36), (31, 37)]   # row5 -> partial row6
    return out
cycle = ["H0", "V0", "H1", "V1"]
first = {0: 0}; S = {0}
for t in range(16):
    new = set()
    for a, b in pairs(cycle[t % 4]):
        if (a in S) != (b in S): new.add(a if b in S else b)
    for q in new: first.setdefault(q, t + 1)
    S |= new
slack = {q: 16 - first.get(q, 99) for q in range(38)}
print("gates per cycle:", {k: len(pairs(k)) for k in cycle}, "total/16 layers:", sum(len(pairs(cycle[t % 4])) for t in range(16)))
for s in sorted(set(slack.values()), reverse=True):
    print(f"slack {s:>2}: {[q for q in range(38) if slack[q]==s]}")
