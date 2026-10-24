"""Template-locked CSV validation and recoverable checkpoints."""

from __future__ import annotations

import csv
import io
import math
import os
from pathlib import Path
import tempfile
from typing import Mapping


HEADER = ("circuit", "qubit", "estimate")
Target = tuple[str, str]


class SubmissionError(ValueError):
    """An estimate file cannot be submitted against the given template."""


def _read_rows(path: Path) -> list[dict[str, str]]:
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as source:
            reader = csv.DictReader(source)
            if tuple(reader.fieldnames or ()) != HEADER:
                raise SubmissionError(f"{path}: expected header {','.join(HEADER)}")
            rows = list(reader)
    except (OSError, UnicodeError, csv.Error) as exc:
        raise SubmissionError(f"Cannot read {path}: {exc}") from exc
    if not rows:
        raise SubmissionError(f"{path}: no target rows")
    for line_number, row in enumerate(rows, 2):
        if None in row or any(value is None for value in row.values()):
            raise SubmissionError(f"{path}:{line_number}: wrong number of columns")
    return rows


def _target(row: Mapping[str, str], path: Path, line_number: int) -> Target:
    circuit = row["circuit"].strip()
    qubit = row["qubit"].strip()
    if not circuit or not qubit:
        raise SubmissionError(f"{path}:{line_number}: circuit and qubit are required")
    return circuit, qubit


def read_template(path: Path) -> list[Target]:
    """Return the authoritative target keys in the template's row order."""
    path = Path(path)
    targets: list[Target] = []
    seen: set[Target] = set()
    for line_number, row in enumerate(_read_rows(path), 2):
        target = _target(row, path, line_number)
        if target in seen:
            raise SubmissionError(f"{path}:{line_number}: duplicate target {target}")
        seen.add(target)
        targets.append(target)
    return targets


def read_estimates(path: Path) -> dict[Target, float]:
    """Read finite real estimates keyed by the official circuit/qubit labels."""
    path = Path(path)
    estimates: dict[Target, float] = {}
    for line_number, row in enumerate(_read_rows(path), 2):
        target = _target(row, path, line_number)
        if target in estimates:
            raise SubmissionError(f"{path}:{line_number}: duplicate estimate for {target}")
        raw = row["estimate"].strip()
        try:
            value = float(raw)
        except ValueError as exc:
            raise SubmissionError(f"{path}:{line_number}: nonnumeric estimate for {target}") from exc
        if not math.isfinite(value):
            raise SubmissionError(f"{path}:{line_number}: nonfinite estimate for {target}")
        estimates[target] = value
    return estimates


def validate_against_template(template: list[Target], estimates: Mapping[Target, float]) -> None:
    required = set(template)
    given = set(estimates)
    missing = required - given
    extra = given - required
    if missing or extra:
        details = []
        if missing:
            details.append(f"missing {len(missing)}: {sorted(missing)[:5]}")
        if extra:
            details.append(f"unexpected {len(extra)}: {sorted(extra)[:5]}")
        raise SubmissionError("Estimate keys differ from template (" + "; ".join(details) + ")")
    for target, value in estimates.items():
        if isinstance(value, bool) or not isinstance(value, (float, int)) or not math.isfinite(value):
            raise SubmissionError(f"Invalid estimate for {target}: {value!r}")


def _csv_bytes(template: list[Target], estimates: Mapping[Target, float]) -> bytes:
    validate_against_template(template, estimates)
    buffer = io.StringIO(newline="")
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(HEADER)
    for circuit, qubit in template:
        writer.writerow((circuit, qubit, format(estimates[(circuit, qubit)], ".17g")))
    return buffer.getvalue().encode("utf-8")


def write_validated_csv(
    template: list[Target],
    estimates: Mapping[Target, float],
    destination: Path,
    *,
    immutable: bool = False,
) -> bool:
    """Atomically write a complete CSV; immutable outputs cannot be changed.

    Returns True when created/replaced and False for an identical immutable file.
    """
    destination = Path(destination)
    payload = _csv_bytes(template, estimates)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb", dir=destination.parent, prefix=".checkpoint-", suffix=".tmp", delete=False
        ) as output:
            temporary = Path(output.name)
            output.write(payload)
            output.flush()
            os.fsync(output.fileno())
        if temporary.read_bytes() != payload:
            raise OSError(f"Temporary checkpoint failed verification: {temporary}")
        if immutable:
            try:
                # A same-directory hard link creates the final name without an overwrite race.
                os.link(temporary, destination)
            except FileExistsError:
                if destination.read_bytes() == payload:
                    return False
                raise SubmissionError(f"Protected baseline already exists with different values: {destination}")
        else:
            os.replace(temporary, destination)
        return True
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def checkpoint_from_files(
    template_path: Path, estimates_path: Path, destination: Path, *, immutable: bool = False
) -> bool:
    template = read_template(template_path)
    estimates = read_estimates(estimates_path)
    return write_validated_csv(template, estimates, destination, immutable=immutable)
