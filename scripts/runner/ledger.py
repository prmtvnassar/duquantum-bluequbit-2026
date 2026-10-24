"""Append-only CSV record of every job event: the runner's cache and resume source.

The workbooks are what the team reads; the ledger is what the runner trusts. It is
plain text, so it merges in git and survives a damaged workbook.
"""

from __future__ import annotations

import csv
from datetime import datetime, timezone
from pathlib import Path

FIELDS = ["recorded_utc", "mode", "circuit", "qubit", "method", "setting", "transpile",
          "device", "job_key", "job_id", "status", "estimate", "wall_s", "credits", "error"]
TERMINAL = {"succeeded", "failed", "canceled"}


class Ledger:
    def __init__(self, path: Path):
        self.path = path

    def append(self, **row) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        new = not self.path.exists()
        with self.path.open("a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=FIELDS)
            if new:
                writer.writeheader()
            if not row.get("recorded_utc"):
                row["recorded_utc"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
            writer.writerow({k: "" if row.get(k) is None else row[k] for k in FIELDS})

    def rows(self) -> list[dict]:
        if not self.path.exists():
            return []
        with self.path.open(newline="", encoding="utf-8") as f:
            return list(csv.DictReader(f))

    def latest_by_job(self) -> dict[str, dict]:
        latest: dict[str, dict] = {}
        for row in self.rows():
            latest[row["job_id"]] = row
        return latest

    def succeeded(self, mode: str) -> dict[str, dict]:
        """job_key -> latest succeeded ledger row."""
        return {r["job_key"]: r for r in self.latest_by_job().values() if r["status"] == "succeeded" and r["mode"] == mode}

    def unfinished(self, mode: str) -> list[dict]:
        return [r for r in self.latest_by_job().values() if r["status"] not in TERMINAL and r["mode"] == mode]
