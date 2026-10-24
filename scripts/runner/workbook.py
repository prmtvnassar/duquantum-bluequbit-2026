"""Append rows to the run workbooks (runs/*.xlsx) without disturbing anything else.

Only the edited cells change; every other byte of the sheet XML, styles, formulas and
dropdowns is kept as is. The workbook is flagged to recalculate on open so the Qubits
and Status formulas pick up the new rows. Column layouts follow runs/README.md.
"""

from __future__ import annotations

import os
import re
import shutil
import tempfile
from datetime import datetime
from pathlib import Path
from xml.sax.saxutils import escape
from zipfile import ZIP_DEFLATED, ZipFile

from .config import ROOT

# Sheet layouts. Update here if the workbook template changes.
ESTIMATES = {"sheet": "Estimates", "first": 5, "last": 2004,
             "cols": ["A", "B", "C", "D", "E", "F", "G", "H"]}   # Qubit, Method, χ, ε, transpile, Estimate, Job ID, Accepted
JOBS = {"sheet": "Jobs", "first": 5, "last": 1004,
        "cols": ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J"]}  # Job ID, Method, χ, ε, Transpile, Status, Qubits, Wall s, Credits, Note
QUBIT_IDS = ("Qubits", "A", 6, 165)
STATUS_ID, STATUS_COUNT = ("Status", "B4"), ("Status", "B5")
SETTINGS = {"mps": ("E5", "F5", "G5"), "pps": ("E6", "F6", "G6")}
TRANSPILE = "E7"

REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"


def _col_num(col: str) -> int:
    n = 0
    for ch in col:
        n = n * 26 + ord(ch) - 64
    return n


def _split(addr: str) -> tuple[str, int]:
    m = re.fullmatch(r"([A-Z]+)(\d+)", addr)
    if not m:
        raise ValueError(f"bad cell address {addr!r}")
    return m.group(1), int(m.group(2))


def _format_number(value: float) -> str:
    value = float(value)
    return str(int(value)) if value.is_integer() and abs(value) < 1e15 else repr(value)


class Workbook:
    def __init__(self, path: Path):
        self.path = Path(path)
        lock = self.path.with_name("~$" + self.path.name)
        if lock.exists():
            raise RuntimeError(f"{self.path.name} is open in Excel ({lock.name} exists). Close it first.")
        with ZipFile(self.path) as z:
            self._infos = z.infolist()
            self._data = {i.filename: z.read(i.filename) for i in self._infos}
        self._sheet_files = self._find_sheets()
        self._xml: dict[str, str] = {}
        self.changed = False
        self._backed_up = False

    # ------------------------------------------------------------ locating sheets
    def _find_sheets(self) -> dict[str, str]:
        wb = self._data["xl/workbook.xml"].decode("utf-8")
        rels = self._data["xl/_rels/workbook.xml.rels"].decode("utf-8")
        targets = dict(re.findall(r'<(?:\w+:)?Relationship\b[^>]*?Id="([^"]+)"[^>]*?Target="([^"]+)"', rels))
        targets.update({i: t for t, i in re.findall(r'<(?:\w+:)?Relationship\b[^>]*?Target="([^"]+)"[^>]*?Id="([^"]+)"', rels)})
        sheets = {}
        for tag in re.findall(r"<(?:\w+:)?sheet\b[^>]*>", wb):
            name = re.search(r'\bname="([^"]+)"', tag).group(1)
            rid = re.search(r'\br:id="([^"]+)"', tag).group(1)
            target = targets[rid].lstrip("/")
            sheets[name] = target if target.startswith("xl/") else f"xl/{target}"
        return sheets

    def _sheet(self, name: str) -> str:
        if name not in self._sheet_files:
            raise ValueError(f"{self.path.name}: missing sheet {name!r}")
        file = self._sheet_files[name]
        if file not in self._xml:
            self._xml[file] = self._data[file].decode("utf-8")
        return file

    @staticmethod
    def _prefix(xml: str) -> str:
        m = re.search(r"<(\w+:)?worksheet\b", xml)
        return m.group(1) or ""

    # ------------------------------------------------------------ reading
    def _shared_strings(self) -> list[str]:
        raw = self._data.get("xl/sharedStrings.xml")
        if not raw:
            return []
        xml = raw.decode("utf-8")
        items = re.findall(r"<(?:\w+:)?si>(.*?)</(?:\w+:)?si>", xml, re.S)
        return ["".join(re.findall(r"<(?:\w+:)?t\b[^>]*>(.*?)</(?:\w+:)?t>", i, re.S)) for i in items]

    def _value(self, attrs: str, body: str | None, p: str):
        if not body:
            return None
        kind = re.search(r'\bt="(\w+)"', attrs)
        kind = kind.group(1) if kind else "n"
        if kind == "inlineStr":
            return _unescape("".join(re.findall(rf"<{p}t\b[^>]*>(.*?)</{p}t>", body, re.S)))
        v = re.search(rf"<{p}v>(.*?)</{p}v>", body, re.S)
        if not v:
            return None
        if kind == "s":
            return _unescape(self._shared_strings()[int(v.group(1))])
        if kind in ("str", "e"):
            return _unescape(v.group(1))
        if kind == "b":
            return v.group(1) == "1"
        return float(v.group(1))

    def get(self, sheet: str, addr: str):
        file = self._sheet(sheet)
        xml, p = self._xml[file], self._prefix(self._xml[file])
        m = re.search(rf'<{p}c r="{addr}"(?P<a>[^>]*?)(?:/>|>(?P<b>.*?)</{p}c>)', xml, re.S)
        return self._value(m.group("a"), m.group("b"), p) if m else None

    def table(self, sheet: str, first: int, last: int, cols: list[str]) -> dict[int, list]:
        """{row: [values in cols]} for rows first..last, read in one pass."""
        file = self._sheet(sheet)
        xml, p = self._xml[file], self._prefix(self._xml[file])
        out = {r: [None] * len(cols) for r in range(first, last + 1)}
        index = {c: i for i, c in enumerate(cols)}
        for cm in re.finditer(rf'<{p}c r="([A-Z]+)(\d+)"(?P<a>[^>]*?)(?:/>|>(?P<b>.*?)</{p}c>)', xml, re.S):
            col, row = cm.group(1), int(cm.group(2))
            if row in out and col in index:
                out[row][index[col]] = self._value(cm.group("a"), cm.group("b"), p)
        return out

    def column(self, sheet: str, col: str, first: int, last: int) -> list:
        return [v[0] for v in self.table(sheet, first, last, [col]).values()]

    # ------------------------------------------------------------ writing
    def set(self, sheet: str, addr: str, value) -> None:
        file = self._sheet(sheet)
        xml = self._xml[file]
        p = self._prefix(xml)
        col, row = _split(addr)
        row_re = re.compile(rf'<{p}row r="{row}"(?P<a>[^>]*?)(?:/>|>(?P<b>.*?)</{p}row>)', re.S)
        rm = row_re.search(xml)
        if not rm:
            raise ValueError(f"{self.path.name}!{sheet}: row {row} is outside the template")
        body = rm.group("b") or ""
        cell_re = re.compile(rf'<{p}c r="{addr}"(?P<a>[^>]*?)(?:/>|>(?P<b>.*?)</{p}c>)', re.S)
        cm = cell_re.search(body)
        style = ""
        if cm:
            s = re.search(r'\bs="(\d+)"', cm.group("a"))
            style = f' s="{s.group(1)}"' if s else ""
        if value is None or value == "":
            new_cell = f'<{p}c r="{addr}"{style} />'
        elif isinstance(value, str):
            new_cell = f'<{p}c r="{addr}"{style} t="inlineStr"><{p}is><{p}t>{escape(value)}</{p}t></{p}is></{p}c>'
        else:
            new_cell = f'<{p}c r="{addr}"{style} t="n"><{p}v>{_format_number(value)}</{p}v></{p}c>'
        if cm:
            body = body[:cm.start()] + new_cell + body[cm.end():]
        else:  # insert in column order
            pos = len(body)
            for other in re.finditer(rf'<{p}c r="([A-Z]+){row}"', body):
                if _col_num(other.group(1)) > _col_num(col):
                    pos = other.start()
                    break
            body = body[:pos] + new_cell + body[pos:]
        new_row = f'<{p}row r="{row}"{rm.group("a").rstrip("/").rstrip()}>{body}</{p}row>'
        self._xml[file] = xml[:rm.start()] + new_row + xml[rm.end():]
        self.changed = True

    def append_row(self, layout: dict, values: list) -> int:
        """Write values into the first row after the last used row of the layout."""
        sheet, cols = layout["sheet"], layout["cols"]
        last_used = layout["first"] - 1
        for r, existing in self.table(sheet, layout["first"], layout["last"], cols).items():
            if any(v not in (None, "") for v in existing):
                last_used = r
        row = last_used + 1
        if row > layout["last"]:
            raise RuntimeError(f"{self.path.name}!{sheet} is full (rows {layout['first']}-{layout['last']})")
        for c, v in zip(cols, values):
            self.set(sheet, f"{c}{row}", v)
        return row

    def save(self, backup_dir: Path | None = ROOT / "scratch" / "workbook_backups") -> None:
        if not self.changed:
            return
        if backup_dir is not None and not self._backed_up:  # once per command, before its first write
            self._backed_up = True
            backup_dir.mkdir(parents=True, exist_ok=True)
            stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            shutil.copy2(self.path, backup_dir / f"{self.path.stem}.{stamp}.xlsx")
        data = dict(self._data)
        for file, xml in self._xml.items():
            data[file] = xml.encode("utf-8")
        data["xl/workbook.xml"] = _recalc_on_open(data["xl/workbook.xml"].decode("utf-8")).encode("utf-8")
        fd, tmp = tempfile.mkstemp(dir=self.path.parent, suffix=".xlsx")
        os.close(fd)
        try:
            with ZipFile(tmp, "w", ZIP_DEFLATED) as z:
                for info in self._infos:
                    z.writestr(info, data[info.filename])
            os.replace(tmp, self.path)
        finally:
            if os.path.exists(tmp):
                os.unlink(tmp)
        self._data = data
        self.changed = False

    # ------------------------------------------------------------ workbook-specific helpers
    def qubit_ids(self) -> list[str]:
        sheet, col, first, last = QUBIT_IDS
        return [_identifier(v) for v in self.column(sheet, col, first, last) if _identifier(v)]

    def settings(self, method: str) -> list[float | None]:
        return [self.get("Status", a) for a in SETTINGS[method]]

    def transpile(self) -> float | None:
        return self.get("Status", TRANSPILE)


def _identifier(value) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value).strip()


def _unescape(text: str) -> str:
    return text.replace("&lt;", "<").replace("&gt;", ">").replace("&quot;", '"').replace("&apos;", "'").replace("&amp;", "&")


def _recalc_on_open(xml: str) -> str:
    """Ask Excel to recompute formulas on open, since we don't update cached values."""
    m = re.search(r"<(\w+:)?calcPr\b([^>]*?)/?>", xml)
    if m:
        if "fullCalcOnLoad" in m.group(2):
            return xml
        return xml[:m.start()] + m.group(0).replace("calcPr", 'calcPr fullCalcOnLoad="1"', 1) + xml[m.end():]
    p = re.search(r"<(\w+:)?workbook\b", xml).group(1) or ""
    anchor = re.search(rf"</{p}definedNames>|</{p}sheets>", xml)
    return xml[:anchor.end()] + f'<{p}calcPr fullCalcOnLoad="1" />' + xml[anchor.end():]


def qubit_cell(qubit_id: str):
    """Write integer-looking qubit IDs as numbers (how people paste them into Qubits!A)."""
    return int(qubit_id) if re.fullmatch(r"-?\d+", qubit_id) else qubit_id
