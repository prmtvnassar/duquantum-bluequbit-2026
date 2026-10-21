# Pre-hackathon task list (≈80 h until kickoff, Sat Oct 24 11:30 ET)

> **Heads-up:** `docs/duquantum_bluequbit_48h_practice.tex` was written from older public info
> ("~10 circuits, ~50 observables"). The **live challenge page** says: **OTOC(2)** estimation,
> **4 hidden circuits, ~140 numbers**, inspired by Google's *Quantum Echoes*. Prioritize the
> OTOC-specific items below; use the handout's generic Pauli/IBM exercises only to fill gaps.

## Phase 0 — Admin (today, ~30 min)
- [ ] Register the team on the hackathon page (one account submits for the whole team, ≤5 people).
- [ ] Create a BlueQubit account, copy the API token into `.env` (`BLUEQUBIT_API_TOKEN=...`).
- [ ] `python scripts/smoke_test.py` — confirms SDK, token, statevector, MPS and Pauli-path all work.
- [ ] Invite teammates to the GitHub repo; confirm everyone can clone over SSH and run the smoke test.
- [ ] Open a **Hybrid mode** notebook on BlueQubit once so it isn't new on the day.

## Phase 1 — Understand OTOCs (Day 1, ~4 h)
- [ ] Work through the **BlueQubit OTOC tutorial** end to end: https://app.bluequbit.io/tutorial/otoc-tutorial
      (OTOC(1) vs OTOC(2) echo circuits, scrambling, exact vs MPS vs Pauli-path).
- [ ] Read Google *Quantum Echoes* (Nature 2025, doi:10.1038/s41586-025-09526-6) + the Google Research blog post.
      Focus: the definition of OTOC^(2), circuit structure U · B · U† · M · U · B · U† (butterfly B, measurement M),
      and *why* OTOC(2) has a large interference term that's hard for classical methods.
- [ ] Be able to write on paper: C^(2) = ⟨ψ| (B(t) M)^4 |ψ⟩–style correlator, where B(t) = U† B U. Know what
      "one estimate per qubit per observable" probably means (butterfly or measurement qubit is swept).
- [ ] Understand light cones: a local Pauli under U† ... U only touches qubits within the causal cone →
      this is what makes Pauli-path / light-cone truncation work on large circuits.

## Phase 2 — Build our own OTOC pipeline (Day 1–2, ~6 h)
Build it so it's ready to swap in `challenge_tools.otoc2_circuit` at kickoff.
- [ ] `src/otoc/circuits.py`: random brickwork / iSWAP-like circuit generator U(n, depth, seed), and an
      `otoc2_circuit(U, butterfly_q, measure_q)` builder (our guess at the kit's function).
- [ ] `src/otoc/exact.py`: local exact OTOC via statevector (qiskit-aer) for n ≤ ~20 — the ground truth.
- [ ] `src/otoc/bq_methods.py`: wrappers for BlueQubit `mps.cpu` (bond dim χ) and `pauli-path` (threshold τ),
      each returning (estimate, runtime, job_id) and appending a row to `results/logs/runs.csv`.
- [ ] Verify qubit/Pauli-string ordering on a 3-qubit case (Qiskit's `Pauli("XYZ")` puts Z on q0. Check whether BlueQubit's `pauli_sum` uses the same order or the reverse).

## Phase 3 — Scorer + benchmarking (Day 2, ~4 h)
- [ ] `src/otoc/score.py`: placeholder metric = Pearson correlation / SNR per circuit, weighted sum.
      Replace with the **exact** formula from the kit (`challenge_tools.score_csv`) at kickoff.
      Note: offset doesn't matter, ordering does → also track Spearman rank correlation.
- [ ] Sweep on 12–20-qubit random circuits with known exact answers:
      MPS χ ∈ {16, 32, 64, 128, 256}, Pauli-path τ ∈ {1e-1, 1e-2, 1e-3, 1e-4}.
      Record estimate, |error|, correlation, runtime, cost. Plot score vs. cost.
- [ ] Learn how depth changes things: MPS degrades with entanglement (deep), Pauli-path degrades with
      operator spreading. Find the crossover.
- [ ] Try a cheap ensemble: average/blend MPS + Pauli-path estimates and see if correlation improves.
- [ ] Use `asynchronous=True` + `bq.wait()` to batch many jobs in parallel; practice `bq.cancel()`.

## Phase 4 — Rehearse (Day 3, ~3 h)
- [ ] Mock run: a teammate generates a "hidden" 30–50-qubit circuit; you have 2 h to produce a CSV
      (`circuit,qubit,estimate`) with every row filled and scored on the small sample.
- [ ] Write `docs/RUNBOOK.md`: first-hour checklist, roles, credit budget per circuit
      (harder/later circuits weigh more → spend more there), who submits, submission deadline buffer (≥1 h).
- [ ] Sleep plan for the 24 h window (two shifts if team ≥ 3).

## Kickoff day (Sat 11:30 ET)
1. Redeem coupon (Account → Billing → Redeem Coupon). Drop kit into `kit/`. Read kit README fully.
2. Copy the official scoring rule into `docs/`; swap our scorer for `challenge_tools.score_csv`.
3. Sample circuits: statevector vs MPS(χ sweep) vs Pauli-path(τ sweep) → `samples_estimates.csv` → score.
4. Submit a **baseline CSV for all 4 hidden circuits early**, then improve the heavy-weight ones.
5. Log every job. Keep ≥1 h buffer before 11:30 ET Sunday.
