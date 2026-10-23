from nbbuild import code, ex, md

NAME = "05_mock_challenge"

CELLS = [
md("""
# 05 · Mock challenge: a full offline dress rehearsal

This notebook runs the hackathon workflow end to end on fake hidden circuits, so kickoff morning
feels familiar. It follows the organizers' warm-up prompt step by step:

> *Work on the two sample circuits (their exact answers are given). For every observable, estimate
> OTOC(2) using `otoc2_circuit` to build the echoes. Try exact statevector, MPS at a few bond
> dimensions, and Pauli paths at a few truncation thresholds. Compare every method with the exact
> answers [...]. Write your best estimates to a CSV (`circuit,qubit,estimate`) and score it. [...]
> Then point the same workflow at the hidden circuits by ID, and spend your compute where the samples
> showed it pays off.*

**What's real and what's invented.** Real: the task, the echo, the CSV format, scoring by
correlation/SNR per circuit with later circuits weighted more. Invented for practice: circuit sizes
(laptop-sized so we can score you), the weights 1-2-3-4, the budget (simulator seconds instead of
credits), and a 12-qubit statevector limit so you *must* use approximate methods, as on the day.

The first scoring computes the exact answers once (~30 s) and caches them.
"""),
code("""
import time
import numpy as np
import matplotlib.pyplot as plt
from mock_challenge import MockChallenge, otoc2_circuit, write_submission
from otoc_tools import score, echo_schematic, draw, read_csv
import checks

mc = MockChallenge(seed=2026, budget_s=600)
print("samples:", {c: mc.info(c) for c in mc.sample_ids})
print("hidden :", {c: mc.info(c) for c in mc.hidden_ids})
print(f"budget : {mc.budget_left():.0f} simulator-seconds")
mc.truth();   # computes and caches exact answers the first time (used for sample answers and scoring)
"""),
md("""
## Step 0: know the interface

- `mc.samples[cid]` is a sample circuit $U$ you may inspect; `mc.sample_exact(cid)` gives `{q: exact OTOC(2)}`.
- `mc.run(cid, q, device, **options)` estimates OTOC(2) at probe $q$ of **any** circuit by ID
  (`device` = `"cpu"`, `"mps.cpu"`, `"pauli-path"`), and charges the time to your budget.
- `mc.rows()` lists every `(circuit, qubit)` row a hidden-circuit submission needs.
- `write_submission(path, {(cid, q): value})` writes the CSV; `mc.score_csv(path)` scores it.
"""),
ex("how many numbers do you owe?",
   """
   Set `n_rows` to the number of rows the hidden-circuit submission needs, and `probe_qubits` to a
   dict `{cid: number of probe qubits}` for the hidden circuits. (The real challenge: ~140 numbers over 4 circuits.)
   """,
   """
   n_rows = None          # YOUR CODE
   probe_qubits = None
   """,
   """
   n_rows = len(mc.rows())
   probe_qubits = {cid: mc.info(cid)["n"] for cid in mc.hidden_ids}
   """,
   """
   checks.equal("n_rows", n_rows, 64)
   checks.equal("probe_qubits", probe_qubits, {"H1": 14, "H2": 16, "H3": 16, "H4": 18})
   """),
code("""
# The echo for sample S1 with butterfly b=0 and probe q=5: this is what otoc2_circuit builds.
draw(echo_schematic(n=mc.info("S1")["n"], b=0, q=5, order=2), scale=0.6);
"""),
md("""
## Step 1: a cheap baseline for **everything**, first

Rule from the runbook: *produce a complete submission early, then improve.* A cheap MPS run
($\\chi = 4$) costs seconds and already captures the trivial structure (qubits ahead of the
butterfly's front read exactly 1).
"""),
ex("baseline submission",
   """
   Write `estimate_all(mc, ids, device, **opts)` returning `{(cid, q): estimate}` for every probe of
   every circuit in `ids`. Use it to make `baseline` for the hidden circuits with `mps.cpu`, $\\chi=4$,
   write it to `submissions/mock_baseline.csv`, and store `mc.score_csv(...)` in `baseline_score`.
   """,
   """
   def estimate_all(mc, ids, device, **opts):
       raise NotImplementedError   # YOUR CODE

   baseline = None
   baseline_score = None
   """,
   """
   def estimate_all(mc, ids, device, **opts):
       return {(cid, q): mc.run(cid, q, device, **opts) for cid in ids for q in range(mc.info(cid)["n"])}

   baseline = estimate_all(mc, mc.hidden_ids, "mps.cpu", mps_bond_dimension=4)
   write_submission("submissions/mock_baseline.csv", baseline)
   baseline_score = mc.score_csv("submissions/mock_baseline.csv")
   """,
   """
   checks.truthy("baseline covers all 64 rows", baseline is not None and len(baseline) == 64, todo=baseline is None)
   checks.truthy("baseline scores above zero", baseline_score is not None and baseline_score["weighted_bits"] > 0,
                 todo=baseline_score is None)
   if baseline_score:
       for c, s in baseline_score["per_circuit"].items(): print(f"  {c}: r={s['r']:+.3f}  bits={s['bits']:.2f}")
       print(f"  weighted bits: {baseline_score['weighted_bits']:.2f}   budget left: {mc.budget_left():.0f}s")
   """),
md("""
## Step 2: calibrate every method on the samples

The samples come with exact answers, so this is where you learn **which method works on which kind
of circuit**, and what it costs. S1 is a Haar-random brickwork; S2 is near-Clifford. Sample runs
are charged too, so be deliberate.
"""),
ex("calibration table",
   """
   For each sample circuit and each setting in `settings`, estimate all its probes, score them against
   `mc.sample_exact(cid)`, and append a dict `{"cid", "device", "opts", "r", "bits", "seconds"}` to `calib`.
   Then set `best` to a dict `{cid: (device, opts)}` with the highest-`bits` setting per sample.
   """,
   """
   settings = [("mps.cpu", {"mps_bond_dimension": 4}), ("mps.cpu", {"mps_bond_dimension": 16}),
               ("mps.cpu", {"mps_bond_dimension": 32}),
               ("pauli-path", {"pauli_path_truncation_threshold": 3e-2}),
               ("pauli-path", {"pauli_path_truncation_threshold": 1e-2})]
   calib = []      # YOUR CODE fills this
   best = None
   """,
   """
   settings = [("mps.cpu", {"mps_bond_dimension": 4}), ("mps.cpu", {"mps_bond_dimension": 16}),
               ("mps.cpu", {"mps_bond_dimension": 32}),
               ("pauli-path", {"pauli_path_truncation_threshold": 3e-2}),
               ("pauli-path", {"pauli_path_truncation_threshold": 1e-2})]
   calib = []
   for cid in mc.sample_ids:
       exact = mc.sample_exact(cid)
       for dev, opts in settings:
           t = time.perf_counter()
           est = [mc.run(cid, q, dev, **opts) for q in sorted(exact)]
           sc = score(est, [exact[q] for q in sorted(exact)])
           calib.append({"cid": cid, "device": dev, "opts": opts, "r": sc["r"], "bits": sc["bits"],
                         "seconds": time.perf_counter() - t})
   best = {cid: max(((r["device"], r["opts"], r["bits"]) for r in calib if r["cid"] == cid), key=lambda x: x[2])[:2]
           for cid in mc.sample_ids}
   """,
   """
   checks.truthy("calib has 10 rows", len(calib) == 10, todo=len(calib) == 0)
   checks.truthy("best S1 is an MPS setting (Pauli paths fail on random circuits)",
                 best is not None and best["S1"][0] == "mps.cpu", todo=best is None)
   for r in calib:
       print(f"  {r['cid']}  {r['device']:10s} {str(r['opts']):42s} r={r['r']:+.3f}  bits={r['bits']:5.2f}  {r['seconds']:.1f}s")
   """),
md("""
**Read your table like a scientist.** On the random-brickwork sample, Pauli paths return ≈0 for
every scrambled probe and lose the signal, exactly the failure the OTOC tutorial showed. On the
near-Clifford sample, both work. MPS gets better with $\\chi$ and costs more.

On hidden circuits you have **no exact answers**. Your only evidence there is **self-consistency**:
does the estimate move when you double $\\chi$? If it doesn't, you're probably converged.
"""),
ex("where is the uncertainty?",
   """
   For each hidden circuit, estimate every probe with $\\chi = 8$ and with $\\chi = 16$, and store the
   largest absolute change across its probes in `instability[cid]`. Keep the $\\chi=16$ estimates in
   `est16` (a dict `{(cid, q): value}`) so you don't pay for them twice.
   Big instability = not converged = where your remaining budget should go.
   """,
   """
   instability = None   # YOUR CODE: {cid: max |est_chi16 - est_chi8|}
   est16 = None
   """,
   """
   est8 = estimate_all(mc, mc.hidden_ids, "mps.cpu", mps_bond_dimension=8)
   est16 = estimate_all(mc, mc.hidden_ids, "mps.cpu", mps_bond_dimension=16)
   instability = {cid: max(abs(est16[cid, q] - est8[cid, q]) for q in range(mc.info(cid)["n"])) for cid in mc.hidden_ids}
   """,
   """
   checks.truthy("instability for all 4 hidden circuits", instability is not None and set(instability) == set(mc.hidden_ids),
                 todo=instability is None)
   if instability:
       for c, v in instability.items(): print(f"  {c}: max change chi 8 -> 16 = {v:.3f}")
       checks.truthy("the deep / middle-butterfly circuits are the least converged",
                     max(instability, key=instability.get) in ("H3", "H4"))
       print(f"  budget left: {mc.budget_left():.0f}s")
   """),
md("""
## Step 3: spend the budget where it pays, then submit

Strategy: start from `est16`. For each circuit that isn't converged, double $\\chi$ until the
estimates stop moving (or the budget runs low). Spend on **later circuits first**: they carry more
weight. Then write the final CSV and score it.
"""),
ex("final submission",
   """
   Starting from `est16`, refine each hidden circuit in the order H4, H3, H2, H1: keep doubling
   $\\chi$ (32, 64, ...) while the max change versus the previous $\\chi$ exceeds `tol = 0.02`.

   **Budget discipline:** a job that starts still runs to the end, but `mc.run` refuses new jobs once
   you're out, even mid-circuit. So before each doubling, *predict* its cost: MPS time grows like
   $\\chi^2$ to $\\chi^3$, so assume the next sweep costs about **6×** the last sweep of that circuit, and
   only start it if that fits in `mc.budget_left()` minus a 60 s reserve.

   Store the final dict in `final`, write it to `submissions/mock_final.csv`, and store the score in
   `final_score`. It should beat the baseline.
   """,
   """
   tol, reserve = 0.02, 60
   final = None        # YOUR CODE
   final_score = None
   """,
   """
   tol, reserve = 0.02, 60
   final = dict(est16)
   for cid in ["H4", "H3", "H2", "H1"]:
       n_c, chi, last_cost = mc.info(cid)["n"], 16, 5.0
       prev = {q: final[cid, q] for q in range(n_c)}
       while 6 * last_cost < mc.budget_left() - reserve:
           chi *= 2
           t0 = mc.spent_s
           cur = {q: mc.run(cid, q, "mps.cpu", mps_bond_dimension=chi) for q in range(n_c)}
           last_cost = mc.spent_s - t0
           change = max(abs(cur[q] - prev[q]) for q in range(n_c))
           final.update({(cid, q): v for q, v in cur.items()})
           print(f"  {cid}: chi={chi:>3}  max change {change:.3f}  cost {last_cost:5.1f}s  budget left {mc.budget_left():.0f}s")
           if change < tol:
               break
           prev = cur
       else:
           print(f"  {cid}: stop at chi={chi}; the next doubling (~{6 * last_cost:.0f}s) doesn't fit the budget")
   write_submission("submissions/mock_final.csv", final)
   final_score = mc.score_csv("submissions/mock_final.csv")
   """,
   """
   checks.truthy("final covers all 64 rows", final is not None and len(final) == 64, todo=final is None)
   if final_score and baseline_score:
       for c, s in final_score["per_circuit"].items(): print(f"  {c}: r={s['r']:+.3f}  bits={s['bits']:.2f}")
       print(f"  weighted bits: baseline {baseline_score['weighted_bits']:.2f} -> final {final_score['weighted_bits']:.2f}")
       checks.truthy("final beats baseline", final_score["weighted_bits"] > baseline_score["weighted_bits"])
   else:
       checks.truthy("final beats baseline", False, todo=True)
   """),
md("""
## Step 4: look at what you got right and wrong

Only possible in the mock (on the day you never see hidden answers): plot estimate vs truth per circuit.
"""),
code("""
import os
if os.path.exists("submissions/mock_final.csv"):
    sub, tru = read_csv("submissions/mock_final.csv", "estimate"), mc.truth()
    fig, axes = plt.subplots(1, 4, figsize=(15, 3.4))
    for ax, cid in zip(axes, mc.hidden_ids):
        qs = range(mc.info(cid)["n"])
        ax.plot(qs, [tru[cid, q] for q in qs], "ko-", ms=4, label="exact")
        ax.plot(qs, [sub[cid, q] for q in qs], "s--", mfc="none", label="your estimate")
        ax.set(title=f"{cid} (b={mc.info(cid)['b']})", xlabel="probe qubit q", ylim=(-1.1, 1.1))
    axes[0].legend(); plt.tight_layout(); plt.show()
else:
    print("finish the final-submission exercise first")
"""),
md("""
## Reflection: what transfers to the real day

1. **Baseline everything first** (minutes), then improve. A missing row is worse than a rough one.
2. **Calibrate on the samples**: they tell you which method fits which circuit family. Pauli paths
   were useless on random brickwork, fine on near-Clifford; MPS needed more $\\chi$ for deep circuits
   and for a butterfly in the middle of the chain (two fronts).
3. **On hidden circuits, use self-consistency** ($\\chi$ vs $2\\chi$, $\\delta$ vs $\\delta/3$) to find
   where you're not converged, and spend there, **heaviest-weighted circuits first**.
4. **Budget like the platform bills:** doubling $\\chi$ costs ~4-8×. Predict before you launch; a sweep
   that runs dry mid-circuit wastes everything it spent.
5. **Cross-check methods when one stalls.** H1 is near-Clifford: Pauli paths converge there even where
   MPS wobbles. Agreement between two *different* methods is strong evidence.
6. **Correlation rewards ordering:** the exact-1 qubits ahead of the front and the ≈0 scrambled ones are
   easy points; the circuit-specific band just behind the front is where scores are won or lost.
7. **Watch the real scoring rule at kickoff.** If it centres values per circuit (the `families` option in
   `otoc_tools.score`), the easy 1s stop helping and only the in-between band counts.
8. **Real budget = credits:** `cpu`, `mps.cpu`, `pauli-path` were free in the tutorial; GPUs cost.
   BQ 201: `mps.gpu` only wins above $\\chi\\approx128$.

✏️ **Write your method note** (the kind you'd submit), 5 sentences: what you ran, why, how you
checked convergence, what you'd do with 10× the budget, one limitation.

*Your note here.*
"""),
]
