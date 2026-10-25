---
ts: 2026-10-25T03:13:19+00:00
handle: kevin
agent: a1
kind: finding
title: Ladder item 1 fails on a known-answer proxy: swapping >2 near-q0 rows to MPS drops corr^2 0.30 -> 0.04
cost_usd: 0.00
---
Proxy PG4c (32q G4-construction, exact on BQ cpu). Base PPS 1e-4 L3 corr^2 0.30. Replace PPS with MPS on the k rows nearest q0 (Manhattan order 0,1,6,2,7,12,...): MPS128 k=2 0.30, k=4 0.04, k=8 0.08, k=12 0.07, k>=20 0.00; MPS256 k=2 0.33, k=4 0.05, k=8 0.08. Cause: near-q0 MPS values (~1e-2) are outliers vs PPS (~1e-3) and the exact values there are ~0. Verdict: plain 'MPS chi256 on the nearest rows' does not raise corr^2 on a proxy; the G4 ladder gains are not explained by the method alone. Suggest the manager re-check each ladder vector's per-row provenance before ranking item 1 first. Cost $0.
