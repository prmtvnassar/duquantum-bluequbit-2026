"""Install the published sample QASM archives and create all seven problem folders.

The four graded problems are intentionally ID-only: BlueQubit does not publish
their QASM. This script never submits a simulation job or uses an API token.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
from pathlib import Path
import re
from zipfile import ZipFile


ROOT = Path(__file__).resolve().parents[1]
PROBLEMS = (
    (1, "S1", "sample", 4, 100, "1D Haar-random chain; 4 two-qubit layers; butterfly q0"),
    (2, "S2", "sample", 16, 100, "1D Haar-random chain; 12 two-qubit layers; butterfly q0"),
    (3, "S3", "sample", 30, 100, "5x6 mostly-Clifford grid; 16 two-qubit layers; butterfly q14"),
    (4, "G1", "graded", 30, 300, "1D Haar-random chain; 32 two-qubit layers; butterfly q0"),
    (5, "G2", "graded", 36, 600, "1D Haar-random chain; 18 two-qubit layers; butterfly q18"),
    (6, "G3", "graded", 36, 800, "6x6 mostly-Clifford grid; 24 two-qubit layers; butterfly q14"),
    (7, "G4", "graded", 38, 1000, "38-qubit Haar-random grid; 16 two-qubit layers; butterfly q0"),
)
SOURCE_URL = "https://app.bluequbit.io/hackathons/2GMaAenu3iSsIC6Z?tab=problems"


def csv_bytes(rows: list[list[str]]) -> bytes:
    buffer = io.StringIO(newline="")
    csv.writer(buffer, lineterminator="\n").writerows(rows)
    return buffer.getvalue().encode("utf-8")


def write_if_new_or_identical(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_bytes() != payload:
            raise ValueError(f"Existing file differs; refusing to overwrite: {path}")
        return
    path.write_bytes(payload)


def verify_qasm(data: bytes, circuit_id: str, num_qubits: int) -> None:
    text = data.decode("utf-8")
    if not text.lstrip().startswith("OPENQASM 2.0;"):
        raise ValueError(f"Missing OpenQASM 2.0 header: {circuit_id}")
    match = re.search(r"(?m)^\s*qreg\s+q\[(\d+)\];", text)
    if match is None or int(match.group(1)) != num_qubits:
        raise ValueError(f"Unexpected qreg size: {circuit_id}")
    if re.search(r"(?m)^\s*measure\b", text):
        raise ValueError(f"Downloaded circuit includes measurement: {circuit_id}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--downloads-dir", type=Path, default=Path.home() / "Downloads")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "problems")
    args = parser.parse_args()

    for number, code, kind, num_qubits, points, description in PROBLEMS:
        folder = args.output_dir / f"{number:02d}_{kind}_{code}"
        identifiers = [f"Duke_{code}_{q}" for q in range(num_qubits)]
        write_if_new_or_identical(
            folder / "circuit_ids.csv",
            csv_bytes([["circuit_id", "qubit"]] + [[cid, str(q)] for q, cid in enumerate(identifiers)]),
        )
        blank_submission = csv_bytes([["circuit_id", "value"]] + [[cid, ""] for cid in identifiers])
        write_if_new_or_identical(folder / "local_submission_template.csv", blank_submission)
        selected = folder / "selected.csv"
        if not selected.exists():
            selected.write_bytes(blank_submission)

        source_note = "The QASM files are not published. Run each circuit by ID through BlueQubit."
        if kind == "sample":
            archive_name = f"duke-otoc-problem-{number}-sample-qasms.zip"
            source = args.downloads_dir / archive_name
            if not source.is_file():
                raise FileNotFoundError(f"Download missing: {source}")
            archive_bytes = source.read_bytes()
            with ZipFile(io.BytesIO(archive_bytes)) as archive:
                expected_names = {f"{cid}.qasm" for cid in identifiers}
                actual_names = set(archive.namelist())
                if len(actual_names) != len(archive.namelist()) or actual_names != expected_names:
                    raise ValueError(f"Unexpected archive entries in {source}: {sorted(actual_names ^ expected_names)}")
                if archive.testzip() is not None:
                    raise ValueError(f"Archive checksum failed: {source}")
                circuits: dict[str, bytes] = {}
                for circuit_id in identifiers:
                    data = archive.read(f"{circuit_id}.qasm")
                    verify_qasm(data, circuit_id, num_qubits)
                    circuits[circuit_id] = data
            write_if_new_or_identical(folder / archive_name, archive_bytes)
            hash_rows = [["circuit_id", "sha256", "bytes"]]
            for circuit_id, data in circuits.items():
                write_if_new_or_identical(folder / "circuits" / f"{circuit_id}.qasm", data)
                hash_rows.append([circuit_id, hashlib.sha256(data).hexdigest(), str(len(data))])
            write_if_new_or_identical(folder / "circuits_sha256.csv", csv_bytes(hash_rows))
            source_note = f"The `circuits/` directory has one QASM per ID, extracted from `{archive_name}`."

        readme = (
            f"# Problem {number}: {code}\n\n"
            f"- Type: {kind}\n"
            f"- Qubits / circuit IDs: {num_qubits}\n"
            f"- Maximum points: {points}\n"
            f"- Structure: {description}\n"
            f"- Source: {SOURCE_URL}\n\n"
            f"{source_note}\n\n"
            "`circuit_ids.csv` lists the published IDs in qubit order. "
            "`local_submission_template.csv` follows the released per-problem "
            "`circuit_id,value` format; it is a local template derived from the "
            "published IDs, not an organizer download. Values are intentionally blank.\n"
        )
        write_if_new_or_identical(folder / "README.md", readme.encode("utf-8"))
        print(f"Prepared {folder.name}: {num_qubits} IDs" + (f", {num_qubits} QASM files" if kind == "sample" else ", ID-only"))


if __name__ == "__main__":
    main()
