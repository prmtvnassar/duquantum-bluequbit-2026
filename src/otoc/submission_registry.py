"""Associate observed official scores with the exact submitted bytes and note."""

import hashlib
import json
import math
from pathlib import Path
import csv
from bluequbit_samples.provenance import atomic_json
from .experiment_store import utc_now
from .duke_submission import build_submission, write_submission
from .ledger import DEFAULT_ROOT, REPO, atomic_bytes, csv_bytes, event, relative

POINTS = {"S1":100,"S2":100,"S3":100,"G1":300,"G2":600,"G3":800,"G4":1000}


def record_submission(problem, attempt, csv_path, note, score, root="results/workflow"):
    if problem not in POINTS or not 1 <= attempt <= 20:
        raise ValueError("Invalid submission identity")
    if not note.strip() or not math.isfinite(score) or not 0 <= score <= POINTS[problem]:
        raise ValueError("A method explanation and an observed valid score are required")
    path=Path(root)/"official_submissions"/f"{problem}-{attempt:02d}.json"
    content=Path(csv_path).read_bytes()
    value={"problem":problem,"attempt":attempt,"csv_path":str(Path(csv_path).resolve()),
           "sha256":hashlib.sha256(content).hexdigest(),"method_note":note,
           "displayed_score":score,"points":POINTS[problem],"observed_at":utc_now(),
           "source":"https://app.bluequbit.io/hackathons/2GMaAenu3iSsIC6Z?tab=submissions",
           "precision_note":"UI display may round the official score; this is not a pointwise error bound"}
    if path.exists():
        previous=json.loads(path.read_text())
        if previous["sha256"]!=value["sha256"]:
            raise ValueError("A different file is already recorded for this attempt")
        archive_submission(previous)
        return previous
    atomic_json(path,value)
    archive_submission(value)
    return value


def archive_submission(value, repo=REPO, ledger_root=DEFAULT_ROOT):
    """Preserve the bytes actually uploaded, explanation, score, and row provenance."""
    repo, ledger_root = Path(repo), Path(ledger_root)
    problem, attempt = value["problem"], value["attempt"]
    source = Path(value["csv_path"])
    payload = source.read_bytes()
    if hashlib.sha256(payload).hexdigest() != value["sha256"]:
        raise ValueError("The submitted file no longer matches its recorded checksum")
    template = next((repo / "problems").glob(f"*_{problem}/local_submission_template.csv"))
    build_submission(template, source)
    target = repo / "submissions" / problem / f"attempt-{attempt:02d}.csv"
    write_submission(payload, target, immutable=True)
    note_path = target.with_suffix(".txt")
    note = (value["method_note"].strip() + "\n").encode()
    if note_path.exists() and note_path.read_bytes() != note:
        raise ValueError("Cannot alter the explanation of a recorded submission")
    atomic_bytes(note_path, note)
    runs = [json.loads(p.read_text()) for p in (ledger_root / "records").glob("*.json")]
    with target.open(newline="") as stream:
        rows = list(csv.DictReader(stream))
    provenance = []
    for row in rows:
        matches = [r["run_id"] for r in runs if r["circuit_id"] == row["circuit_id"]
                   and r.get("estimate") == float(row["value"])
                   and (r.get("finished_at") or "") <= value["observed_at"]]
        if not matches:
            raise ValueError(f"No recorded simulation supports submitted row {row['circuit_id']}")
        provenance.append({"circuit_id":row["circuit_id"], "value":float(row["value"]), "supporting_run_ids":matches})
    archived = {**value, "csv_path":relative(target), "method_note_path":relative(note_path),
                "row_provenance":provenance}
    receipt = target.with_suffix(".json")
    if receipt.exists():
        prior = json.loads(receipt.read_text())
        if any(prior[k] != archived[k] for k in ("sha256","method_note","displayed_score","attempt")):
            raise ValueError("Cannot replace an observed submission receipt")
    else:
        atomic_json(receipt, archived)
        event("official_submission", {"problem":problem, "attempt":attempt, "sha256":value["sha256"],
                                      "displayed_score":value["displayed_score"], "receipt":relative(receipt)}, ledger_root)
    submissions = [{"owner":"original_submitter","status":"VERIFIED_BROWSER",**json.loads(p.read_text())}
                   for p in (repo / "submissions").glob("*/attempt-*.json")]
    for p in (repo / "submissions/teammates").glob("*/*/submitted-*.json"):
        external=json.loads(p.read_text())
        submissions.append({**external,"points":external["maximum_points"],"displayed_score":"",
                            "method_note_path":relative(p.with_suffix(".txt")),"status":"REPORTED_BY_TEAMMATE",
                            "source":external["source_commit"],"attempt":""})
    fields = ("owner","problem","attempt","status","displayed_score","reported_score_fraction","points","observed_at","sha256","csv_path","method_note_path","source")
    atomic_bytes(ledger_root / "submissions.csv", csv_bytes(fields, sorted(submissions,key=lambda v:(v["problem"],v["attempt"]))))
    return archived


def sync_submissions(root="results/workflow"):
    count = 0
    for path in sorted((Path(root)/"official_submissions").glob("*.json")):
        archive_submission(json.loads(path.read_text()))
        count += 1
    return count
