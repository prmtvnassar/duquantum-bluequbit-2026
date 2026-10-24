"""Build the challenge CSV from selected MPS/PPS runs in the four hidden workbooks.

Usage:
    python scripts/export_submission.py --template path/to/official_template.csv \
        --output submissions/submission.csv

The official template controls circuit IDs, qubit IDs, and row order. This script
reads raw estimates, so it does not depend on Excel's cached formula values.
"""

from __future__ import annotations

import argparse
import csv
import math
import os
from pathlib import Path
import tempfile
from xml.etree import ElementTree as ET
from zipfile import ZipFile


ROOT = Path(__file__).resolve().parents[1]
NS = {
    "x": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "p": "http://schemas.openxmlformats.org/package/2006/relationships",
}
FILES = ["hidden_1.xlsx", "hidden_2.xlsx", "hidden_3.xlsx", "hidden_4.xlsx"]


def identifier(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, (int, float)) and float(value).is_integer():
        return str(int(value))
    return str(value).strip()


def numeric(value: object, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{label} must be a numeric cell")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{label} must be finite")
    return result


def sheet_cells(book: ZipFile, name: str) -> dict[str, object]:
    workbook = ET.fromstring(book.read("xl/workbook.xml"))
    relations = ET.fromstring(book.read("xl/_rels/workbook.xml.rels"))
    targets = {node.attrib["Id"]: node.attrib["Target"] for node in relations}
    sheets = {
        node.attrib["name"]: targets[node.attrib[f"{{{NS['r']}}}id"]]
        for node in workbook.findall("x:sheets/x:sheet", NS)
    }
    if name not in sheets:
        raise ValueError(f"Missing worksheet: {name}")
    target = sheets[name].lstrip("/")
    if not target.startswith("xl/"):
        target = f"xl/{target}"
    shared: list[str] = []
    if "xl/sharedStrings.xml" in book.namelist():
        strings = ET.fromstring(book.read("xl/sharedStrings.xml"))
        shared = ["".join(t.text or "" for t in item.iter(f"{{{NS['x']}}}t")) for item in strings]
    sheet = ET.fromstring(book.read(target))
    cells: dict[str, object] = {}
    for cell in sheet.findall(".//x:sheetData/x:row/x:c", NS):
        address = cell.attrib["r"]
        kind = cell.attrib.get("t")
        value = cell.find("x:v", NS)
        if kind == "inlineStr":
            inline = cell.find("x:is", NS)
            cells[address] = "" if inline is None else "".join(
                t.text or "" for t in inline.iter(f"{{{NS['x']}}}t")
            )
        elif value is None or value.text is None:
            continue
        elif kind == "s":
            cells[address] = shared[int(value.text)]
        elif kind in {"str", "e"}:
            cells[address] = value.text
        elif kind == "b":
            cells[address] = value.text == "1"
        else:
            cells[address] = float(value.text)
    return cells


def selected_run(workbook_path: Path) -> tuple[str, set[str], dict[str, float]]:
    with ZipFile(workbook_path) as book:
        status = sheet_cells(book, "Status")
        qubits = sheet_cells(book, "Qubits")
        estimates = sheet_cells(book, "Estimates")

    circuit = identifier(status.get("B4"))
    if not circuit:
        raise ValueError(f"{workbook_path.name}: enter the official circuit ID in Status!B4")
    required = numeric(status.get("B5"), f"{workbook_path.name} Status!B5")
    if required <= 0 or not required.is_integer():
        raise ValueError(f"{workbook_path.name}: required qubits must be a positive integer")
    method = identifier(status.get("B13")).upper()
    if method not in {"MPS", "PPS"}:
        raise ValueError(f"{workbook_path.name}: choose MPS or PPS in Status!B13")
    slot = numeric(status.get("B14"), f"{workbook_path.name} Status!B14")
    if slot not in {1, 2, 3}:
        raise ValueError(f"{workbook_path.name}: precision slot must be 1, 2, or 3")
    column = {1: "E", 2: "F", 3: "G"}[int(slot)]
    setting_row = 5 if method == "MPS" else 6
    setting = numeric(status.get(f"{column}{setting_row}"), f"{workbook_path.name} precision setting")
    transpile = numeric(status.get("E7"), f"{workbook_path.name} PPS transpilation") if method == "PPS" else None

    targets = [identifier(qubits.get(f"A{row}")) for row in range(6, 166)]
    targets = [value for value in targets if value]
    if len(targets) != int(required) or len(set(targets)) != len(targets):
        raise ValueError(f"{workbook_path.name}: Qubits target IDs must be unique and match Status!B5")
    target_set = set(targets)

    chosen: dict[str, float] = {}
    for row in range(5, 2005):
        q = identifier(estimates.get(f"A{row}"))
        if not q or identifier(estimates.get(f"B{row}")).upper() != method:
            continue
        if method == "MPS":
            entry_setting = estimates.get(f"C{row}")
            match = isinstance(entry_setting, (int, float)) and float(entry_setting) == setting
        else:
            entry_setting = estimates.get(f"D{row}")
            entry_transpile = estimates.get(f"E{row}")
            match = (
                isinstance(entry_setting, (int, float))
                and math.isclose(float(entry_setting), setting, rel_tol=0, abs_tol=1e-12)
                and isinstance(entry_transpile, (int, float))
                and float(entry_transpile) == transpile
            )
        if not match:
            continue
        if q not in target_set:
            raise ValueError(f"{workbook_path.name}: selected run has unexpected qubit {q}")
        if q in chosen:
            raise ValueError(f"{workbook_path.name}: duplicate selected estimate for qubit {q}")
        chosen[q] = numeric(estimates.get(f"F{row}"), f"{workbook_path.name} Estimates!F{row}")
    missing = target_set - chosen.keys()
    if missing:
        preview = ", ".join(sorted(missing)[:6])
        raise ValueError(f"{workbook_path.name}: selected run is missing {len(missing)} qubits ({preview})")
    return circuit, target_set, chosen


def build_rows(template_path: Path, runs_dir: Path) -> list[list[str]]:
    if not template_path.is_file():
        raise ValueError(f"Official template not found: {template_path}")
    selected: dict[str, tuple[set[str], dict[str, float]]] = {}
    for file in FILES:
        path = runs_dir / file
        if not path.is_file():
            raise ValueError(f"Missing workbook: {path}")
        circuit, targets, values = selected_run(path)
        if circuit in selected:
            raise ValueError(f"Official circuit ID {circuit} appears in multiple workbooks")
        selected[circuit] = (targets, values)

    with template_path.open("r", encoding="utf-8-sig", newline="") as source:
        reader = csv.DictReader(source)
        if reader.fieldnames != ["circuit", "qubit", "estimate"]:
            raise ValueError("Official template must have exactly: circuit,qubit,estimate")
        template = list(reader)
    if not template:
        raise ValueError("Official template has no rows")
    seen: set[tuple[str, str]] = set()
    output: list[list[str]] = [["circuit", "qubit", "estimate"]]
    by_circuit: dict[str, set[str]] = {circuit: set() for circuit in selected}
    for row in template:
        circuit, q = row["circuit"].strip(), row["qubit"].strip()
        key = (circuit, q)
        if not circuit or not q or key in seen:
            raise ValueError(f"Blank or duplicate circuit/qubit in official template: {key}")
        seen.add(key)
        if circuit not in selected or q not in selected[circuit][0]:
            raise ValueError(f"Template row is not present in the selected workbooks: {key}")
        by_circuit[circuit].add(q)
        output.append([circuit, q, format(selected[circuit][1][q], ".17g")])
    if set(by_circuit) != {c for c, qubits in by_circuit.items() if qubits}:
        raise ValueError("Official template does not include all four hidden circuits")
    for circuit, (targets, _) in selected.items():
        if by_circuit[circuit] != targets:
            raise ValueError(f"Official template does not match the target qubits for circuit {circuit}")
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--template", type=Path, required=True, help="Released hackathon submission template CSV")
    parser.add_argument("--output", type=Path, default=ROOT / "submissions" / "submission.csv")
    parser.add_argument("--runs-dir", type=Path, default=ROOT / "runs")
    parser.add_argument("--overwrite", action="store_true", help="Replace an existing output CSV")
    args = parser.parse_args()
    try:
        rows = build_rows(args.template, args.runs_dir)
    except (ValueError, OSError, KeyError) as exc:
        parser.exit(2, f"Cannot export: {exc}\n")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    if args.output.exists() and not args.overwrite:
        parser.error(f"Output already exists: {args.output}. Use --overwrite to replace it.")
    temp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", newline="", dir=args.output.parent, suffix=".csv", delete=False) as temp:
            temp_path = Path(temp.name)
            writer = csv.writer(temp, lineterminator="\n")
            writer.writerows(rows)
        os.replace(temp_path, args.output)
    finally:
        if temp_path is not None and temp_path.exists():
            temp_path.unlink()
    print(f"Wrote {len(rows) - 1} estimate rows to {args.output}")


if __name__ == "__main__":
    main()
