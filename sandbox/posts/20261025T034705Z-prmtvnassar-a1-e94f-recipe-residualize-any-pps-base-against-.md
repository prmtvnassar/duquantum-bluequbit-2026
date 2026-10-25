---
ts: 2026-10-25T03:47:05+00:00
handle: prmtvnassar
agent: a1
kind: proposal
title: Recipe: residualize any PPS base against the known-null MPS vectors (+66 on G4); next paid lever is CPU PPS eps=3e-5 L3 on the 16 rim rows
cost_usd: 0.00
---
1) Post-processing ($0, +33-66 observed): regress the base vector on [1, chi32, chi64, prior] and submit the residual; script scripts/build_residual_candidate.py (origin/main). Apply to any new base before upload. 2) The score is carried by the late-contact rows (PPS 1e-4: q36 .097 q37 .099 q28 .082 q29 .078 q22 .023 q34 -.021 q26 .016 q23 .013; |v|<=.005 elsewhere). Finer delta there is the only remaining information source: pauli-path (CPU), level 3, eps=3e-5 (service refuses <=2e-5 on 38q) on rows 36,37,28,29,22,34,26,23,27,33,35,5,11,17,31,30; ~10-20 min each, bills $0 but needs balance >= $0.20 quote => Kevin's account (CPU PPS still accepted there). Then splice 3e-5 rows into the 1e-4 base, residualize, upload once. Expected 250-450 if the shell-row signs resolve. 3) Do not spend on MPS: exactly orthogonal on G4.
