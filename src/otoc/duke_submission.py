"""Validate the released challenge's one-file-per-problem CSV format."""

from __future__ import annotations

import csv
import hashlib
import io
import math
import os
from pathlib import Path
import tempfile


HEADER = ("circuit_id", "value")


class DukeSubmissionError(ValueError):
    """A per-problem CSV is incomplete or malformed."""


def _read(path: Path, *, values_required: bool) -> list[tuple[str, str]]:
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as source:
            reader = csv.DictReader(source)
            if tuple(reader.fieldnames or ()) != HEADER:
                raise DukeSubmissionError(f"{path}: expected header circuit_id,value")
            rows = list(reader)
    except (OSError, UnicodeError, csv.Error) as exc:
        raise DukeSubmissionError(f"Cannot read {path}: {exc}") from exc
    if not rows:
        raise DukeSubmissionError(f"{path}: no circuit IDs")
    result: list[tuple[str, str]] = []
    seen: set[str] = set()
    for line_number, row in enumerate(rows, 2):
        if None in row or any(value is None for value in row.values()):
            raise DukeSubmissionError(f"{path}:{line_number}: wrong number of columns")
        circuit_id = row["circuit_id"].strip()
        value = row["value"].strip()
        if not circuit_id or circuit_id in seen:
            raise DukeSubmissionError(f"{path}:{line_number}: blank or duplicate circuit ID {circuit_id!r}")
        seen.add(circuit_id)
        if values_required:
            try:
                numeric = float(value)
            except ValueError as exc:
                raise DukeSubmissionError(f"{path}:{line_number}: nonnumeric value for {circuit_id}") from exc
            if not math.isfinite(numeric):
                raise DukeSubmissionError(f"{path}:{line_number}: nonfinite value for {circuit_id}")
        result.append((circuit_id, value))
    return result


def build_submission(template_path: Path, values_path: Path) -> bytes:
    """Return a validated submission in the local template's published ID order."""
    expected = [circuit_id for circuit_id, _ in _read(template_path, values_required=False)]
    chosen = dict(_read(values_path, values_required=True))
    missing = set(expected) - set(chosen)
    extra = set(chosen) - set(expected)
    if missing or extra:
        raise DukeSubmissionError(
            f"IDs differ from {template_path}: missing {sorted(missing)[:5]}, extra {sorted(extra)[:5]}"
        )
    buffer = io.StringIO(newline="")
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(HEADER)
    for circuit_id in expected:
        writer.writerow((circuit_id, format(float(chosen[circuit_id]), ".17g")))
    return buffer.getvalue().encode("utf-8")


def write_submission(payload: bytes, path: Path, *, immutable: bool = False) -> tuple[bool, str]:
    """Write complete bytes atomically; protected baselines cannot be replaced."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile("wb", dir=path.parent, prefix=".duke-", suffix=".tmp", delete=False) as output:
            temporary = Path(output.name)
            output.write(payload)
            output.flush()
            os.fsync(output.fileno())
        if immutable:
            try:
                os.link(temporary, path)
            except FileExistsError:
                if path.read_bytes() == payload:
                    return False, hashlib.sha256(payload).hexdigest()
                raise DukeSubmissionError(f"Protected baseline already differs: {path}")
        else:
            os.replace(temporary, path)
        return True, hashlib.sha256(payload).hexdigest()
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
