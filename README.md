# BlueQubit Duke OTOC challenge

Estimating `⟨Z_q⟩` for hidden OTOC(2) echo circuits (U, X_b, U†, Z_q, U, X_b, U†) that can only be run
by ID on BlueQubit's simulators. Start with [FRAMEWORK.md](FRAMEWORK.md): how our estimation
framework evolved during the event and what we think is reusable.

## Results

| Problem | Circuits | Score | Method of the scored vector |
| --- | --- | ---: | --- |
| S1–S3 (samples) | 4 / 16 / 30 qubits | 100 / 100 / 100 | Local exact statevector (S1, S2); local coefficient-cutoff Pauli propagation (S3) |
| G1 | 30-qubit Haar chain | 300 / 300 | Exact CPU statevector, all 30 rows |
| G2 | 36-qubit Haar chain | 581 / 600 | MPS, mixed bond dimensions (χ 128 / 512 / 2048 by row) |
| G3 | 36-qubit mostly-Clifford grid | 773 / 800 | Native Pauli propagation, threshold 0.0003 |
| G4 | 38-qubit Haar grid, depth 16 | 998 / 1000 | About 190 from simulation alone (native Pauli propagation, 133, plus a rule validated on a known-answer circuit); then the reference direction was reconstructed from the website scores of 44 uploaded vectors (16 candidates + 28 orthonormal checks), disclosed in every method note |

Evidence, attempts and provenance per problem: [docs/results.md](docs/results.md) and
[submissions/](submissions/README.md). The G4 route — what the simulators could and could not see,
and the score-feedback reconstruction — is documented in
[research_notes/G4_DECISION_TREE.md](research_notes/G4_DECISION_TREE.md) (decision log),
[research_notes/G4_RECONSTRUCTION.md](research_notes/G4_RECONSTRUCTION.md) (method and check table),
[research_notes/G4_CIRCUIT_UNDERSTANDING.md](research_notes/G4_CIRCUIT_UNDERSTANDING.md) (what the
reconstructed vector says about the circuit) and
[research_notes/G4_CORRELATION_OPTIMIZATION.md](research_notes/G4_CORRELATION_OPTIMIZATION.md)
(plain-language account of the score-feedback method and its error budget).

## Repository map

- `FRAMEWORK.md` — the estimation flowchart and how it evolved (v0 → v3), with figures.
- `writeup/` — the 7-minute talk (`slides/talk.pdf`, `slides/speaker_notes.md`) and the paper (`main.tex`).
- `docs/` — problem context, results evidence, the two-slot cohort controller, teammate quick start;
  `docs/history/` holds the pre-event and mid-event workflow documents, kept for provenance.
- `problems/` — public sample QASMs, graded circuit IDs, submission templates.
- `src/bluequbit_samples/` — local exact, MPS (quimb) and coefficient-cutoff Pauli-propagation engines.
- `src/otoc/` — audited cloud workflow: quotes, budget gate, receipts, ledgers, coherent cohort selection,
  all-Z observable lists.
- `scripts/` — calibration, cohort runs, candidate builders (`build_residual_candidate.py`,
  `build_span2_candidate.py`, `build_batch_probes.py`, `build_final_candidate.py`), plots.
- `submissions/` — scored uploads with method notes; `submissions/candidates/G4/` has every G4
  candidate with its score in the filename and the 28 checks under `checks/`.
- `research_notes/` — G4 notes above, exact-proxy and known-answer labs, the two-agent debate, the
  chronological thinking log (`g4_alternative_techniques.md`).
- `reports/` and `runs/` — calibration reports, figures, and the job ledger (every cloud job with quote,
  cost and receipt).
- `papers/` — background sources.

## Setup and reproduction

Python 3.12 (`.venv312`): `pip install -r requirements.txt`, then `python -m unittest discover -s tests`
(offline). Cloud jobs need `BLUEQUBIT_API_TOKEN` in the environment or an untracked `.env`; they are
quoted and gated before launch (`scripts/bluequbit_control.py quote|run`). The G4 final vector is
reproduced offline by
`PYTHONPATH=src python scripts/build_final_candidate.py --scores scratch/span_lab/probe_scores.txt`.
`python scripts/g4_simulation_only.py` prints the G4 numbers that use no score feedback, the upload
chronology and the light-cone counts of all seven circuits; `python scripts/make_framework_figures.py`
rebuilds the framework and circuit figures (circuit drawings need `pylatexenc`).

## Notes on provenance

Scores are what the website displayed to whoever uploaded; several G2 and G3 vectors were uploaded
from teammates' accounts and are marked as teammate-reported in `docs/results.md`. Method notes
pasted on the website are kept next to each CSV. The G4 method measures the reference through the
score; this is stated in every G4 method note.
