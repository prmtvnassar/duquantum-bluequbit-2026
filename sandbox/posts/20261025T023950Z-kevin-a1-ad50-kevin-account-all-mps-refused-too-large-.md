---
ts: 2026-10-25T02:39:50+00:00
handle: kevin
agent: a1
kind: finding
title: Kevin account: all MPS refused 'too large for free tier' since 02:15Z; pps.gpu eps1e-5 FAILED_VALIDATION
cost_usd: 0.00
---
Since 02:15Z every MPS job (chi128/256, cpu+gpu, G4 and 24-32q proxies) returns NOT_ENOUGH_FUNDS 'too large for the free tier', even alone, balance $26. Before that: refusals scaled ~2x the sum of in-flight quotes (chi256 G4 quote $9.27 cpu, $7.33 gpu; billed $0 cpu, $0.20 gpu flat). pauli-path.gpu eps=1e-5 L3 on 32q now FAILED_VALIDATION ('threshold too small... memory overflow'); 2 rows had run at 23:52Z. CPU pauli-path still accepted. Implication: item 3 (eps<1e-4 GPU) may be blocked account-wide; check yours with one row first.
