"""Serial observable-list (all_z) feature jobs through the audited adapter.

One job at a time under the sole ``remote_runner`` lock, through the unchanged
``BlueQubitAdapter.run`` gates (fresh quote, cost gate, STOP, per-job timeout).
IDs that already hold a COMPLETED receipt for the identical action are skipped
without any API call.  One JSON line per ID is appended to ``--log``.  The
first BLOCKED, cancelled, failed, invalid or unknown-cost outcome stops the
run with a non-zero exit so the operator reconciles before continuing.
"""

import argparse
import json
import logging
from pathlib import Path

from otoc.bluequbit_adapter import SIZES, BlueQubitAdapter, observable_pauli_sums
from otoc.calibration import load_settings
from otoc.experiment_store import ExperimentStore, digest, utc_now


def normalize_ids(problem, ids):
    """Accept ``Duke_G4_5`` or bare ``5``; keep order, refuse duplicates/foreign IDs."""
    normalized = []
    for raw in ids:
        cid = raw if str(raw).startswith("Duke_") else f"Duke_{problem}_{raw}"
        if cid.split("_")[1] != problem or cid in normalized:
            raise ValueError(f"ID {raw!r} is not a distinct {problem} circuit ID")
        normalized.append(cid)
    if not normalized:
        raise ValueError("At least one circuit ID is required")
    return normalized


def feature_action(cid, device, options, observables):
    problem, z, _ = observable_pauli_sums(cid, device, options, observables)
    return {"circuit_id": cid, "device": device, "options": options, "pauli": z, "observables": observables}


def run_feature_jobs(adapter, settings, problem, device, options, ids, observables, justification, log_path):
    """Return ``(exit_code, entries)``; entries mirror the JSON lines written to ``log_path``."""
    root = Path(adapter.root)
    log_path = Path(log_path)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    entries = []
    if not str(justification).strip():
        raise ValueError("A nonempty --justification is required for graded actions")
    actions = [feature_action(cid, device, options, observables) for cid in normalize_ids(problem, ids)]

    def log(entry):
        entry = {"recorded_at": utc_now(), "problem": problem, "device": device, "options": options,
                 "observables": observables, **entry}
        with log_path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(entry, sort_keys=True, allow_nan=False) + "\n")
        entries.append(entry)
        return entry

    with ExperimentStore(root).lock("remote_runner"):
        for action in actions:
            cid, key = action["circuit_id"], digest(action)
            path = root / "remote_actions" / f"{key}.json"
            if path.exists():
                saved = json.loads(path.read_text(encoding="utf-8"))
                if saved.get("status") == "COMPLETED":
                    log({"circuit_id": cid, "action_key": key, "status": "SKIPPED_COMPLETED",
                         "job_id": saved.get("job_id"), "estimate": saved.get("estimate"),
                         "cost_usd": saved.get("cost_usd"),
                         "vector_length": len(saved["estimates_vector"]) if isinstance(saved.get("estimates_vector"), list) else None})
                    continue
            if (root / "STOP").exists():
                log({"circuit_id": cid, "action_key": key, "status": "BLOCKED_STOP", "reason": "stop_file"})
                return 1, entries
            try:
                saved = adapter.run(cid, device, options, settings, justification, observables=observables)
            except Exception as exc:
                # SDK exception bodies may hold sensitive data; keep the type only.
                log({"circuit_id": cid, "action_key": key, "status": "ERROR", "error": type(exc).__name__})
                return 1, entries
            status = saved.get("status")
            vector = saved.get("estimates_vector")
            log({"circuit_id": cid, "action_key": key, "status": status, "job_id": saved.get("job_id"),
                 "estimate": saved.get("estimate"), "cost_usd": saved.get("cost_usd"),
                 "compute_ms": saved.get("compute_ms"), "queue_ms": saved.get("queue_ms"),
                 "reason": saved.get("reason") or saved.get("error"),
                 "quote_usd": (saved.get("quote") or {}).get("cost_usd"),
                 "vector_length": len(vector) if isinstance(vector, list) else None})
            if status != "COMPLETED" or saved.get("cost_usd") is None:
                return 1, entries
    return 0, entries


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="configs/workflow_final.json")
    parser.add_argument("--problem", choices=sorted(SIZES), required=True)
    parser.add_argument("--device", choices=["mps.cpu", "mps.gpu"], required=True)
    parser.add_argument("--options-file", type=Path, required=True, help="JSON object with every native option, e.g. configs/cohorts/mps_chi32.json")
    parser.add_argument("--observables", choices=["all_z"], required=True)
    parser.add_argument("--ids", nargs="+", required=True, help="Circuit IDs (Duke_G4_5) or bare qubit indices (5)")
    parser.add_argument("--timeout", type=float, required=True, help="Per-job cap in seconds (quoted runtime and cancellation)")
    parser.add_argument("--justification", required=True)
    parser.add_argument("--log", type=Path, required=True, help="Append one JSON line per ID here")
    parser.add_argument("--execute", action="store_true", help="Required; no network calls without this flag")
    args = parser.parse_args()
    if not args.execute:
        parser.error("Execution requires --execute; review the IDs, options and timeout first")
    if not args.justification.strip():
        parser.error("--justification must be nonempty")
    if not 1 <= args.timeout <= 7200:
        parser.error("--timeout must be within 1..7200 seconds")
    settings = load_settings(args.config)
    settings["per_job_seconds"] = args.timeout
    options = json.loads(args.options_file.read_text(encoding="utf-8-sig"))
    logging.disable(logging.CRITICAL)
    code, entries = run_feature_jobs(BlueQubitAdapter(), settings, args.problem, args.device, options,
                                     args.ids, args.observables, args.justification, args.log)
    print(json.dumps({"exit_code": code, "jobs": entries}, indent=2), flush=True)
    return code


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(json.dumps({"status": "BLOCKED", "reason": "entrypoint_exception:" + type(exc).__name__}))
        raise SystemExit(1)
