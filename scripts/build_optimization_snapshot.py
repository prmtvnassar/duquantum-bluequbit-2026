"""Build a small, offline visualization snapshot from saved job receipts.

Reads JSON files only. This module has no SDK, subprocess, network, polling, or
simulation dependencies. Only explicitly allowed fields enter the snapshot.
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path


CASES = ("Duke_G4_4", "Duke_G4_0", "Duke_G4_19", "Duke_G3_0", "Duke_G2_9")
OPTION_KEYS = (
    "mps_bond_dimension",
    "pauli_path_truncation_threshold",
    "pauli_path_circuit_transpilation_level",
)
RECEIPT_KEYS = (
    "estimate", "status", "cost_usd", "compute_ms", "queue_ms",
    "requested_at", "updated_at",
)
QUOTE_KEYS = ("cost_usd", "runtime_seconds", "quoted_at", "binding_cost_cap")


def keep(source: dict, keys: tuple[str, ...]) -> dict:
    return {key: source[key] for key in keys if key in source}


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def build_snapshot(state_root: Path) -> dict:
    records = []
    for path in sorted((state_root / "remote_actions").glob("*.json")):
        raw = read_json(path)
        action = raw.get("action", {})
        if action.get("circuit_id") not in CASES:
            continue
        record = keep(raw, RECEIPT_KEYS)
        record["source_file"] = path.name
        record["action"] = {
            "circuit_id": action["circuit_id"],
            "device": action.get("device"),
            "options": keep(action.get("options", {}), OPTION_KEYS),
        }
        if isinstance(raw.get("quote"), dict):
            record["quote"] = keep(raw["quote"], QUOTE_KEYS)
        records.append(record)
    usage = read_json(state_root / "api_usage.json")
    batch = read_json(state_root / "batch_status.json")
    return {
        "schema_version": 1,
        "snapshot_at": datetime.now(timezone.utc).isoformat(),
        "source": "Saved local BlueQubit receipts",
        "ground_truth_available": False,
        "wallet_balance": None,
        "case_ids": list(CASES),
        "api_usage": keep(usage, (
            "observed_at", "known_cost_usd", "active_jobs", "job_count",
            "unknown_terminal_costs",
        )),
        "batch_status": keep(batch, (
            "updated_at", "status", "execution_timeout_seconds",
            "completed_target_rows", "required_target_rows",
        )),
        "receipts": records,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state-root", required=True, type=Path,
                        help="Directory containing remote_actions and saved status JSON")
    parser.add_argument("--output", type=Path,
                        default=Path(__file__).resolve().parents[1] / "reports" /
                        "optimization_visual_snapshot.json")
    parser.add_argument("--html", type=Path,
                        help="Optionally refresh only the embedded JSON of an existing visual")
    args = parser.parse_args()
    snapshot = build_snapshot(args.state_root)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(snapshot, indent=2) + "\n", encoding="utf-8")
    if args.html:
        fragment = args.html.read_text(encoding="utf-8")
        pattern = r'(<script type="application/json" id="bq-evidence-data">)[\s\S]*?(</script>)'
        safe_json = json.dumps(snapshot, separators=(",", ":")).replace("<", "\\u003c")
        updated, count = re.subn(pattern, lambda match: match[1] + safe_json + match[2], fragment)
        if count != 1:
            raise ValueError("Expected exactly one bq-evidence-data block")
        args.html.write_text(updated, encoding="utf-8", newline="\n")
    print(f"Saved {len(snapshot['receipts'])} receipt observations to {args.output}")


if __name__ == "__main__":
    main()
