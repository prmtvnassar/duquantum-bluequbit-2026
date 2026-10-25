---
ts: 2026-10-25T02:39:52+00:00
handle: kevin
agent: a1
kind: finding
title: DEAD: PPS + sign-flipped MPS blend. Proxy said 0.30->0.66, G4 upload scored 94
cost_usd: 0.00
---
Proxy PG4c: 32q, 5x6 grid + 2-qubit row, Haar, 16 layers, butterfly q0; same construction as G4 (reproduces G4's 3024 CZ); exact on BlueQubit cpu. corr^2 vs exact: PPS 1e-4 L3 0.30; 1e-3 L3 0.22; 1e-3 L0/L1 all-zero; GPU 1e-4 L1 zero; MPS128 corr -0.49 with exact (tracks distance +0.46); z(PPS)+z(-MPS128) 0.66. G4 v2 = same blend (18 real chi256 rows, rest filled from distance fit) scored 94 vs 133 base. Verdict: the proxy's falling distance trend does not transfer; G4's truth likely rises with distance from q0 (G4 PPS corr +0.32 with distance; PG4b proxy also +). Do not use -distance priors on G4.
