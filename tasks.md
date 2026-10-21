# TASKS — BlueQubit OTOC(2) Challenge (DuQuantum 2026)

**Deadline math**
- Kickoff: **Sat Oct 24, 2026, 11:30 ET** (check-in 9:00 ET at the Wilkinson Building if in person)
- Finish: **Sun Oct 25, 2026, 11:30 ET**
- Aim to submit a full CSV by **10:30 ET Sunday** (1 hour buffer).

**How to use this file**
- Do the steps in order. Tick each box `[x]` when done.
- Every step says *what to do*, *how to tell it worked*, and *what to do if it didn't*.
- Work in the repo folder `D:\BluQubit` unless a step says otherwise.
- Don't commit anything you don't understand. Use the git recap on your Desktop.

**Known facts vs. unknowns** (source: the saved page `D:\BluQubit\Duke Quantum Hackathon.html`)
- *Known:* OTOC(2) estimates, 4 hidden circuits, about 140 numbers total (one per qubit per observable), output CSV `circuit,qubit,estimate` with one row per observable, scored per circuit by correlation with exact values (signal-to-noise), later circuits weigh more, ordering matters more than offset.
- *Known:* the kit has `README.md`, `samples/` (two sample circuits), `samples/samples_exact.csv` (exact answers for the samples), a CSV template, and `challenge_tools` with `otoc2_circuit` (builds the echo circuits) and `score_csv` (scores a CSV). The full scoring rule ships with the kit.
- *Known:* the kit is **not** available before kickoff. The samples, the template and `challenge_tools` only arrive at 11:30 ET Saturday. So Phase 2 uses our own stand-ins until then.
- *Known:* compute is sold as BlueQubit credits. The coupon code is "coming soon" (not announced yet). Redeem at Account → Billing → Redeem Coupon. Larger Hybrid machines bill your credits.
- *Known:* AI tools are encouraged. Graded circuits can only be run through BlueQubit. Teams of up to 5, one account submits.
- *Unknown until kickoff:* qubit counts, the graded circuit details, the coupon amount, and the exact scoring code. Everything that depends on these is marked **[KICKOFF]**.

---

## PHASE 0 — Admin (today, about 1 hour)

### 0.1 Register
- [ ] Open https://app.bluequbit.io/hackathons/2GMaAenu3iSsIC6Z
- [ ] Click sign up / join. Use the same Google account you'll use on the day.
- [ ] **Verify:** the page shows you as registered or lets you open the challenge.
- [ ] **If it fails:** try a different browser window, then message the organizers via the DuQuantum site.

### 0.2 Decide who submits
- [ ] Pick **one person** as the submitter. Only that account submits.
- [ ] Write the name here: `Submitter: ____________`
- [ ] The submitter's BlueQubit account gets the coupon and token.

### 0.3 BlueQubit account + token
- [ ] Log into https://app.bluequbit.io
- [ ] Find your API token (Account / settings page). Copy it.
- [ ] Open `D:\BluQubit\.env` (create it from `.env.example` if it doesn't exist):
  ```
  BLUEQUBIT_API_TOKEN=paste-your-token-here
  ```
- [ ] Save the file.
- [ ] **Verify:** `D:\BluQubit\.env` exists and `git status` does **not** list it. If it does, stop and fix `.gitignore` first.
- [ ] **Never** paste the token into chat, a notebook, a commit message, or a screenshot.

### 0.4 Python environment check
- [ ] Open PowerShell in `D:\BluQubit`
- [ ] Run:
  ```
  .\.venv\Scripts\python -c "import bluequbit, qiskit; print('ok')"
  ```
- [ ] **Verify:** it prints `ok`.
- [ ] **If it fails:** `.\.venv\Scripts\pip install -r requirements.txt` then retry.

### 0.5 Smoke test
- [ ] Run:
  ```
  .\.venv\Scripts\python scripts\smoke_test.py
  ```
- [ ] **Verify:** you see a statevector printed, then two expectation values (Pauli-path and MPS) that are close to each other.
- [ ] **If you get an auth error:** the token is wrong or has a space at the end. Re-copy it.
- [ ] Note the runtime and any credit usage in `results\logs\` (create a file `setup.md` there).

### 0.6 Hybrid notebook warm-up
- [ ] On BlueQubit, open a **Hybrid mode** machine once. Just open it, run a cell, close it.
- [ ] **Verify:** the notebook runs a cell and shows output.

### 0.7 Team access
- [ ] Each teammate follows the "How to join the repo" steps from the chat.
- [ ] Each teammate runs `scripts\smoke_test.py` on their own machine.
- [ ] Check off names here as they finish:
  - [ ] Teammate 1: ________
  - [ ] Teammate 2: ________
  - [ ] Teammate 3: ________
  - [ ] Teammate 4: ________
  - [ ] Teammate 5: ________

---

## PHASE 1 — Learn OTOCs (Day 1 before the hackathon, about 4 hours)

Goal: be able to draw the OTOC circuit on paper and say why it's hard to simulate.

### 1.1 Read the BlueQubit OTOC tutorial
- [ ] Open https://app.bluequbit.io/tutorial/otoc-tutorial
- [ ] Read it from top to bottom. Don't skip the code cells.
- [ ] Also read the challenge's own FAQ item 7 (it names the same tutorial and the Quantum Echoes paper title: *Observation of constructive interference at the edge of quantum ergodicity*, Nature 2025).
- [ ] Write 3 sentences in `docs\notes.md`: what an OTOC measures, what "scrambling" means, why it's hard classically.
- [ ] **Verify:** you can say those 3 sentences without looking.

### 1.2 Read the Google paper (skim first)
- [ ] Open https://doi.org/10.1038/s41586-025-09526-6
- [ ] Read the abstract and the figure captions only.
- [ ] Find the sentence that defines OTOC. Copy it into `docs\notes.md`.

### 1.3 Read the Google blog post
- [ ] Open https://research.google/blog/a-verifiable-quantum-advantage/
- [ ] Note in `docs\notes.md`: one sentence on what "verifiable" means here.

### 1.4 Draw the echo circuit by hand
- [ ] On paper, draw this structure:
  - Start: `|0...0⟩`
  - Apply `U` (scrambling circuit)
  - Apply butterfly `B` on one qubit
  - Apply `U†`
  - Apply measurement operator `M` on another qubit
  - Apply `U`, then `B`, then `U†` again (the second echo)
- [ ] Label where the "time" part is.
- [ ] **Verify:** you can explain in one sentence why `U` appears forwards and backwards.
- [ ] Take a photo and save it to `docs\figures\echo_circuit.jpg` (create the folder).

### 1.5 Light cones
- [ ] Read the light-cone section of the tutorial or paper.
- [ ] Draw a 1D chain of 8 qubits with 3 layers of 2-qubit gates. Shade the qubits that a single gate can influence.
- [ ] **Verify:** you can say why a shallow circuit only needs a small region simulated.

### 1.6 Check your understanding
- [ ] Answer these in `docs\notes.md`, in your own words:
  1. What does one "estimate per qubit per observable" mean?
  2. Why would Pauli-path simulation be cheaper for some circuits than statevector?
  3. What does an MPS bond dimension control?
  4. Which measurement basis do you need for Z? For X? For Y?
- [ ] **Verify:** if you can't answer one, reread that part before moving on.

---

## PHASE 2 — Our local pipeline (Day 1–2, about 6 hours)

Goal: a tested local tool that computes exact answers for small circuits. It's our ground truth for checking BlueQubit results.

### 2.1 Random circuit generator
- [ ] Create `src\otoc\circuits.py`
- [ ] Write a function `random_brickwork(n_qubits, depth, seed)` that returns a Qiskit circuit made of random single-qubit rotations and CNOTs/CZs in alternating layers.
- [ ] **Verify:** for `n_qubits=3, depth=2, seed=1`, calling it twice gives the same circuit (same seed = same output).
- [ ] Add a test in `tests\test_circuits.py` (create `tests` folder) that checks this.
- [ ] Run `.\.venv\Scripts\pytest` and check it passes.

### 2.2 Exact statevector reference
- [ ] Create `src\otoc\exact.py`
- [ ] Write `exact_expectation(circuit, pauli_string)` using `qiskit.quantum_info.Statevector` and `Pauli`.
- [ ] **Verify with a known answer:** the state `|+⟩` has `⟨X⟩ = 1`, `⟨Z⟩ = 0`. Write a test for both.
- [ ] **Verify endianness:** for a state `|10⟩` (qubit 0 = 0, qubit 1 = 1), check which Pauli string gives `⟨Z⟩ = -1` on qubit 1. Write this down in `docs\notes.md`. Qiskit's labels read right-to-left, so this matters for the CSV.

### 2.3 Pauli-sum helper
- [ ] Write `combine(terms)` that sums `coefficient × expectation` over a list of `(pauli_string, coeff)` pairs.
- [ ] Test it against the Hamiltonian `2X − Z` on `|+⟩`. Expected result: `2`.

### 2.4 BlueQubit wrappers with logging
- [ ] Create `src\otoc\bq_methods.py`
- [ ] Write `run_mps(circuit, pauli_sum, bond_dim)` that calls `client.run(..., device="mps.cpu", options={"mps_bond_dimension": bond_dim}, pauli_sum=...)`.
- [ ] Write `run_pauli_path(circuit, pauli_sum, threshold)` that calls `device="pauli-path"` with `pauli_path_truncation_threshold`.
- [ ] Each function appends one row to `results\logs\runs.csv`: `timestamp, method, setting, circuit_id, estimate, runtime_s, job_id`.
- [ ] **Verify:** run both on the 3-qubit example from the smoke test. Both should match the exact answer from 2.2 to about 3 decimal places.

### 2.5 Ordering check
- [ ] Take a 3-qubit random circuit. Compute `⟨ZII⟩`, `⟨IZI⟩`, `⟨IIZ⟩` exactly.
- [ ] Run the same via BlueQubit.
- [ ] **Verify:** the values match in the same order. If they're reversed, fix the qubit mapping in one place (`bq_methods.py`) and note it in `docs\notes.md`.

### 2.6 Commit this phase
- [ ] `git status` → check only the files you expect
- [ ] `git checkout -b phase2-pipeline`
- [ ] `git add src\otoc tests scripts` then `git diff --staged` and check it
- [ ] `git commit -m "Add exact reference, Pauli sum helper and BlueQubit wrappers"`
- [ ] `git push -u origin phase2-pipeline`
- [ ] Merge to `main` on GitHub (or ask someone to review).

---

## PHASE 3 — Scoring and benchmarking (Day 2, about 4 hours)

Goal: know which method to trust, and how much it costs.

### 3.1 Placeholder scorer
- [ ] Create `src\otoc\score.py`
- [ ] Write `pearson(pred, truth)` and `spearman(pred, truth)`. Use `scipy.stats`.
- [ ] Write `score_circuit(pred, truth)` that returns Pearson.
- [ ] Test with `pred = truth` (score should be 1.0) and `pred = -truth` (score should be -1.0).
- [ ] **[KICKOFF]** Replace this with the official `challenge_tools.score_csv` once you have the kit. Don't use this one for the real submission.

### 3.2 Build a benchmark set
- [ ] Generate 6 random circuits: 12, 14, 16, 18, 20 qubits, depth 4 and 8.
- [ ] Compute exact answers for each (statevector works up to about 20 qubits).
- [ ] Save them to `results\benchmark\` as `.csv` files.

### 3.3 Sweep MPS bond dimension
- [ ] For each circuit, run MPS with χ = 16, 32, 64, 128.
- [ ] Log every run to `runs.csv`.
- [ ] Make a table: circuit, χ, Pearson, runtime, credits used.
- [ ] **Verify:** the table has 6 × 4 = 24 rows.

### 3.4 Sweep Pauli-path threshold
- [ ] For each circuit, run Pauli-path with threshold = 1e-1, 1e-2, 1e-3.
- [ ] Log every run.
- [ ] Add these rows to the same table.

### 3.5 Find the crossover
- [ ] Plot score vs. runtime for both methods (`matplotlib`, save to `results\plots\`).
- [ ] Write 3 sentences in `docs\notes.md`: which method wins at which depth.
- [ ] **Verify:** you can point to a row in the table that supports each sentence.

### 3.6 Try blending
- [ ] Average MPS and Pauli-path estimates for the same observable.
- [ ] Check if Pearson goes up.
- [ ] Record the result. If it doesn't help, drop it.

### 3.7 Async batching
- [ ] Practice `client.run(..., asynchronous=True)` to submit 5 jobs at once.
- [ ] Use `client.wait(job_id)` to collect them.
- [ ] Practice `client.cancel(job_id)` on one job.
- [ ] **Verify:** all 5 finish (or you cancel one on purpose) and you know the code for each.

### 3.8 Commit benchmark results
- [ ] Commit the CSVs and plots (not raw dumps, which `.gitignore` already excludes).
- [ ] Push to a branch `phase3-benchmarks`.

---

## PHASE 4 — Rehearse (Day 3, about 3 hours)

### 4.1 Mock hidden-circuit run
- [ ] One teammate writes a random 30-qubit circuit and saves it to a file. They don't tell anyone what's in it.
- [ ] Another teammate has 90 minutes to produce `submissions\mock.csv` with `circuit,qubit,estimate`.
- [ ] Time it. Write the time in `docs\notes.md`.
- [ ] **Verify:** the CSV has one row per qubit per observable, no blanks.

### 4.2 Write the runbook
- [ ] Create `docs\RUNBOOK.md` with these sections:
  - **Roles:** who runs jobs, who scores, who submits, who watches credits.
  - **Credit budget:** how many credits per circuit. Spend more on later circuits (they count more).
  - **Escalation:** what to do if a job fails 3 times.
  - **Submission:** exact steps, who clicks submit, and the cutoff time.
- [ ] Each teammate reads it and signs off in the file.

### 4.3 Sleep plan
- [ ] Split 24 hours into 3 shifts of 8 hours, or 2 shifts of 12 hours.
- [ ] Write the names and times in `docs\RUNBOOK.md`.

---

## KICKOFF DAY — Sat Oct 24, 11:30 ET

Do these in order. Don't skip ahead.

### K.1 First 15 minutes
- [ ] Log into BlueQubit with the submitter account.
- [ ] Get the coupon code (announced at kickoff; the page says "coming soon"). Redeem it at **Account → Billing → Redeem Coupon**. Write down the credit amount: `________`.
- [ ] Download the challenge kit into `D:\BluQubit\kit\`.
- [ ] Read the kit README start to finish. Write any surprises in `docs\notes.md`.

### K.2 Copy the official rules
- [ ] Copy the exact scoring formula into `docs\SCORING.md`.
- [ ] Copy the exact submission format into `docs\SUBMISSION.md`.
- [ ] **Verify:** a teammate reads both and agrees.

### K.3 Warm-up on the samples (about 30 minutes, the organizers' own steps)
- [ ] Open a **Hybrid mode** machine in BlueQubit (or use your own computer). Hybrid machines bill credits.
- [ ] Load the kit there and set `BLUEQUBIT_API_TOKEN`.
- [ ] Run `claude` in the kit folder and paste the organizers' prompt (it's in the saved page, under "Warm up on the samples"). It tells the agent to read `README.md`, work on `samples/`, use `challenge_tools.otoc2_circuit`, compare methods, write `samples_estimates.csv`, and score it with `challenge_tools.score_csv`.
- [ ] **Verify:** `challenge_tools.score_csv` runs on the sample output without errors.

### K.4 Sample circuits (about 2 hours)
- [ ] Put the sample circuits in `samples/` and their exact answers in `samples/samples_exact.csv`. Don't edit these files.
- [ ] For each observable, estimate OTOC(2) with `challenge_tools.otoc2_circuit`. Run:
  - Statevector (exact)
  - MPS at a few bond dimensions (start small: 16, 64, 256)
  - Pauli-path at a few thresholds (start at 1e-1, then 1e-2)
- [ ] Compare each method to `samples_exact.csv`. Pick the best method per circuit and note why.
- [ ] Write the best estimates to `samples_estimates.csv` (`circuit,qubit,estimate`).
- [ ] Score it with `challenge_tools.score_csv`.
- [ ] **Verify:** the score is recorded in `results\logs\runs.csv`.
- [ ] Start small and only go bigger where it helps. The organizers say so too.

### K.5 Baseline for all hidden circuits (within 4 hours)
- [ ] Point the same workflow at the 4 hidden circuits **by ID** (they can only be run through BlueQubit).
- [ ] Run the cheapest reasonable method on all 4 hidden circuits.
- [ ] Fill in every row of `submissions\submission.csv`. No blanks.
- [ ] Validate the file: 4 circuits, correct number of rows, header `circuit,qubit,estimate`.
- [ ] Submit it.
- [ ] **Verify:** the platform accepts it and shows a score.

### K.6 Improve the heavy circuits
- [ ] Look at the scores per circuit. Circuits that score lowest and carry the most weight get the most compute.
- [ ] Re-run those with a bigger χ or lower threshold.
- [ ] Log every run.
- [ ] Resubmit only if the score goes up.

### K.7 Protect the deadline
- [ ] **By 9:00 ET Sunday:** freeze the best submission. Save a copy as `submissions\final_candidate.csv`.
- [ ] **By 10:30 ET Sunday:** final submission is in. Stop starting new runs.
- [ ] **By 11:00 ET Sunday:** write the method note (5 sentences: what you did, why, limits).
- [ ] **11:30 ET Sunday:** deadline. Don't rely on the last 5 minutes.

---

## ALWAYS

- [ ] Log every run in `results\logs\runs.csv`: circuit, method, setting, estimate, runtime, credits, job ID.
- [ ] Check your credit balance before each big batch of runs.
- [ ] Commit at the end of each phase. Don't wait until the end.
- [ ] Never commit `.env`, tokens, or raw job dumps.
- [ ] If you're stuck for more than 30 minutes, write down the problem in `docs\notes.md` and ask the team.
