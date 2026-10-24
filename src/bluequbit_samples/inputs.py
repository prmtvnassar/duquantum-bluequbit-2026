"""Read per-ID QASM without extracting untrusted ZIP members."""

from collections import Counter
from dataclasses import dataclass, field
import hashlib
from pathlib import Path, PurePosixPath
import re
from zipfile import ZipFile

from .models import SampleCircuit

ID_PATTERN = re.compile(r"Duke_(S[123])_(0|[1-9][0-9]*)\Z")
SUPPORTED_GATES = {"u3", "u", "cz", "x", "z", "id", "barrier"}
MAX_QASM_BYTES = 20 * 2**20
MAX_ARCHIVE_QASM_BYTES = 250 * 2**20


def parse_qasm(text):
    from qiskit import qasm2
    circuit = qasm2.loads(text, custom_instructions=qasm2.LEGACY_CUSTOM_INSTRUCTIONS)
    if len(circuit.qregs) != 1 or circuit.qregs[0].name != "q":
        raise ValueError("Expected one QASM quantum register named q for the target q[q]")
    if circuit.num_clbits or circuit.num_parameters:
        raise ValueError("Expected a fully bound, measurement-free circuit without classical bits")
    unsupported = set(circuit.count_ops()) - SUPPORTED_GATES
    if unsupported:
        raise ValueError(f"Unsupported QASM operations: {sorted(unsupported)}")
    return circuit


def sample_from_text(circuit_id, text, source, *, dataset_kind="official", sample=None, qubit=None, raw_sha256=None):
    if dataset_kind == "official":
        match = ID_PATTERN.fullmatch(circuit_id)
        if not match:
            raise ValueError(f"Invalid case-sensitive sample ID: {circuit_id}")
        sample, qubit = match[1], int(match[2])
    elif sample is None or qubit is None:
        raise ValueError("Synthetic checks require an explicit group and target qubit")
    circuit = parse_qasm(text)
    return SampleCircuit(
        circuit_id=circuit_id, sample=sample, qubit=qubit,
        num_qubits=circuit.num_qubits,
        qasm_sha256=raw_sha256 or hashlib.sha256(text.encode("utf-8")).hexdigest(),
        qasm_text=text, source=source,
        gate_count=sum(n for name, n in circuit.count_ops().items() if name != "barrier"),
        depth=circuit.depth(), dataset_kind=dataset_kind,
    )


@dataclass
class InputReport:
    samples: list[SampleCircuit] = field(default_factory=list)
    issues: list[str] = field(default_factory=list)
    expected_total: int = 50

    @property
    def ready(self):
        return not self.issues and len(self.samples) == self.expected_total

    def to_dict(self):
        return {"status": "READY" if self.ready else "MISSING_OR_INVALID_INPUTS",
                "expected_total": self.expected_total, "observed_total": len(self.samples),
                "issues": self.issues, "manifest": [s.manifest_row() for s in self.samples]}


def discover_samples(data_root, expected_total=50):
    root = Path(data_root)
    report = InputReport(expected_total=expected_total)
    entries = []
    if not root.exists():
        report.issues.append(f"Input directory does not exist: {root}")
    else:
        for path in sorted(root.rglob("*")):
            if not path.is_file():
                continue
            if path.suffix.lower() == ".qasm":
                if path.stat().st_size > MAX_QASM_BYTES:
                    report.issues.append(f"QASM exceeds the size limit: {path}")
                    continue
                entries.append((path.stem, path.read_bytes(), str(path)))
            elif path.suffix.lower() == ".zip":
                try:
                    with ZipFile(path) as archive:
                        total = 0
                        for item in archive.infolist():
                            member = PurePosixPath(item.filename.replace("\\", "/"))
                            if member.is_absolute() or ".." in member.parts or ":" in item.filename:
                                raise ValueError("Unsafe ZIP member path")
                            if item.is_dir() or member.suffix.lower() != ".qasm":
                                continue
                            total += item.file_size
                            if item.file_size > MAX_QASM_BYTES or total > MAX_ARCHIVE_QASM_BYTES:
                                raise ValueError("ZIP QASM content exceeds the size limit")
                            entries.append((member.stem, archive.read(item), f"{path}!{item.filename}"))
                except Exception as exc:
                    report.issues.append(f"Cannot read {path}: {exc}")
    counts = Counter(cid for cid, _, _ in entries)
    duplicated = {cid for cid, count in counts.items() if count > 1}
    for cid in sorted(duplicated):
        report.issues.append(f"Duplicate ID, including ZIP/extracted copies: {cid}")
    for cid, raw, source in entries:
        if cid in duplicated:
            continue
        try:
            text = raw.decode("utf-8-sig").replace("\r\n", "\n")
            report.samples.append(sample_from_text(cid, text, source, raw_sha256=hashlib.sha256(raw).hexdigest()))
        except Exception as exc:
            report.issues.append(f"Invalid input {source}: {exc}")
    report.samples.sort(key=lambda s: (s.sample, s.qubit))
    for label in ("S1", "S2", "S3"):
        group = [s for s in report.samples if s.sample == label]
        if not group:
            report.issues.append(f"No valid QASM files for {label}")
            continue
        dimensions = {s.num_qubits for s in group}
        if len(dimensions) != 1:
            report.issues.append(f"Inconsistent register sizes within {label}: {sorted(dimensions)}")
            continue
        n = next(iter(dimensions))
        observed = {s.qubit for s in group}
        if observed != set(range(n)):
            report.issues.append(f"Incomplete {label}: missing target indices {sorted(set(range(n)) - observed)}")
    if len(report.samples) != expected_total:
        report.issues.append(f"Expected {expected_total} sample IDs; found {len(report.samples)}")
    return report

