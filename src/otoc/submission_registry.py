"""Associate submission evidence with immutable uploaded bytes and provenance."""

import csv
import hashlib
import io
import json
import math
from pathlib import Path
import re

from bluequbit_samples.provenance import atomic_json
from .experiment_store import utc_now
from .duke_submission import build_submission, write_submission
from .ledger import DEFAULT_ROOT, REPO, atomic_bytes, csv_bytes, event, relative

POINTS = {"S1":100,"S2":100,"S3":100,"G1":300,"G2":600,"G3":800,"G4":1000}
EVIDENCE_SOURCES = ("browser_observed", "user_report")
NOTE_EVIDENCE = ("submitted_text", "prepared_explanation")
DEFAULT_OWNER = "original_submitter"


def _owner(value):
    owner = value.get("owner", DEFAULT_OWNER)
    if (not isinstance(owner, str) or len(owner) > 64
            or not re.fullmatch(r"[a-z0-9]+(?:[_-][a-z0-9]+)*", owner)):
        raise ValueError("Submission owner must be a safe lowercase slug")
    return owner


def _evidence(value):
    # Legacy attempt receipts were recorded from actual browser observations.
    source = value.get("evidence_source", "browser_observed")
    if source not in EVIDENCE_SOURCES:
        raise ValueError("Unknown submission evidence source")
    return {"evidence_source":source,
            "status":"USER_REPORTED" if source == "user_report" else "VERIFIED_BROWSER",
            "verification_note":(
                "The user reported this owner's upload, attempt number and displayed score; browser verification is pending."
                if source == "user_report" else
                "The submission and displayed score were observed on the official website."),
            "timestamp_note":"observed_at records when the evidence was recorded, not the actual upload time"}


def _note_evidence(value):
    source = value.get("note_evidence", "submitted_text")
    if source not in NOTE_EVIDENCE:
        raise ValueError("Unknown method explanation evidence")
    return {"note_evidence":source,
            "method_note_verification":(
                "Prepared method explanation; the exact text entered on the website has not been confirmed."
                if source == "prepared_explanation" else
                "This explanation is recorded as the text submitted on the website.")}


def _time_penalty(value):
    hours = value.get("time_penalty_hours")
    if hours is None:
        return None
    if (isinstance(hours, bool) or not isinstance(hours, (int, float))
            or not math.isfinite(hours) or hours < 0):
        raise ValueError("Time penalty hours must be a finite nonnegative number")
    return float(hours)


def _same_attempt(previous, proposed):
    immutable = ("problem", "attempt", "sha256", "method_note", "displayed_score", "points", "source")
    if (any(previous.get(key) != proposed.get(key) for key in immutable)
            or _owner(previous) != _owner(proposed)
            or _evidence(previous)["evidence_source"] != _evidence(proposed)["evidence_source"]
            or _note_evidence(previous)["note_evidence"] != _note_evidence(proposed)["note_evidence"]
            or _time_penalty(previous) != _time_penalty(proposed)):
        raise ValueError("Cannot replace a recorded attempt's file, score, time penalty, explanation, owner or evidence identity")


def record_submission(problem, attempt, csv_path, note, score, root="results/workflow", *,
                      evidence_source="browser_observed", owner=DEFAULT_OWNER,
                      note_evidence="submitted_text", time_penalty_hours=None,
                      repo=REPO, ledger_root=DEFAULT_ROOT):
    if problem not in POINTS or type(attempt) is not int or not 1 <= attempt <= 20:
        raise ValueError("Invalid submission identity")
    if (not isinstance(note, str) or not note.strip() or isinstance(score, bool)
            or not isinstance(score, (int, float)) or not math.isfinite(score)
            or not 0 <= score <= POINTS[problem]):
        raise ValueError("A method explanation and an observed valid score are required")
    owner = _owner({"owner":owner})
    evidence = _evidence({"evidence_source":evidence_source})
    note_metadata = _note_evidence({"note_evidence":note_evidence})
    penalty = _time_penalty({"time_penalty_hours":time_penalty_hours})
    prefix = "" if owner == DEFAULT_OWNER else owner + "-"
    path = Path(root) / "official_submissions" / f"{prefix}{problem}-{attempt:02d}.json"
    content = Path(csv_path).read_bytes()
    value = {"problem":problem, "attempt":attempt, "owner":owner,
             "csv_path":str(Path(csv_path).resolve()), "sha256":hashlib.sha256(content).hexdigest(),
             "method_note":note, "displayed_score":score, "points":POINTS[problem], "observed_at":utc_now(),
             "source":"https://app.bluequbit.io/hackathons/2GMaAenu3iSsIC6Z?tab=submissions",
             "precision_note":"UI display may round the official score; this is not a pointwise error bound",
             "time_penalty_hours":penalty,
             **evidence, **note_metadata}
    if path.exists():
        previous = json.loads(path.read_text(encoding="utf-8"))
        if time_penalty_hours is None:
            # Omission on an idempotent retry must not clear previously supplied evidence.
            value["time_penalty_hours"] = _time_penalty(previous)
        _same_attempt(previous, value)
        archive_submission(previous, repo=repo, ledger_root=ledger_root)
        return previous
    # Invalid provenance must not leave an official receipt or partially validated archive.
    archive_submission(value, repo=repo, ledger_root=ledger_root)
    atomic_json(path, value)
    return value


def archive_submission(value, repo=REPO, ledger_root=DEFAULT_ROOT):
    """Preserve submitted bytes with explicit owner, evidence and row provenance."""
    repo, ledger_root = Path(repo), Path(ledger_root)
    owner, evidence, note_metadata = _owner(value), _evidence(value), _note_evidence(value)
    penalty = _time_penalty(value)
    problem, attempt = value["problem"], value["attempt"]
    source = Path(value["csv_path"])
    payload = source.read_bytes()
    if hashlib.sha256(payload).hexdigest() != value["sha256"]:
        raise ValueError("The submitted file no longer matches its recorded checksum")
    template = next((repo / "problems").glob(f"*_{problem}/local_submission_template.csv"))
    build_submission(template, source)
    directory = repo / "submissions"
    if owner != DEFAULT_OWNER:
        directory = directory / "teammates" / owner
    target = directory / problem / f"attempt-{attempt:02d}.csv"
    note_path = target.with_suffix(".txt")
    note = (value["method_note"].strip() + "\n").encode("utf-8")
    if target.exists() and target.read_bytes() != payload:
        raise ValueError("Cannot alter the bytes of a recorded submission")
    if note_path.exists() and note_path.read_bytes() != note:
        raise ValueError("Cannot alter the explanation of a recorded submission")
    runs = [json.loads(p.read_text(encoding="utf-8")) for p in (ledger_root / "records").glob("*.json")]
    rows = list(csv.DictReader(io.StringIO(payload.decode("utf-8-sig"))))
    provenance = []
    for row in rows:
        matches = [r["run_id"] for r in runs if r.get("circuit_id") == row["circuit_id"]
                   and r.get("estimate") == float(row["value"])
                   and r.get("status") in {"SUCCEEDED", "COMPLETED"}
                   and r.get("finished_at") and r["finished_at"] <= value["observed_at"]]
        if not matches:
            raise ValueError(f"No recorded simulation supports submitted row {row['circuit_id']}")
        provenance.append({"circuit_id":row["circuit_id"], "value":float(row["value"]),
                           "supporting_run_ids":matches})
    archived = {**value, "owner":owner, **evidence, **note_metadata, "time_penalty_hours":penalty,
                "csv_path":relative(target),
                "method_note_path":relative(note_path), "row_provenance":provenance}
    receipt = target.with_suffix(".json")
    if receipt.exists():
        _same_attempt(json.loads(receipt.read_text(encoding="utf-8")), archived)
    # All semantic validation precedes any new archive file or official receipt.
    write_submission(payload, target, immutable=True)
    write_submission(note, note_path, immutable=True)
    if not receipt.exists():
        atomic_json(receipt, archived)
        event("official_submission", {"problem":problem, "attempt":attempt, "owner":owner,
                                      "sha256":value["sha256"], "displayed_score":value["displayed_score"],
                                      "evidence_source":evidence["evidence_source"], "status":evidence["status"],
                                      "note_evidence":note_metadata["note_evidence"],
                                      "time_penalty_hours":penalty,
                                      "receipt":relative(receipt)}, ledger_root)
    rebuild_submission_index(repo=repo, ledger_root=ledger_root)
    return archived


SUBMISSION_FIELDS = ("owner","problem","attempt","status","displayed_score",
                     "reported_score_fraction","points","observed_at","sha256","csv_path",
                     "method_note_path","source","evidence_source","note_evidence",
                     "time_penalty_hours","upload_bytes_verified","score_evidence_source",
                     "score_evidence_path","score_evidence_commit","receipt_path")


def rebuild_submission_index(repo=REPO, ledger_root=DEFAULT_ROOT):
    """Rebuild the CSV from saved claims, including scores and unresolved uploads.

    The source receipts remain authoritative. A hash here identifies the saved
    candidate, not necessarily the exact bytes uploaded to the website. Missing
    account, attempt, score, or upload identity stays blank rather than inferred.
    This function only reads local files and writes the derived CSV index.
    """
    repo, ledger_root = Path(repo).resolve(), Path(ledger_root)
    submissions = repo / "submissions"
    rows = []

    def source_path(path):
        return path.relative_to(repo).as_posix()

    def portable(path):
        return str(path).replace("\\", "/") if path else ""

    def explicit_upload_verification(value):
        for key in ("exact_uploaded_bytes_verified", "uploaded_bytes_independently_verified",
                    "uploaded_bytes_verified"):
            if key in value:
                return value[key]
        return ""

    for path in sorted(submissions.rglob("attempt-*.json")):
        value = json.loads(path.read_text(encoding="utf-8"))
        evidence, note = _evidence(value), _note_evidence(value)
        rows.append({**value, "owner":_owner(value), "status":evidence["status"],
                     "evidence_source":evidence["evidence_source"],
                     "score_evidence_source":evidence["evidence_source"],
                     "note_evidence":note["note_evidence"],
                     "time_penalty_hours":_time_penalty(value),
                     "csv_path":portable(value.get("csv_path")),
                     "method_note_path":portable(value.get("method_note_path")),
                     "upload_bytes_verified":explicit_upload_verification(value),
                     "receipt_path":source_path(path)})

    for path in sorted((submissions / "teammates").glob("*/*/submitted-*.json")):
        value = json.loads(path.read_text(encoding="utf-8"))
        score = value.get("reported_displayed_score")
        if score is None:
            score = value.get("observed_displayed_score")
        note_path = value.get("method_note_path")
        if not note_path and path.with_suffix(".txt").exists():
            note_path = source_path(path.with_suffix(".txt"))
        rows.append({"owner":value.get("owner", ""), "problem":value["problem"],
                     "attempt":value.get("attempt"),
                     "status":value.get("submission_status") or "REPORTED_BY_TEAMMATE",
                     "displayed_score":score,
                     "reported_score_fraction":value.get("reported_score_fraction"),
                     "points":value.get("maximum_points"),
                     "observed_at":value.get("observed_at"),
                     "sha256":value.get("sha256"),
                     "csv_path":portable(value.get("csv_path")),
                     "method_note_path":portable(note_path),
                     "source":value.get("source_commit"),
                     "evidence_source":"teammate_report",
                     "score_evidence_source":"teammate_report",
                     "note_evidence":"prepared_explanation" if note_path else "",
                     "time_penalty_hours":value.get("time_penalty_hours"),
                     "upload_bytes_verified":explicit_upload_verification(value),
                     "receipt_path":source_path(path)})

    for path in sorted(submissions.glob("*/user-reported-submission.json")):
        value = json.loads(path.read_text(encoding="utf-8"))
        rows.append({"owner":value.get("owner", DEFAULT_OWNER),
                     "problem":value["problem"], "attempt":value.get("attempt"),
                     "status":value.get("status", "SUBMITTED_USER_REPORTED"),
                     "displayed_score":value.get("score"), "points":POINTS[value["problem"]],
                     "source":value.get("source"), "evidence_source":"user_report",
                     "upload_bytes_verified":explicit_upload_verification(value),
                     "receipt_path":source_path(path)})

    for path in sorted((submissions / "candidates").glob("*/*.feedback.json")):
        value = json.loads(path.read_text(encoding="utf-8"))
        if not (value.get("submission_status") in {"USER_CONFIRMED_SUBMITTED", "REPORTED_SUBMITTED"}
                or value.get("accepted_grading") is True):
            continue
        score = value.get("score")
        if score is None:
            score = value.get("reported_displayed_score")
        candidate_path = portable(value.get("candidate_csv"))
        note_path = Path(candidate_path).with_suffix(".txt") if candidate_path else None
        note_path = note_path.as_posix() if note_path and (repo / note_path).exists() else ""
        rows.append({"owner":value.get("account_owner") or value.get("owner") or "",
                     "problem":value["problem"], "attempt":value.get("attempt"),
                     "status":value.get("submission_status") or "USER_REPORTED_ACCEPTED",
                     "displayed_score":score,
                     "points":value.get("maximum_points", POINTS[value["problem"]]),
                     "observed_at":value.get("recorded_at"),
                     "sha256":value.get("candidate_sha256"), "csv_path":candidate_path,
                     "method_note_path":note_path,
                     "source":value.get("source_commit"),
                     "evidence_source":value.get("submission_evidence_source") or
                         value.get("evidence_source", "user_report"),
                     "score_evidence_source":value.get("score_evidence_source") or
                         value.get("evidence_source", "user_report"),
                     "score_evidence_path":portable(value.get("score_report_path") or
                                                     value.get("score_source_path") or
                                                     value.get("source_path")),
                     "score_evidence_commit":value.get("score_source_commit"),
                     "note_evidence":"prepared_explanation" if note_path else "",
                     "time_penalty_hours":value.get("time_penalty_hours"),
                     "upload_bytes_verified":explicit_upload_verification(value),
                     "receipt_path":source_path(path)})

    order = {problem:i for i, problem in enumerate(POINTS)}
    rows.sort(key=lambda row:(order[row["problem"]], str(row.get("owner") or ""),
                              str(row.get("attempt") or "").zfill(2), row["receipt_path"]))
    atomic_bytes(ledger_root / "submissions.csv", csv_bytes(SUBMISSION_FIELDS, rows))
    return len(rows)


def sync_submissions(root="results/workflow", *, repo=REPO, ledger_root=DEFAULT_ROOT):
    count = 0
    for path in sorted((Path(root)/"official_submissions").glob("*.json")):
        archive_submission(json.loads(path.read_text(encoding="utf-8")), repo=repo,
                           ledger_root=ledger_root)
        count += 1
    rebuild_submission_index(repo=repo, ledger_root=ledger_root)
    return count
