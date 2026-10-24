"""Import the reviewed collaborator ledger and exact G1 anchor without rerunning jobs."""
import csv
import hashlib
import io
import json
import math
from pathlib import Path
import subprocess

from bluequbit_samples.provenance import atomic_json
from otoc.bluequbit_adapter import SIZES, validate_action
from otoc.duke_submission import build_submission, write_submission
from otoc.ledger import atomic_bytes, event, record_run


def main():
    ref="origin/kevin/experiment"
    commit=subprocess.check_output(["git","rev-parse",ref],text=True).strip()
    root=Path("runs/imports/kevin")
    def blob(path):
        return subprocess.check_output(["git","show",f"{commit}:{path}"])
    raw=blob("runs/ledger.csv")
    archive=root/"original_ledger.csv"
    write_submission(raw,archive,immutable=True)
    rows=list(csv.DictReader(io.StringIO(raw.decode())))
    latest, first={},{}
    for row in rows:
        if row["mode"]!="cloud":
            raise ValueError("Synthetic/offline data cannot be imported as cloud evidence")
        latest[row["job_id"]]=row
        first.setdefault(row["job_id"],row)
    g1=[]
    for job_id,row in latest.items():
        problem,q=row["circuit"],int(row["qubit"])
        cid=f"Duke_{problem}_{q}"
        if problem not in SIZES or not 0<=q<SIZES[problem]:
            raise ValueError("Unknown collaborator target")
        if row["method"]!="exact" or row["device"]!="cpu":
            raise ValueError("Review new collaborator methods before importing")
        value=float(row["estimate"]) if row["estimate"] else None
        if value is not None and (not math.isfinite(value) or abs(value)>1+1e-8):
            raise ValueError("Invalid collaborator estimate")
        status={"succeeded":"COMPLETED","failed":"FAILED","canceled":"CANCELED","running":"UNRESOLVED_IMPORTED"}[row["status"]]
        record_run("kevin-"+job_id,{"circuit_id":cid,"problem":problem,"qubit":q,
            "origin":"collaborator_kevin","account_scope":"collaborator; not current API account",
            "method":"exact","backend":"cpu","parameters":{},"status":status,"estimate":value,
            "cost_usd":float(row["credits"]) if row["credits"] else None,
            "wall_seconds":float(row["wall_s"]) if row["wall_s"] else None,"job_id":job_id,
            "started_at":first[job_id]["recorded_utc"],"finished_at":row["recorded_utc"],
            "reason":"Reviewed exact by-ID CPU results imported from kevin/experiment",
            "error":row["error"],"source_commit":commit,"source_ledger":str(archive)})
        if problem=="G1" and status=="COMPLETED":
            _,pauli=validate_action(cid,"cpu",{})
            g1.append({"action":{"circuit_id":cid,"device":"cpu","options":{},"pauli":pauli},
                       "status":"COMPLETED","estimate":value,"cost_usd":float(row["credits"]),
                       "job_id":job_id,"compute_ms":1000*float(row["wall_s"]),"updated_at":row["recorded_utc"],
                       "origin":"collaborator_kevin","source_commit":commit,
                       "scheduler_justification":"Reuse exact G1 outputs; no duplicate simulation needed"})
    if len(g1)!=30 or len({r["action"]["circuit_id"] for r in g1})!=30:
        raise ValueError("Collaborator ledger does not supply 30 distinct exact G1 results")
    csv_path=Path("submissions/teammates/kevin/G1/submitted-v1.csv")
    payload=blob("submissions/G1_v1.csv")
    write_submission(payload,csv_path,immutable=True)
    build_submission(Path("problems/04_graded_G1/local_submission_template.csv"),csv_path)
    submitted={r["circuit_id"]:float(r["value"]) for r in csv.DictReader(io.StringIO(payload.decode()))}
    with Path("problems/04_graded_G1/exact_values.csv").open(newline="") as stream:
        current={r["circuit_id"]:float(r["value"]) for r in csv.DictReader(stream)}
    if submitted!=current or submitted!={r["action"]["circuit_id"]:r["estimate"] for r in g1}:
        raise ValueError("G1 upload, main exact values and source job ledger disagree")
    atomic_json(root/"g1_exact_actions.json",{"source_commit":commit,"records":g1})
    note=("Ran all 30 stored Duke_G1_q programs separately on BlueQubit's exact CPU statevector backend, "
          "starting in |0...0>. Evaluated Z on each ID's target q; q0 is rightmost in the Pauli string. "
          "Used completed direct expectation values with no MPS/PPS truncation, fitting or fusion. "
          "The source ledger reports $0 cost for every successful G1 job.")
    atomic_bytes(csv_path.with_suffix(".txt"),(note+"\n").encode())
    atomic_json(csv_path.with_suffix(".json"),{"problem":"G1","owner":"kevin","source_commit":commit,
        "csv_path":str(csv_path),"sha256":hashlib.sha256(payload).hexdigest(),"submission_status":"REPORTED_SUBMITTED",
        "reported_score_fraction":1.0,"maximum_points":300,"observed_displayed_score":None,"attempt":None,
        "score_evidence":"User statement, source commit and main README report 100%; website not independently checked",
        "method_note":note,"method_note_origin":"Reconstructed from reviewed runner code/config; original website wording unavailable",
        "row_provenance":[{"circuit_id":r["action"]["circuit_id"],"run_id":"kevin-"+r["job_id"]} for r in g1]})
    manifest={"source_branch":ref,"commit":commit,"source_files":{},"jobs":len(latest),"g1_successes":len(g1)}
    for name in ("scripts/runner/backends.py","scripts/runner/targets.py","scripts/runner.toml","runs/ledger.csv","submissions/G1_v1.csv"):
        manifest["source_files"][name]=hashlib.sha256(blob(name)).hexdigest()
    marker=root/"source_manifest.json"
    if not marker.exists():
        for row in rows:
            event("collaborator_job_event",{"source_commit":commit,"original_event":row})
        event("collaborator_submission",{"problem":"G1","owner":"kevin","reported_score_fraction":1.0,
                                         "receipt":str(csv_path.with_suffix('.json'))})
    atomic_json(marker,manifest)
    print(json.dumps(manifest,indent=2))


if __name__=="__main__":
    main()
