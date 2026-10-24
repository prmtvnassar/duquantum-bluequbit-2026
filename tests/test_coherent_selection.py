from copy import deepcopy
import math
import unittest

from otoc.coherent_selection import select_coherent_vector


IDS = [f"Duke_G2_{q}" for q in range(4)]


def vector(device, options, values, ids=IDS):
    return [{"action": {"circuit_id": cid, "device": device, "options": deepcopy(options)},
             "status": "COMPLETED", "estimate": value, "cost_usd": 0.0,
             "job_id": f"{device}-{options}-{cid}"} for cid, value in zip(ids, values)]


def correlation(a, b):
    ac = [value - sum(a) / len(a) for value in a]
    bc = [value - sum(b) / len(b) for value in b]
    return sum(x * y for x, y in zip(ac, bc)) / math.sqrt(sum(x*x for x in ac) * sum(y*y for y in bc))


class CoherentSelectionTests(unittest.TestCase):
    def test_partial_affine_refinement_preserves_the_complete_baseline(self):
        # Each full vector correlates perfectly with truth; pointwise substitution does not.
        truth = [-0.8, -0.2, 0.3, 0.9]
        coarse = [value / 10 for value in truth]
        rows = vector("mps.cpu", {"mps_bond_dimension": 16}, coarse)
        finer = vector("mps.cpu", {"mps_bond_dimension": 32}, truth)
        self.assertAlmostEqual(correlation(truth, coarse), 1.0)
        self.assertLess(correlation(truth, [truth[0], *coarse[1:]]), 0.9)
        result = select_coherent_vector(rows + finer[:1], IDS, "mps.cpu")
        self.assertEqual(result["selected"]["values"], coarse)
        self.assertEqual(result["incomplete_candidates"][0]["missing_ids"], IDS[1:])
        complete = select_coherent_vector(rows + finer, IDS, "mps.cpu")
        self.assertEqual(complete["selected"]["values"], truth)
        self.assertEqual(len(complete["complete_candidates"]), 2)

    def test_global_row_coverage_does_not_imply_a_coherent_vector(self):
        rows = vector("mps.cpu", {"mps_bond_dimension": 16}, [0.1, 0.2])
        rows += vector("mps.cpu", {"mps_bond_dimension": 32}, [0.3, 0.4], IDS[2:])
        result = select_coherent_vector(rows, IDS, "mps.cpu")
        self.assertEqual(result["status"], "INCOMPLETE")
        self.assertIsNone(result["selected"])
        self.assertEqual(len(result["incomplete_candidates"]), 2)

    def test_device_and_every_option_define_separate_cohorts(self):
        rows = vector("mps.cpu", {"mps_bond_dimension": 16}, [0.1, 0.2])
        rows += vector("mps.gpu", {"mps_bond_dimension": 16}, [0.3, 0.4], IDS[2:])
        rows += vector("mps.cpu", {"mps_bond_dimension": 16, "cutoff": 0}, [0.3, 0.4], IDS[2:])
        result = select_coherent_vector(rows, IDS, "mps.cpu")
        self.assertEqual(result["status"], "INCOMPLETE")
        self.assertEqual(len(result["incomplete_candidates"]), 3)

    def test_transpilation_is_isolated_and_primary_constraint_is_respected(self):
        level1 = {"pauli_path_truncation_threshold": 0.001, "pauli_path_circuit_transpilation_level": 1}
        level2 = {"pauli_path_truncation_threshold": 0.0001, "pauli_path_circuit_transpilation_level": 2}
        rows = vector("pauli-path", level1, [0.1, 0.2])
        rows += vector("pauli-path", level2, [0.3, 0.4], IDS[2:])
        self.assertEqual(select_coherent_vector(rows, IDS, "pauli-path")["status"], "INCOMPLETE")
        rows = vector("pauli-path", level1, [0.1, 0.2, 0.3, 0.4])
        rows += vector("pauli-path", level2, [0.2, 0.3, 0.4, 0.5])
        selected = select_coherent_vector(rows, IDS, "pauli-path",
                    primary_options={"pauli_path_circuit_transpilation_level": 1})["selected"]
        self.assertEqual(selected["options"], level1)
        excluded = select_coherent_vector(rows, IDS, "pauli-path",
                    primary_options={"pauli_path_circuit_transpilation_level": 0})
        self.assertEqual(excluded["status"], "INCOMPLETE")
        self.assertEqual(len(excluded["complete_candidates"]), 2)

    def test_complete_exact_wins_and_partial_exact_is_not_spliced(self):
        approximate = vector("mps.cpu", {"mps_bond_dimension": 32}, [0.1, 0.2, 0.3, 0.4])
        exact = vector("cpu", {}, [0.2, 0.3, 0.4, 0.5])
        result = select_coherent_vector(approximate + exact[:2], IDS, "mps.cpu")
        self.assertEqual(result["selected"]["family"], "mps")
        result = select_coherent_vector(approximate + exact, IDS, "mps.cpu")
        self.assertEqual(result["selected"]["family"], "exact")
        self.assertEqual(result["selected"]["values"], [0.2, 0.3, 0.4, 0.5])

    def test_complete_fallback_retains_manifest_order_and_snapshots(self):
        rows = vector("mps.cpu", {"mps_bond_dimension": 32}, [0.1, 0.2, 0.3, 0.4])
        saved = deepcopy(rows)
        result = select_coherent_vector(reversed(rows), list(reversed(IDS)), "pauli-path")
        self.assertEqual(result["selected"]["values"], [0.4, 0.3, 0.2, 0.1])
        self.assertIn("fallback", result["selected"]["selection_reason"])
        self.assertEqual(rows, saved)
        result["selected"]["records"][0]["estimate"] = 0.0
        self.assertEqual(rows, saved)
        self.assertEqual(result["complete_candidates"][0]["records"][0]["estimate"], 0.4)

    def test_nonterminal_unknown_cost_and_nonfinite_rows_do_not_complete_vector(self):
        for changes in ({"status": "RUNNING"}, {"cost_usd": None}, {"estimate": float("nan")},
                        {"estimate": 1.1}, {"cost_usd": float("inf")}):
            with self.subTest(changes=changes):
                rows = vector("mps.cpu", {"mps_bond_dimension": 16}, [0.1, 0.2, 0.3, 0.4])
                rows[-1].update(changes)
                result = select_coherent_vector(rows, IDS, "mps.cpu")
                self.assertEqual(result["status"], "INCOMPLETE")
                self.assertEqual(result["incomplete_candidates"][0]["missing_ids"], [IDS[-1]])

    def test_exact_primary_can_name_a_complete_fallback(self):
        rows = vector("mps.cpu", {"mps_bond_dimension": 16}, [0.1, 0.2, 0.3, 0.4])
        rows += vector("pauli-path", {"pauli_path_truncation_threshold": 0.001}, [0.2, 0.3, 0.4, 0.5])
        result = select_coherent_vector(rows, IDS, "cpu", fallback_device="pauli-path")
        self.assertEqual(result["selected"]["family"], "pps")

    def test_empty_or_duplicate_manifest_is_rejected(self):
        for ids in ([], [IDS[0], IDS[0]]):
            with self.assertRaises(ValueError):
                select_coherent_vector([], ids, "mps.cpu")


if __name__ == "__main__":
    unittest.main()
