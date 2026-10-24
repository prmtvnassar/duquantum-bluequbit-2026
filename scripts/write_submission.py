"""Write one circuit's submission CSV from the runner's ledger.

Format (challenge page): rows `circuit_id,value`, one per ID (Duke_<C>_<q>), optional header.
Output: submissions/<circuit>_v<N>.csv, N = next free version (team convention).

Examples:
    python scripts/write_submission.py S1 --method exact
    python scripts/write_submission.py G2 --method mps --setting 128
    python scripts/write_submission.py G2 --method pps --setting 0.001 --transpile 2
"""

from __future__ import annotations

import argparse
import csv
import math
import re
import sys

from runner.config import ROOT, circuit_config, get_client, load_config
from runner.core import ledger_for
from runner.targets import Context, build_targets


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("circuit", help="circuit name from scripts/runner.toml, e.g. S1")
    ap.add_argument("--method", choices=("exact", "mps", "pps"), required=True)
    ap.add_argument("--setting", type=float, help="χ (mps) or ε (pps)")
    ap.add_argument("--transpile", type=int, default=None, help="pps transpilation level (default: any)")
    ap.add_argument("--offline", action="store_true", help="read the offline test ledger")
    args = ap.parse_args()
    if args.method != "exact" and args.setting is None:
        ap.error("--setting is required for mps/pps")

    cfg = load_config()
    c = circuit_config(cfg, args.circuit)
    targets = build_targets(args.circuit, c, Context(cfg, get_client, lambda _: []))
    ids = {t.qubit: (t.circuit if isinstance(t.circuit, str) else f"{c.get('official_id', args.circuit)}_{t.qubit}")
           for t in targets}

    values: dict[str, float] = {}
    for row in ledger_for(args.offline).latest_by_job().values():
        if row["circuit"] != args.circuit or row["method"] != args.method or row["status"] != "succeeded":
            continue
        if args.method != "exact" and float(row["setting"]) != args.setting:
            continue
        if args.transpile is not None and row["transpile"] not in ("", str(args.transpile)):
            continue
        values[row["qubit"]] = float(row["estimate"])  # later rows win

    missing = [q for q in ids if q not in values]
    if missing:
        sys.exit(f"Missing {len(missing)} of {len(ids)} qubits for this method/setting: {missing[:10]}")
    if any(not math.isfinite(values[q]) for q in ids):
        sys.exit("Non-finite value; the upload would reject it")
    if len({values[q] for q in ids}) == 1:
        sys.exit("All values are equal, which scores 0")

    name = c.get("official_id", args.circuit)
    out_dir = ROOT / "submissions"
    out_dir.mkdir(exist_ok=True)
    taken = [int(m.group(1)) for p in out_dir.glob(f"{name}_v*.csv") if (m := re.fullmatch(rf"{re.escape(name)}_v(\d+)\.csv", p.name))]
    path = out_dir / f"{name}_v{max(taken, default=0) + 1}.csv"
    with path.open("x", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["circuit_id", "value"])
        for q in sorted(ids, key=lambda q: int(q) if q.isdigit() else q):
            w.writerow([ids[q], repr(values[q])])
    setting = "" if args.method == "exact" else f" {args.setting:g}"
    print(f"Wrote {len(ids)} rows to {path.relative_to(ROOT)}")
    print(f"Suggested method note: {args.method.upper()}{setting} via BlueQubit"
          f"{' (exact statevector)' if args.method == 'exact' else ''}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
