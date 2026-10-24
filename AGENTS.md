# Repository Guidelines

## Project Structure

- `src/otoc/` contains the installable Python package; shared BlueQubit client setup currently lives in `config.py`.
- `tutorials/study/` holds the offline learning notebooks and simulator helpers. Notebook source content is in `tutorials/build/nb*.py`; `tutorials/build/nbbuild.py` generates the notebooks. `tutorials/originals/` stores reference tutorials.
- `scripts/` contains command-line utilities such as `smoke_test.py`. `kit/` is reserved for the kickoff challenge kit; `submissions/` for CSVs; `results/logs/` for run records; `docs/` for preparation notes and runbooks.

## Setup and Development Commands

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
jupyter lab tutorials\study
```

Regenerate study notebooks with `python tutorials/build/nbbuild.py [nb00_linear_algebra ...]`. Run `python tutorials/build/verify.py [nb00_linear_algebra ...]` to execute notebooks and their embedded checks. Run `python scripts/smoke_test.py` only when you intend to submit BlueQubit jobs and have configured credentials.

## Style and Naming

Use four spaces for Python indentation, `snake_case` for functions and variables, and descriptive names for circuits, observables, and simulator settings. The package targets Python 3.10 or newer. Keep notebook explanations short and pair exercises with checks. Edit `tutorials/build/nb*.py` when changing generated study notebooks. No formatter or linter is configured.

## Testing

There is no standalone `tests/` suite yet. The study exercises use checks in `tutorials/study/checks.py`; run them through `tutorials/build/verify.py`. The smoke test exercises the live SDK and is not a substitute for offline checks. For simulator changes, compare small cases against exact statevector results and record simulator settings with estimates.

## Commits and Pull Requests

Recent commits use concise, imperative subjects, such as `Add offline study notebooks` and `Make smoke test free-tier safe`. Keep each commit focused. A pull request should explain the change, list validation performed, and call out any SDK jobs, credit use, or submission-format changes. Include generated CSVs or notebook outputs only when they are part of the intended result.

## Security and Challenge Data

Provide `BLUEQUBIT_API_TOKEN` through the environment or a local, gitignored `.env` file. Never commit tokens, raw job dumps, or private challenge data. Treat the kickoff kit's README, scorer, and CSV template as authoritative over local mock-challenge assumptions.
