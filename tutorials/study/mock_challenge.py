"""mock_challenge.py: an offline dress rehearsal of the BlueQubit OTOC(2) challenge.

Mirrors what the challenge page says:
  * a few HIDDEN circuits you can only run "by ID", choosing method and compute;
  * two SAMPLE circuits you can inspect, with exact answers;
  * one estimate per probe qubit: OTOC(2) = <Z_q> after U, X_b, U^dag, Z_q, U, X_b, U^dag;
  * submit one CSV `circuit,qubit,estimate`; each circuit scored by correlation (SNR), later ones weigh more.

Things we had to make up (the real rules come with the kit at kickoff):
  * sizes, depths and circuit families of the hidden circuits;
  * the weights (1, 2, 3, 4) and how per-circuit scores combine (weighted mean of `bits`);
  * the budget, counted here in simulator seconds instead of credits;
  * a statevector limit of 12 qubits, to force you onto approximate methods as on the real day.

Honor system: the hidden circuits live inside this object. Don't peek, it's practice.
"""
from __future__ import annotations

import csv
import json
import time
from pathlib import Path

import numpy as np

from offline_sim import LocalBQ
from otoc_tools import (brickwork, echo_circuit, exact_otoc2, near_clifford_circuit, read_csv, score,
                        simulate_expz, to_qiskit, z_label)

HERE = Path(__file__).resolve().parent


def otoc2_circuit(U, b, q):
    """The OTOC(2) echo for circuit U, butterfly X_b, probe Z_q (like challenge_tools.otoc2_circuit)."""
    return echo_circuit(U, b, q, order=2)


class MockChallenge:
    WEIGHTS = {"H1": 1, "H2": 2, "H3": 3, "H4": 4}

    def __init__(self, seed: int = 2026, budget_s: float = 1500.0, sv_limit: int = 12, verbose: bool = True):
        self.seed, self.budget_s, self.spent_s = seed, budget_s, 0.0
        self.bq = LocalBQ(sv_qubit_limit=sv_limit)
        self.verbose = verbose
        rng = np.random.default_rng(seed)
        # (id, n, depth, family, b).  Families: 'brick' = Haar brickwork, 'nc' = near-Clifford.
        spec_samples = [("S1", 10, 8, "brick", 0), ("S2", 12, 10, "nc", 0)]
        spec_hidden = [("H1", 14, 10, "nc", 0), ("H2", 16, 6, "brick", 0),
                       ("H3", 16, 7, "brick", 8), ("H4", 18, 12, "brick", 0)]
        self._circ, self._gates, self._meta = {}, {}, {}
        for cid, n, d, fam, b in spec_samples + spec_hidden:
            if fam == "brick":
                g = brickwork(n, d, rng)
                self._gates[cid] = g
                self._circ[cid] = to_qiskit(n, g)
            else:
                self._circ[cid] = near_clifford_circuit(n, d, rng, p=0.35)
            self._meta[cid] = {"n": n, "b": b, "depth": d, "family": fam}
        self.samples = {cid: self._circ[cid] for cid, *_ in spec_samples}
        self.hidden_ids = [cid for cid, *_ in spec_hidden]
        self.sample_ids = list(self.samples)
        self._truth_path = HERE / f"mock_truth_seed{seed}.json"
        self._truth = None

    # ---------------------------------------------------------------- what participants see
    def info(self, cid):
        """Public facts about a circuit. Samples reveal everything; hidden ones only n and b."""
        m = self._meta[cid]
        return dict(m) if cid in self.samples else {"n": m["n"], "b": m["b"]}

    def sample_exact(self, cid):
        """Exact OTOC(2) for every probe qubit of a SAMPLE circuit: {q: value}."""
        if cid not in self.samples:
            raise PermissionError("exact answers are only given for sample circuits")
        return {q: v for (c, q), v in self.truth().items() if c == cid}

    def write_sample_exact_csv(self, path):
        with open(path, "w", newline="") as f:
            w = csv.writer(f); w.writerow(("circuit", "qubit", "exact"))
            for cid in self.sample_ids:
                for q, v in sorted(self.sample_exact(cid).items()):
                    w.writerow((cid, q, repr(float(v))))

    def rows(self, ids=None):
        """Every (circuit, qubit) row the submission needs."""
        ids = ids or self.hidden_ids
        return [(cid, q) for cid in ids for q in range(self._meta[cid]["n"])]

    def run(self, cid, q, device="mps.cpu", **options):
        """Estimate OTOC(2) at probe q of circuit cid. Counts simulator time against the budget."""
        if self.spent_s >= self.budget_s:
            raise RuntimeError(f"budget exhausted ({self.spent_s:.0f}s of {self.budget_s:.0f}s)")
        qc = otoc2_circuit(self._circ[cid], self._meta[cid]["b"], q)
        t = time.perf_counter()
        r = self.bq.run(qc, device=device, pauli_sum=[(z_label(q, qc.num_qubits), 1.0)], options=options or None)
        self.spent_s += time.perf_counter() - t
        return float(r.expectation_value)

    def budget_left(self):
        return max(0.0, self.budget_s - self.spent_s)

    # ---------------------------------------------------------------- scoring
    def truth(self):
        if self._truth is None:
            if self._truth_path.exists():
                raw = json.loads(self._truth_path.read_text())
                self._truth = {(c, int(q)): v for c, q, v in raw}
            else:
                self._truth = {}
                for cid in self.sample_ids + self.hidden_ids:
                    t = time.time(); m = self._meta[cid]
                    for q in range(m["n"]):
                        if cid in self._gates:
                            self._truth[cid, q] = exact_otoc2(m["n"], self._gates[cid], m["b"], q)
                        else:
                            self._truth[cid, q] = simulate_expz(otoc2_circuit(self._circ[cid], m["b"], q), q)
                    if self.verbose:
                        print(f"  computed exact answers for {cid} ({m['n']} qubits) in {time.time() - t:.0f}s")
                self._truth_path.write_text(json.dumps([[c, q, v] for (c, q), v in self._truth.items()]))
        return self._truth

    def score_csv(self, path, ids=None):
        """Per-circuit score (r, snr, bits) and a weighted total. Raises on a malformed CSV."""
        ids = ids or self.hidden_ids
        sub = read_csv(path, "estimate")
        need = set(self.rows(ids))
        missing, extra = need - sub.keys(), sub.keys() - need
        if missing or extra:
            raise ValueError(f"{len(missing)} rows missing (e.g. {sorted(missing)[:3]}), {len(extra)} unexpected")
        tru = self.truth()
        per = {}
        for cid in ids:
            qs = range(self._meta[cid]["n"])
            per[cid] = score([sub[cid, q] for q in qs], [tru[cid, q] for q in qs])
        w = {cid: self.WEIGHTS.get(cid, 1) for cid in ids}
        total = sum(w[c] * per[c]["bits"] for c in ids) / sum(w.values())
        return {"per_circuit": per, "weighted_bits": total}


def write_submission(path, estimates):
    """estimates: {(circuit, qubit): value} -> CSV with header circuit,qubit,estimate."""
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="") as f:
        w = csv.writer(f); w.writerow(("circuit", "qubit", "estimate"))
        for (c, q), v in sorted(estimates.items()):
            w.writerow((c, int(q), repr(float(v))))
