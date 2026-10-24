"""Legacy pre-release combined CSV exporter from accepted MPS/PPS estimates.

The released Duke challenge requires one circuit_id,value CSV per problem.
Use export_problem_submission.py for uploads instead.

Usage:
    python scripts/export_submission.py --template path/to/official_template.csv \
        --output submissions/submission.csv
    python scripts/export_submission.py --set sample \
        --template path/to/official_sample_template.csv

The official template controls circuit IDs, qubit IDs, and row order. This script
reads raw accepted estimates, so it does not depend on Excel's cached formulas.
For extrapolation it uses a straight line in 1/chi (MPS) or epsilon (PPS),
with the intercept set by the two finest selected levels.
"Calibrated" selects a separately entered, model-labeled estimate vector.
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
}
FILES = {
    "hidden": ["hidden_1.xlsx", "hidden_2.xlsx", "hidden_3.xlsx", "hidden_4.xlsx"],
    "sample": ["sample_1.xlsx", "sample_2.xlsx"],
}


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


def accepted(value: object, label: str) -> bool:
    if value is None or value == "":
        return False
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(float(value)) or value not in (0, 1):
        raise ValueError(f"{label} must be numeric 1 (accepted) or 0 (ignored)")
    return value == 1


def selected_run(workbook_path: Path, set_name: str = "hidden") -> tuple[str, set[str], dict[str, float]]:
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
    targets = [identifier(qubits.get(f"A{row}")) for row in range(6, 166)]
    targets = [value for value in targets if value]
    if len(targets) != int(required) or len(set(targets)) != len(targets):
        raise ValueError(f"{workbook_path.name}: Qubits target IDs must be unique and match Status!B5")
    target_set = set(targets)

    raw_choice = identifier(status.get("B6"))
    if raw_choice.lower() == "calibrated":
        model_note = status.get("B30")
        if not isinstance(model_note, str) or not model_note.strip():
            raise ValueError(f"{workbook_path.name}: Calibrated needs a model ID/evidence note in Status!B30")
        if set_name == "hidden" and identifier(status.get("B7")).lower() != "yes":
            raise ValueError(f"{workbook_path.name}: hidden Calibrated needs Yes in Status!B7")
        chosen: dict[str, float] = {}
        for row in range(6, 166):
            q = identifier(qubits.get(f"A{row}"))
            value = qubits.get(f"Q{row}")
            if not q:
                if value is not None and value != "":
                    raise ValueError(f"{workbook_path.name}: Calibrated value in Qubits!Q{row} has no qubit ID")
                continue
            if value is None or value == "":
                continue
            chosen[q] = numeric(value, f"{workbook_path.name} Qubits!Q{row}")
        missing = target_set - chosen.keys()
        if missing:
            preview = ", ".join(sorted(missing)[:6])
            raise ValueError(f"{workbook_path.name}: Calibrated is missing {len(missing)} qubits ({preview})")
        return circuit, target_set, chosen

    choice = raw_choice.split()
    if len(choice) != 2 or choice[0].upper() not in {"MPS", "PPS"} or choice[1].lower() not in {"1", "2", "3", "extrap"}:
        raise ValueError(f"{workbook_path.name}: choose MPS/PPS 1, 2, 3, extrap, or Calibrated in Status!B6")
    method, selection = choice[0].upper(), choice[1].lower()
    extrapolate = selection == "extrap"
    if extrapolate and set_name == "hidden" and identifier(status.get("B7")).lower() != "yes":
        raise ValueError(f"{workbook_path.name}: hidden extrapolation needs Yes in Status!B7")
    setting_row = 5 if method == "MPS" else 6
    slots = [1, 2, 3] if extrapolate else [int(selection)]
    settings = {}
    for slot in slots:
        column = {1: "E", 2: "F", 3: "G"}[slot]
        settings[slot] = numeric(status.get(f"{column}{setting_row}"), f"{workbook_path.name} {method} setting {slot}")
    if any(setting <= 0 for setting in settings.values()):
        raise ValueError(f"{workbook_path.name}: selected precision settings must be positive")
    if extrapolate:
        xs = [1 / settings[i] if method == "MPS" else settings[i] for i in (1, 2, 3)]
        if not (xs[0] > xs[1] > xs[2] > 0):
            raise ValueError(f"{workbook_path.name}: extrapolation needs three distinct settings ordered coarse to fine")
        if math.isclose(xs[1], xs[2], rel_tol=1e-12, abs_tol=0):
            raise ValueError(f"{workbook_path.name}: the final two precision settings are too close to extrapolate")
    transpile = numeric(status.get("E7"), f"{workbook_path.name} PPS transpilation") if method == "PPS" else None

    by_slot: dict[int, dict[str, float]] = {slot: {} for slot in slots}
    for row in range(5, 2005):
        if not accepted(estimates.get(f"H{row}"), f"{workbook_path.name} Estimates!H{row}"):
            continue
        if identifier(estimates.get(f"B{row}")).upper() != method:
            continue
        q = identifier(estimates.get(f"A{row}"))
        if not q:
            raise ValueError(f"{workbook_path.name}: accepted estimate on row {row} has no qubit ID")
        if method == "MPS":
            entry_setting = numeric(estimates.get(f"C{row}"), f"{workbook_path.name} Estimates!C{row}")
            matched = [slot for slot, setting in settings.items() if entry_setting == setting]
        else:
            entry_setting = numeric(estimates.get(f"D{row}"), f"{workbook_path.name} Estimates!D{row}")
            entry_transpile = numeric(estimates.get(f"E{row}"), f"{workbook_path.name} Estimates!E{row}")
            if entry_transpile != transpile:
                continue
            matched = [slot for slot, setting in settings.items() if entry_setting == setting]
        if not matched:
            continue
        if q not in target_set:
            raise ValueError(f"{workbook_path.name}: selected run has unexpected qubit {q}")
        value = numeric(estimates.get(f"F{row}"), f"{workbook_path.name} Estimates!F{row}")
        for slot in matched:
            if q in by_slot[slot]:
                raise ValueError(f"{workbook_path.name}: multiple accepted {method} estimates for qubit {q}, setting {slot}")
            by_slot[slot][q] = value
    for slot, values in by_slot.items():
        missing = target_set - values.keys()
        if missing:
            preview = ", ".join(sorted(missing)[:6])
            raise ValueError(f"{workbook_path.name}: {method} setting {slot} is missing {len(missing)} accepted qubits ({preview})")
    if extrapolate:
        x2, x3 = xs[1], xs[2]
        chosen = {
            q: (x2 * by_slot[3][q] - x3 * by_slot[2][q]) / (x2 - x3)
            for q in target_set
        }
        if any(not math.isfinite(value) for value in chosen.values()):
            raise ValueError(f"{workbook_path.name}: extrapolation produced a nonfinite result")
    else:
        chosen = by_slot[int(selection)]
    return circuit, target_set, chosen


def build_rows(template_path: Path, runs_dir: Path, set_name: str = "hidden") -> list[list[str]]:
    if not template_path.is_file():
        raise ValueError(f"Official template not found: {template_path}")
    selected: dict[str, tuple[set[str], dict[str, float]]] = {}
    for file in FILES[set_name]:
        path = runs_dir / file
        if not path.is_file():
            raise ValueError(f"Missing workbook: {path}")
        circuit, targets, values = selected_run(path, set_name)
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
        if None in row:
            raise ValueError("Official template has a row with extra columns")
        circuit, q = (row["circuit"] or "").strip(), (row["qubit"] or "").strip()
        key = (circuit, q)
        if not circuit or not q or key in seen:
            raise ValueError(f"Blank or duplicate circuit/qubit in official template: {key}")
        seen.add(key)
        if circuit not in selected or q not in selected[circuit][0]:
            raise ValueError(f"Template row is not present in the selected workbooks: {key}")
        by_circuit[circuit].add(q)
        output.append([circuit, q, format(selected[circuit][1][q], ".17g")])
    if any(not qubits for qubits in by_circuit.values()):
        raise ValueError(f"Official template does not include all {len(FILES[set_name])} {set_name} circuits")
    for circuit, (targets, _) in selected.items():
        if by_circuit[circuit] != targets:
            raise ValueError(f"Official template does not match the target qubits for circuit {circuit}")
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--set", choices=tuple(FILES), default="hidden", help="Circuit set to export (default: hidden)")
    parser.add_argument("--template", type=Path, required=True, help="Released hackathon submission template CSV")
    parser.add_argument("--output", type=Path, help="CSV destination; defaults under submissions/")
    parser.add_argument("--runs-dir", type=Path, default=ROOT / "runs")
    parser.add_argument("--overwrite", action="store_true", help="Replace an existing output CSV")
    args = parser.parse_args()
    if args.output is None:
        filename = "submission.csv" if args.set == "hidden" else "samples_estimates.csv"
        args.output = ROOT / "submissions" / filename
    try:
        rows = build_rows(args.template, args.runs_dir, args.set)
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
