# BlueQubit Duke OTOC challenge

*Our team account is **Kevin Zhu*** on [BlueQubit Challenge Leaderboards](https://app.bluequbit.io/hackathons/2GMaAenu3iSsIC6Z?page=1&tab=leaderboard&viewUniversity=true)

Estimating `⟨Z_q⟩` for hidden OTOC(2) echo circuits (U, X_b, U†, Z_q, U, X_b, U†) that can only be run
by ID on BlueQubit's simulators: exact statevector (up to 34 qubits), MPS (bond dimension χ) and Pauli-path
propagation (PPS, threshold ε). Start with [FRAMEWORK.md](FRAMEWORK.md): how we chose between MPS and PPS,
how the estimation workflow evolved during the event, and what we think is reusable.

## Results

| Problem | Circuits | Score | Method of the scored vector |
| --- | --- | ---: | --- |
| S1–S3 (samples) | 4 / 16 / 30 qubits | 100 / 100 / 100 | Local exact statevector (S1, S2); local coefficient-cutoff Pauli propagation (S3) |
| G1 | 30-qubit Haar chain | 300 / 300 | Exact CPU statevector, all 30 rows |
| G2 | 36-qubit Haar chain | 581 / 600 | MPS, mixed bond dimensions (χ 128 / 512 / 2048 by row) |
| G3 | 36-qubit mostly-Clifford grid | 773 / 800 | Native PPS, transpilation level 1, ε 0.0003 |
| G4 | 38-qubit Haar grid, depth 16 | 284 / 1000 | PPS baseline (ε 1e-4, level 3: 133) refined with MPS χ256 rows (165), measured-null MPS directions removed (199), refined vectors mixed into an ensemble (284; its dominant ingredient was fitted to earlier whole-vector scores, stated in the method note) |

Evidence and provenance per problem: [docs/results.md](docs/results.md) and [submissions/](submissions/README.md).
The G4 route (why MPS alone scored 0, why PPS became the baseline, how MPS refined it) is in
[research_notes/G4_PPS_MPS.md](research_notes/G4_PPS_MPS.md).

## Repository map

- `FRAMEWORK.md`: the estimation flowchart and how it evolved (v0 → v3), with figures.
- `writeup/main.tex`: the paper (method details and limitations).
- `docs/`: problem context, results evidence, the two-slot cohort controller, teammate quick start.
  `docs/history/` holds the pre-event and mid-event workflow documents.
- `problems/`: public sample QASMs, graded circuit IDs, submission templates.
- `src/bluequbit_samples/`: local exact, MPS (quimb) and coefficient-cutoff Pauli-propagation engines.
- `src/otoc/`: audited cloud workflow (quotes, budget gate, receipts, ledgers, coherent cohort selection,
  all-Z observable lists).
- `scripts/`: calibration, cohort runs, the G4 residual builder, summaries and figures.
- `labs/`: $0 known-answer testbeds: exact proxies of the G4 generator (`proxy_lab`), MPS feature tests on
  the samples (`sample_lab`), a local PPS threshold ladder (`pps_ladder_lab`), and the 32-qubit known-answer
  circuit PG4c (`pg4c`).
- `research_notes/`: the G4 note above, lab reports, MPS/PPS stopping criteria, GPU precision notes.
- `submissions/`: scored uploads with method notes; `submissions/candidates/G4/` lists every scored G4 vector.
- `reports/` and `runs/`: calibration reports, figures, and the job ledger (every cloud job with quote, cost
  and receipt).
- `papers/`: background sources.

## Setup and reproduction

Python 3.12 (`.venv312`): `pip install -r requirements.txt`, then `python -m unittest discover -s tests`
(offline). Cloud jobs need `BLUEQUBIT_API_TOKEN` in the environment or an untracked `.env`; they are
quoted and gated before launch (`scripts/bluequbit_control.py quote|run`). Offline G4 checks:
`python scripts/build_residual_candidate.py` rebuilds the 199 and 195 vectors;
`python scripts/g4_pps_mps_summary.py` prints the G4 score ladder, the known-answer (PG4c) scores of PPS, MPS
and the post-processing rule, and the light-cone counts of all seven circuits;
`python scripts/make_framework_figures.py` rebuilds the framework and circuit figures (circuit drawings need
`pylatexenc`).

## Notes on provenance

Scores are what the website displayed to whoever uploaded; several G2, G3 and G4 vectors were uploaded from
teammates' accounts and are marked as teammate-reported in `docs/results.md`. Method notes pasted on the
website are kept next to each CSV.
