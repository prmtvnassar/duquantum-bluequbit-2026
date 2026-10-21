# DuQuantum 2026 — BlueQubit OTOC(2) Challenge

Team repo for BlueQubit's challenge at the Duke Quantum Hackathon (DuQuantum 2026).

- **Hacking window:** Sat Oct 24, 2026 11:30 ET → Sun Oct 25, 2026 11:30 ET (24 h)
- **Task:** estimate OTOC(2) expectation values for 4 hidden circuits (~140 numbers: one per qubit per observable),
  run on BlueQubit by circuit ID. 2 sample circuits with exact answers are provided for free experimentation.
- **Scoring:** per-circuit correlation / signal-to-noise vs. exact values; later circuits weigh more; *ordering matters more than offset*.
- **Submission:** one CSV, header `circuit,qubit,estimate`.
- Challenge page: https://app.bluequbit.io/hackathons/2GMaAenu3iSsIC6Z

## Layout

| Path | Purpose |
|---|---|
| `kit/` | Official challenge kit (drop it here at kickoff — README, `challenge_tools`, template CSV) |
| `src/otoc/` | Our code: OTOC circuit builders, estimators, scorer |
| `scripts/` | CLI runners (sweeps, batch submissions) |
| `notebooks/` | Exploration |
| `results/` | Benchmark logs (`results/logs/*.csv`); raw dumps in `results/raw/` (gitignored) |
| `submissions/` | Final CSVs |
| `docs/` | Practice handout, notes, runbook |

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows  (source .venv/bin/activate on *nix)
pip install -r requirements.txt
copy .env.example .env          # then paste BLUEQUBIT_API_TOKEN
```

Redeem the kickoff coupon at app.bluequbit.io → Account → Billing → Redeem Coupon.

## Kickoff workflow (from the organizers' guide)

1. Load the kit into `kit/`, set `BLUEQUBIT_API_TOKEN`.
2. On the **sample circuits**: estimate each observable with `challenge_tools.otoc2_circuit`, compare
   exact statevector vs. MPS (several bond dims) vs. Pauli-path (several thresholds) against the exact answers,
   write best estimates to `samples_estimates.csv`, score with `challenge_tools.score_csv`.
3. Apply the same workflow to the hidden circuits, spending compute where the samples showed it helps.

## Rules of the road

- Token lives only in `.env` (gitignored). Never in code, notebooks, or prompts.
- Log every run: circuit, observable, backend, settings, estimate, runtime, cost, job ID.
