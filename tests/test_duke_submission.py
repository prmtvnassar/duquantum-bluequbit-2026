from __future__ import annotations

import csv
from pathlib import Path
import tempfile
import unittest

from otoc.duke_submission import DukeSubmissionError, build_submission, write_submission


def write_rows(path: Path, rows: list[list[str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as output:
        csv.writer(output).writerows(rows)


class DukeSubmissionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.template = self.root / "template.csv"
        self.selected = self.root / "selected.csv"
        write_rows(self.template, [
            ["circuit_id", "value"], ["Duke_S1_1", ""], ["Duke_S1_0", ""],
        ])

    def test_builds_per_problem_csv_in_published_order(self) -> None:
        write_rows(self.selected, [
            ["circuit_id", "value"], ["Duke_S1_0", "0.25"], ["Duke_S1_1", "-0.5"],
        ])
        payload = build_submission(self.template, self.selected)
        self.assertEqual(payload.decode(), "circuit_id,value\nDuke_S1_1,-0.5\nDuke_S1_0,0.25\n")
        output = self.root / "baseline.csv"
        self.assertTrue(write_submission(payload, output, immutable=True)[0])
        self.assertFalse(write_submission(payload, output, immutable=True)[0])
        with self.assertRaises(DukeSubmissionError):
            write_submission(b"different", output, immutable=True)
        self.assertEqual(output.read_bytes(), payload)

    def test_rejects_missing_or_nonfinite_values(self) -> None:
        for rows in (
            [["circuit_id", "value"], ["Duke_S1_0", "0.1"]],
            [["circuit_id", "value"], ["Duke_S1_0", "0.1"], ["Duke_S1_1", "nan"]],
        ):
            with self.subTest(rows=rows):
                write_rows(self.selected, rows)
                with self.assertRaises(DukeSubmissionError):
                    build_submission(self.template, self.selected)


if __name__ == "__main__":
    unittest.main()
