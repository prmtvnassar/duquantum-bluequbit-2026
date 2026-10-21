# Pre-hackathon prep — summary

The detailed, step-by-step plan lives in [`../tasks.md`](../tasks.md). This file is the short version.

> `docs/duquantum_bluequbit_48h_practice.tex` was written from older public info
> ("~10 circuits, ~50 observables"). The **live challenge page** is authoritative:
> **OTOC(2)** estimation, **4 hidden circuits, ~140 numbers**, inspired by Google's *Quantum Echoes*.
> Skip the generic IBM exercises and Shor/Grover; the OTOC material is what matters.

## Facts from the challenge page
- Window: Sat Oct 24, 2026 11:30 ET → Sun Oct 25, 11:30 ET (24 h). Aim to submit by 10:30 ET Sunday.
- Submission: one CSV, header `circuit,qubit,estimate`, one row per observable.
- Scoring: per circuit, correlation with exact values (signal-to-noise). Later circuits weigh more.
  Ordering matters more than a constant offset. Full rule ships with the kit.
- Kit (arrives at kickoff only): `README.md`, `samples/` (2 circuits), `samples/samples_exact.csv`,
  CSV template, `challenge_tools` (`otoc2_circuit`, `score_csv`).
- Credits: coupon code not yet announced. Redeem at Account → Billing → Redeem Coupon. Hybrid machines bill credits.
- Teams ≤ 5, one account submits. AI tools encouraged. Graded circuits run only via BlueQubit, by ID.

## Phases
0. **Admin:** register, pick submitter, token in `.env`, `scripts/smoke_test.py`, open a Hybrid notebook once, onboard teammates.
1. **Learn OTOCs:** BlueQubit OTOC tutorial, Google paper (*Observation of constructive interference at the edge of quantum ergodicity*), light cones.
2. **Local pipeline (stand-ins, since the kit isn't out):** circuit generator, exact statevector reference, BlueQubit MPS / Pauli-path wrappers with run logging, qubit-ordering check.
3. **Benchmark:** sweep MPS bond dimension and Pauli-path threshold on 12–20 qubit circuits with known answers; plot score vs cost; find the crossover; try blending; practice async jobs.
4. **Rehearse:** timed mock run, runbook with roles and credit budget, sleep plan.
5. **Kickoff:** redeem coupon, load kit, run the organizers' warm-up prompt on the samples, baseline CSV for all 4 circuits early, spend remaining credits on the heaviest-weighted circuits.
