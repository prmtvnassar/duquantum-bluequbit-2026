# DuQuantum 2026 — BlueQubit OTOC(2) Challenge

Team repo for BlueQubit's challenge at the Duke Quantum Hackathon (DuQuantum 2026).

- **Hacking window:** Sat Oct 24, 2026 11:30 ET → Sun Oct 25, 2026 11:30 ET (24 h)
- **In person:** check-in 9:00 ET Saturday, Wilkinson Building; closing ceremony ends 4:30 ET Sunday. Online entry is open to anyone.
- **Task:** estimate OTOC(2) expectation values for 4 hidden circuits (~140 numbers: one per qubit per observable),
  run on BlueQubit by circuit ID. 2 sample circuits with exact answers are provided for free experimentation.
- **Teams:** up to 5, one account signs up and submits. AI tools are encouraged.
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

The kit (`README.md`, `samples/`, `samples/samples_exact.csv`, CSV template, `challenge_tools`) is only released at kickoff.

1. Open a Hybrid machine on BlueQubit (or use your own computer), load the kit into `kit/`, set `BLUEQUBIT_API_TOKEN`.
2. Run `claude` in the kit folder and use the organizers' warm-up prompt: on the **sample circuits**, estimate each
   observable with `challenge_tools.otoc2_circuit`, compare exact statevector vs. MPS (several bond dims) vs.
   Pauli-path (several thresholds) against `samples/samples_exact.csv`, write best estimates to
   `samples_estimates.csv`, score with `challenge_tools.score_csv`. Start with the smallest settings.
3. Apply the same workflow to the hidden circuits by ID, spending compute where the samples showed it helps.

Detailed step-by-step plan: [`tasks.md`](tasks.md). Short summary: [`docs/PREP_TASKS.md`](docs/PREP_TASKS.md).

## Rules of the road

- Token lives only in `.env` (gitignored). Never in code, notebooks, or prompts.
- Log every run: circuit, observable, backend, settings, estimate, runtime, cost, job ID.
