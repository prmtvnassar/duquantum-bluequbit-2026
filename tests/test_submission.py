from __future__ import annotations

import csv
from pathlib import Path
import tempfile
import unittest

from otoc.submission import SubmissionError, checkpoint_from_files, read_estimates, read_template


def write_csv(path: Path, rows: list[list[str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as output:
        csv.writer(output).writerows(rows)


class SubmissionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.template = self.root / "template.csv"
        self.estimates = self.root / "estimates.csv"
        self.baseline = self.root / "baseline.csv"
        write_csv(self.template, [
            ["circuit", "qubit", "estimate"], ["circuit-B", "01", ""], ["circuit-A", "00", ""],
        ])

    def test_checkpoint_preserves_template_order_and_protects_baseline(self) -> None:
        write_csv(self.estimates, [
            ["circuit", "qubit", "estimate"], ["circuit-A", "00", "0.25"], ["circuit-B", "01", "-0.5"],
        ])
        self.assertTrue(checkpoint_from_files(self.template, self.estimates, self.baseline, immutable=True))
        self.assertFalse(checkpoint_from_files(self.template, self.estimates, self.baseline, immutable=True))
        self.assertEqual(list(read_estimates(self.baseline)), read_template(self.template))
        original = self.baseline.read_bytes()
        write_csv(self.estimates, [
            ["circuit", "qubit", "estimate"], ["circuit-A", "00", "0.25"], ["circuit-B", "01", "0.4"],
        ])
        with self.assertRaises(SubmissionError):
            checkpoint_from_files(self.template, self.estimates, self.baseline, immutable=True)
        self.assertEqual(self.baseline.read_bytes(), original)
        self.assertEqual(list(self.root.glob(".checkpoint-*.tmp")), [])

    def test_rejects_missing_duplicate_and_nonfinite_estimates(self) -> None:
        for rows in (
            [["circuit", "qubit", "estimate"], ["circuit-A", "00", "0.2"]],
            [["circuit", "qubit", "estimate"], ["circuit-A", "00", "0.2"], ["circuit-A", "00", "0.3"]],
            [["circuit", "qubit", "estimate"], ["circuit-A", "00", "0.2"], ["circuit-B", "01", "nan"]],
        ):
            with self.subTest(rows=rows):
                write_csv(self.estimates, rows)
                with self.assertRaises(SubmissionError):
                    checkpoint_from_files(self.template, self.estimates, self.baseline, immutable=True)
                self.assertFalse(self.baseline.exists())

    def test_rejects_duplicate_template_targets(self) -> None:
        write_csv(self.template, [
            ["circuit", "qubit", "estimate"], ["circuit-A", "00", ""], ["circuit-A", "00", ""],
        ])
        with self.assertRaises(SubmissionError):
            read_template(self.template)


if __name__ == "__main__":
    unittest.main()
