"""Light cone of butterfly q0 after 16 layers of the S3-style 4-sublayer brickwork on RxC grids."""
def layers(R,C):
    idx=lambda r,c:r*C+c
    H0=[(idx(r,c),idx(r,c+1)) for r in range(R) for c in range(0,C-1,2)]
    H1=[(idx(r,c),idx(r,c+1)) for r in range(R) for c in range(1,C-1,2)]
    V0=[(idx(r,c),idx(r+1,c)) for r in range(0,R-1,2) for c in range(C)]
    V1=[(idx(r,c),idx(r+1,c)) for r in range(1,R-1,2) for c in range(C)]
    return [H0,V0,H1,V1]
def cone(R,C,depth=16,start=0):
    L=layers(R,C); S={start}
    for t in range(depth):
        for a,b in L[t%4]:
            if a in S or b in S: S|={a,b}
    return S
for R,C in [(5,6),(2,19),(19,2),(6,7),(7,6),(4,10),(3,13),(6,6)]:
    n=R*C; S=cone(R,C)
    print(f'{R}x{C} n={n}: inside={len(S)} outside={sorted(set(range(n))-S)[:40]}')
