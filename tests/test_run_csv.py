from __future__ import annotations

import csv
from pathlib import Path
import tempfile
import unittest

from otoc.run_csv import RunCsvError, prepare_run_csv, record_estimate, select_estimate, upsert_job, validate_run_csv


class RunCsvTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.runs = self.root / "runs"
        self.template = self.root / "template.csv"
        with self.template.open("w", encoding="utf-8", newline="") as output:
            csv.writer(output).writerows([
                ["circuit", "qubit", "estimate"], ["C", "01", ""], ["C", "00", ""],
            ])
        prepare_run_csv(self.template, "hidden", self.runs)

    def job(self, status: str = "planned") -> dict:
        return {
            "dataset": "hidden", "circuit": "C", "method": "mps", "device": "mps.cpu",
            "kit_version": "test-kit", "options": {"mps_bond_dimension": 64},
            "qubits": ["00", "01"], "status": status,
        }

    def test_init_refuses_to_replace_filled_selection(self) -> None:
        selected = self.runs / "selected_hidden.csv"
        selected.write_text("circuit,qubit,estimate\nC,01,0.5\nC,00,\n", encoding="utf-8")
        with self.assertRaises(RunCsvError):
            prepare_run_csv(self.template, "hidden", self.runs)

    def test_job_and_estimate_are_validated_and_idempotent(self) -> None:
        run_key = upsert_job(self.runs, self.job())
        completed = self.job("succeeded")
        completed["job_id"] = "platform-job-1"
        self.assertEqual(upsert_job(self.runs, completed), run_key)
        record_estimate(self.runs, {"run_key": run_key, "qubit": "01", "estimate": -0.25})
        record_estimate(self.runs, {"run_key": run_key, "qubit": "01", "estimate": -0.25})
        self.assertEqual(validate_run_csv(self.runs), (1, 1))
        with self.assertRaises(RunCsvError):
            record_estimate(self.runs, {"run_key": run_key, "qubit": "01", "estimate": 0.3})
        with self.assertRaises(RunCsvError):
            record_estimate(self.runs, {"run_key": run_key, "qubit": "99", "estimate": 0.3})

    def test_estimate_requires_succeeded_job(self) -> None:
        run_key = upsert_job(self.runs, self.job())
        with self.assertRaises(RunCsvError):
            record_estimate(self.runs, {"run_key": run_key, "qubit": "00", "estimate": 0.1})

    def test_selection_preserves_official_order(self) -> None:
        select_estimate(self.runs, {"dataset": "hidden", "circuit": "C", "qubit": "00", "estimate": 0.5})
        with (self.runs / "selected_hidden.csv").open(newline="", encoding="utf-8") as source:
            rows = list(csv.reader(source))
        self.assertEqual(rows, [
            ["circuit", "qubit", "estimate"], ["C", "01", ""], ["C", "00", "0.5"],
        ])
        with self.assertRaises(RunCsvError):
            select_estimate(self.runs, {"dataset": "hidden", "circuit": "C", "qubit": "99", "estimate": 0.1})


if __name__ == "__main__":
    unittest.main()
