"""Exercise the released sample layout with ZIP and extracted QASM copies."""

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from zipfile import ZipFile

from bluequbit_samples.inputs import discover_samples


def qasm(gate: str) -> bytes:
    return (
        "OPENQASM 2.0;\n"
        'include "qelib1.inc";\n'
        "qreg q[1];\n"
        f"{gate} q[0];\n"
    ).encode("utf-8")


class SampleInputTests(unittest.TestCase):
    def test_identical_zip_and_extracted_copies_are_one_sample(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            circuits = root / "circuits"
            circuits.mkdir()
            with ZipFile(root / "samples.zip", "w") as archive:
                for group in ("S1", "S2", "S3"):
                    name = f"Duke_{group}_0.qasm"
                    original = qasm("x")
                    (circuits / name).write_bytes(original.replace(b"\n", b"\r\n"))
                    archive.writestr(name, original)

            report = discover_samples(root, expected_total=3)

            self.assertTrue(report.ready, report.issues)
            self.assertEqual(len(report.samples), 3)
            self.assertTrue(all("samples.zip!" in sample.source for sample in report.samples))

    def test_conflicting_copies_are_rejected(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "Duke_S1_0.qasm").write_bytes(qasm("x"))
            with ZipFile(root / "samples.zip", "w") as archive:
                archive.writestr("Duke_S1_0.qasm", qasm("z"))

            report = discover_samples(root, expected_total=1)

            self.assertFalse(report.ready)
            self.assertTrue(any("Conflicting QASM content for Duke_S1_0" in issue for issue in report.issues))
            self.assertEqual(report.samples, [])


if __name__ == "__main__":
    unittest.main()
