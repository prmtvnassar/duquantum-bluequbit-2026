import csv
import hashlib
from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import runpy
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from otoc.submission_registry import archive_submission, rebuild_submission_index, record_submission


class SubmissionRegistryTests(TestCase):
    def setUp(self):
        temporary = TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.repo = Path(temporary.name)
        self.workflow = self.repo / "workflow"
        self.ledger = self.repo / "runs"
        self.source = self.repo / "candidate.csv"
        self.source.write_text("circuit_id,value\nDuke_G2_0,0.25\nDuke_G2_1,-0.125\n", encoding="utf-8")
        template = self.repo / "problems/05_graded_G2/local_submission_template.csv"
        template.parent.mkdir(parents=True)
        template.write_text("circuit_id,value\nDuke_G2_0,\nDuke_G2_1,\n", encoding="utf-8")
        (self.ledger / "records").mkdir(parents=True)
        for q, value in enumerate((0.25, -0.125)):
            (self.ledger / "records" / f"run-{q}.json").write_text(json.dumps({
                "run_id":f"run-{q}", "circuit_id":f"Duke_G2_{q}", "estimate":value,
                "status":"COMPLETED", "finished_at":"2026-10-24T12:00:00+00:00"}), encoding="utf-8")
        clock = patch("otoc.submission_registry.utc_now", return_value="2026-10-24T20:00:00+00:00")
        clock.start()
        self.addCleanup(clock.stop)

    def record(self, **overrides):
        args = dict(problem="G2", attempt=1, csv_path=self.source, note="Native CPU MPS chi32.", score=498,
                    root=self.workflow, repo=self.repo, ledger_root=self.ledger)
        args.update(overrides)
        return record_submission(**args)

    def index(self):
        with (self.ledger / "submissions.csv").open(encoding="utf-8", newline="") as stream:
            return list(csv.DictReader(stream))

    def archive_path(self, owner=None):
        base = self.repo / "submissions"
        if owner:
            base = base / "teammates" / owner
        return base / "G2/attempt-01.json"

    def test_user_reported_teammate_is_separate_from_current_submitter(self):
        receipt = self.record(evidence_source="user_report", owner="teammate_reported")
        self.assertEqual(receipt["status"], "USER_REPORTED")
        self.assertEqual(receipt["evidence_source"], "user_report")
        self.assertIn("browser verification is pending", receipt["verification_note"])
        self.assertIn("not the actual upload time", receipt["timestamp_note"])
        self.assertNotIn("uploaded_at", receipt)
        self.assertTrue(receipt["source"].startswith("https://app.bluequbit.io/"))
        archived = json.loads(self.archive_path("teammate_reported").read_text())
        self.assertEqual(len(archived["row_provenance"]), 2)
        self.assertEqual(archived["owner"], "teammate_reported")
        self.assertTrue((self.workflow / "official_submissions/teammate_reported-G2-01.json").exists())
        self.assertFalse((self.workflow / "official_submissions/G2-01.json").exists())
        self.assertFalse(self.archive_path().exists())
        indexed = self.index()[0]
        self.assertEqual((indexed["owner"], indexed["status"], indexed["displayed_score"]),
                         ("teammate_reported", "USER_REPORTED", "498"))

    def test_browser_default_and_matching_attempt_numbers_do_not_collide(self):
        current = self.record()
        teammate = self.record(owner="teammate_reported", evidence_source="user_report", score=497)
        self.assertEqual(current["status"], "VERIFIED_BROWSER")
        self.assertEqual(teammate["status"], "USER_REPORTED")
        self.assertTrue(self.archive_path().exists())
        self.assertTrue(self.archive_path("teammate_reported").exists())
        self.assertEqual({row["owner"] for row in self.index()}, {"original_submitter", "teammate_reported"})

    def test_cleanup_keeps_distinct_claims_without_recreating_duplicate_bytes(self):
        self.record(score=342, evidence_source="user_report")
        teammate = self.record(owner="teammate_reported", evidence_source="user_report")
        receipt_path = self.archive_path("teammate_reported")
        receipt_bytes = receipt_path.read_bytes()
        retired = {}
        for extension in ("csv", "txt"):
            duplicate = receipt_path.with_suffix("." + extension)
            canonical = self.archive_path().with_suffix("." + extension)
            self.assertEqual(duplicate.read_bytes(), canonical.read_bytes())
            retired[duplicate.relative_to(self.repo).as_posix()] = {
                "retained_path":canonical.relative_to(self.repo).as_posix(),
                "match":"byte_identical",
                "sha256":hashlib.sha256(duplicate.read_bytes()).hexdigest()}
            duplicate.unlink()
        (self.repo / "submissions/retention.json").write_text(json.dumps({"retired_files":retired}))
        old = json.loads(receipt_bytes)
        archive_submission(old, repo=self.repo, ledger_root=self.ledger)
        self.record(owner="teammate_reported", evidence_source="user_report")
        self.assertEqual(receipt_path.read_bytes(), receipt_bytes)
        self.assertFalse(receipt_path.with_suffix(".csv").exists())
        self.assertFalse(receipt_path.with_suffix(".txt").exists())
        rows = {row["owner"]:row for row in self.index()}
        self.assertEqual(rows["original_submitter"]["displayed_score"], "342")
        self.assertEqual(rows["teammate_reported"]["displayed_score"], "498")
        self.assertEqual(rows["original_submitter"]["csv_path"], rows["teammate_reported"]["csv_path"])
        canonical.write_text("changed explanation")
        with self.assertRaisesRegex(ValueError, "no longer matches"):
            archive_submission(old, repo=self.repo, ledger_root=self.ledger)

    def test_cleanup_never_substitutes_numerically_equal_different_upload_bytes(self):
        self.record(owner="teammate_reported", evidence_source="user_report")
        receipt_path = self.archive_path("teammate_reported")
        value = json.loads(receipt_path.read_text())
        duplicate = receipt_path.with_suffix(".csv")
        duplicate.unlink()
        (self.repo / "submissions/retention.json").write_text(json.dumps({"retired_files":{
            duplicate.relative_to(self.repo).as_posix():{"match":"numeric_equivalent",
                "retained_path":"candidate.csv"}}}))
        with self.assertRaises(FileNotFoundError):
            archive_submission(value, repo=self.repo, ledger_root=self.ledger)

    def test_original_score_and_time_penalty_leave_teammate_receipt_unchanged(self):
        self.record(owner="teammate_reported", evidence_source="user_report")
        teammate_path = self.archive_path("teammate_reported")
        teammate_bytes = teammate_path.read_bytes()
        receipt = self.record(score=342, time_penalty_hours=3.48, evidence_source="user_report")
        self.assertEqual(receipt["displayed_score"], 342)
        self.assertEqual(receipt["time_penalty_hours"], 3.48)
        self.assertEqual(json.loads(self.archive_path().read_text())["time_penalty_hours"], 3.48)
        self.assertEqual(teammate_path.read_bytes(), teammate_bytes)
        indexed = {row["owner"]:row for row in self.index()}
        self.assertEqual(indexed["original_submitter"]["time_penalty_hours"], "3.48")
        self.assertEqual(indexed["teammate_reported"]["displayed_score"], "498")
        self.assertEqual(indexed["teammate_reported"]["time_penalty_hours"], "")

    def test_recorded_time_penalty_is_immutable_and_omitted_retry_preserves_it(self):
        receipt = self.record(time_penalty_hours=3.48)
        self.assertEqual(self.record(), receipt)
        self.assertEqual(self.record(time_penalty_hours=3.48), receipt)
        for changed in (0, 3.49):
            with self.subTest(changed=changed), self.assertRaisesRegex(ValueError, "Cannot replace"):
                self.record(time_penalty_hours=changed)
        for changed in (None, 3.49):
            with self.subTest(archive_changed=changed), self.assertRaisesRegex(ValueError, "Cannot replace"):
                archive_submission({**receipt, "time_penalty_hours":changed}, repo=self.repo, ledger_root=self.ledger)

    def test_invalid_time_penalties_fail_before_writing(self):
        for hours in (-1, float("nan"), float("inf"), float("-inf"), True, "3.48"):
            with self.subTest(hours=hours), self.assertRaisesRegex(ValueError, "Time penalty"):
                self.record(time_penalty_hours=hours)
        self.assertFalse((self.repo / "submissions").exists())
        self.assertFalse((self.workflow / "official_submissions").exists())
        self.assertEqual(self.record(time_penalty_hours=0)["time_penalty_hours"], 0.0)

    def test_legacy_browser_receipts_keep_default_identity_and_remain_immutable(self):
        original = self.record()
        workflow_path = self.workflow / "official_submissions/G2-01.json"
        for path in (workflow_path, self.archive_path()):
            value = json.loads(path.read_text())
            for key in ("owner", "evidence_source", "status", "verification_note", "timestamp_note",
                        "note_evidence", "method_note_verification", "time_penalty_hours"):
                value.pop(key)
            path.write_text(json.dumps(value), encoding="utf-8")
        old_archive = self.archive_path().read_bytes()
        repeated = self.record()
        self.assertEqual(repeated["observed_at"], original["observed_at"])
        self.assertNotIn("evidence_source", repeated)
        self.assertEqual(self.archive_path().read_bytes(), old_archive)
        self.assertEqual(self.index()[0]["status"], "VERIFIED_BROWSER")
        self.assertEqual(self.index()[0]["evidence_source"], "browser_observed")
        self.assertEqual(self.index()[0]["note_evidence"], "submitted_text")
        self.assertEqual(self.index()[0]["time_penalty_hours"], "")
        self.assertNotIn("time_penalty_hours", repeated)

    def test_prepared_explanation_does_not_claim_verified_website_wording(self):
        receipt = self.record(owner="teammate_reported", evidence_source="user_report",
                              note_evidence="prepared_explanation")
        archived = json.loads(self.archive_path("teammate_reported").read_text())
        self.assertEqual(receipt["note_evidence"], "prepared_explanation")
        self.assertIn("has not been confirmed", archived["method_note_verification"])
        self.assertEqual(self.index()[0]["note_evidence"], "prepared_explanation")
        self.assertEqual(self.archive_path("teammate_reported").with_suffix(".txt").read_text(),
                         "Native CPU MPS chi32.\n")
        with self.assertRaisesRegex(ValueError, "Cannot replace"):
            self.record(owner="teammate_reported", evidence_source="user_report", note_evidence="submitted_text")

    def test_repeat_cannot_silently_change_score_explanation_evidence_or_bytes(self):
        self.record()
        official = self.workflow / "official_submissions/G2-01.json"
        original = official.read_bytes()
        archived = self.archive_path().read_bytes()
        for changes in ({"score":499}, {"note":"A different method."}, {"evidence_source":"user_report"}):
            with self.subTest(changes=changes), self.assertRaisesRegex(ValueError, "Cannot replace"):
                self.record(**changes)
        self.source.write_text(self.source.read_text().replace("0.25", "0.250"), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "Cannot replace"):
            self.record()
        self.assertEqual(official.read_bytes(), original)
        self.assertEqual(self.archive_path().read_bytes(), archived)

    def test_archive_also_rejects_score_and_evidence_changes_before_writes(self):
        value = self.record(owner="teammate_reported", evidence_source="user_report")
        receipt = self.archive_path("teammate_reported")
        previous = receipt.read_bytes()
        for changes in ({"displayed_score":500}, {"evidence_source":"browser_observed"}, {"source":"different source"}):
            with self.subTest(changes=changes), self.assertRaisesRegex(ValueError, "Cannot replace"):
                archive_submission({**value, **changes}, repo=self.repo, ledger_root=self.ledger)
        self.assertEqual(receipt.read_bytes(), previous)

    def test_identical_repeat_keeps_original_evidence_time(self):
        first = self.record(owner="teammate_reported", evidence_source="user_report")
        with patch("otoc.submission_registry.utc_now", return_value="2026-10-24T22:00:00+00:00"):
            repeated = self.record(owner="teammate_reported", evidence_source="user_report")
        self.assertEqual(first, repeated)
        self.assertEqual(len(list((self.ledger / "events").glob("*.json"))), 1)

    def test_missing_provenance_leaves_no_official_receipt_or_archive(self):
        (self.ledger / "records/run-1.json").unlink()
        with self.assertRaisesRegex(ValueError, "No recorded simulation"):
            self.record(owner="teammate_reported", evidence_source="user_report")
        self.assertFalse((self.workflow / "official_submissions").exists())
        self.assertFalse((self.repo / "submissions").exists())
        self.assertFalse((self.ledger / "submissions.csv").exists())

    def test_unfinished_or_later_run_does_not_supply_provenance(self):
        path = self.ledger / "records/run-1.json"
        original = json.loads(path.read_text())
        for change in ({"status":"RUNNING"}, {"finished_at":None}, {"finished_at":"2026-10-25T12:00:00+00:00"}):
            path.write_text(json.dumps({**original, **change}), encoding="utf-8")
            with self.subTest(change=change), self.assertRaisesRegex(ValueError, "No recorded simulation"):
                self.record()
            self.assertFalse((self.repo / "submissions").exists())
            self.assertFalse((self.workflow / "official_submissions").exists())

    def test_archive_failure_does_not_publish_workflow_receipt(self):
        with patch("otoc.submission_registry.archive_submission", side_effect=OSError("archive unavailable")):
            with self.assertRaisesRegex(OSError, "archive unavailable"):
                self.record()
        self.assertFalse((self.workflow / "official_submissions").exists())

    def test_invalid_owner_and_evidence_are_rejected_before_archival(self):
        for changes in ({"owner":"../escape"}, {"owner":"a/b"}, {"owner":""}, {"owner":"A"},
                        {"owner":"x" * 65}, {"evidence_source":"guessed"}, {"attempt":True},
                        {"note_evidence":"unknown"}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                self.record(**changes)
        self.assertFalse((self.repo / "submissions").exists())
        self.assertFalse((self.workflow / "official_submissions").exists())

    def test_existing_teammate_special_schema_remains_in_index(self):
        legacy = self.repo / "submissions/teammates/teammate-1/G1/submitted-v1.json"
        legacy.parent.mkdir(parents=True)
        legacy.write_text(json.dumps({"owner":"teammate-1", "problem":"G1", "maximum_points":300,
                                     "source_commit":"abc123", "reported_score_fraction":1}), encoding="utf-8")
        self.record(owner="teammate_reported", evidence_source="user_report")
        indexed = {row["owner"]:row for row in self.index()}
        self.assertEqual(indexed["teammate-1"]["status"], "REPORTED_BY_TEAMMATE")
        self.assertEqual(indexed["teammate-1"]["displayed_score"], "")
        self.assertEqual(indexed["teammate_reported"]["status"], "USER_REPORTED")

    def test_index_retains_scored_and_pending_submission_claims_without_inference(self):
        def receipt(name, value):
            path = self.repo / "submissions" / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(value), encoding="utf-8")

        receipt("G1/user-reported-submission.json", {
            "problem":"G1", "status":"SUBMITTED_USER_REPORTED", "attempt":None,
            "score":None, "expected_source_csv":"problems/04_graded_G1/exact_values.csv",
            "uploaded_bytes_verified":False})
        receipt("teammates/teammate-1/G3/submitted-v3.json", {
            "problem":"G3", "owner":"teammate-1", "submission_status":"REPORTED_SUBMITTED",
            "reported_displayed_score":773, "reported_score_fraction":0.9663,
            "maximum_points":800, "attempt":None, "source_commit":"abc123"})
        receipt("candidates/G2/mixed.feedback.json", {
            "problem":"G2", "submission_status":"USER_CONFIRMED_SUBMITTED",
            "candidate_csv":"submissions/candidates/G2/mixed.csv",
            "candidate_sha256":"a" * 64, "score":579, "account_owner":None,
            "attempt":None, "exact_uploaded_bytes_verified":False})
        mixed_path = self.repo / "submissions/candidates/G2/mixed.feedback.json"
        mixed_value = json.loads(mixed_path.read_text(encoding="utf-8"))
        mixed_path.write_text(json.dumps({**mixed_value,
            "evidence_source":"repo_text_claim",
            "submission_evidence_source":"user_report",
            "score_evidence_source":"repo_text_claim",
            "score_report_path":"submissions/candidates/G2/mixed.score-report.txt",
            "score_source_commit":"030518f"}),
            encoding="utf-8")
        receipt("candidates/G4/direct.feedback.json", {
            "problem":"G4", "accepted_grading":True, "reported_displayed_score":0,
            "candidate_csv":"submissions/candidates/G4/direct.csv",
            "candidate_sha256":"b" * 64, "owner":None, "attempt":None,
            "uploaded_bytes_independently_verified":False})
        receipt("candidates/G3/unsubmitted.feedback.json", {"problem":"G3", "score":700})

        self.assertEqual(rebuild_submission_index(repo=self.repo, ledger_root=self.ledger), 4)
        original = (self.ledger / "submissions.csv").read_bytes()
        self.assertEqual(rebuild_submission_index(repo=self.repo, ledger_root=self.ledger), 4)
        self.assertEqual((self.ledger / "submissions.csv").read_bytes(), original)
        rows = {row["receipt_path"]:row for row in self.index()}
        g1 = rows["submissions/G1/user-reported-submission.json"]
        self.assertEqual((g1["owner"], g1["displayed_score"], g1["csv_path"],
                          g1["sha256"], g1["upload_bytes_verified"]),
                         ("original_submitter", "", "", "", "False"))
        mixed = rows["submissions/candidates/G2/mixed.feedback.json"]
        self.assertEqual((mixed["owner"], mixed["attempt"], mixed["displayed_score"],
                          mixed["status"], mixed["upload_bytes_verified"],
                          mixed["evidence_source"], mixed["score_evidence_source"],
                          mixed["score_evidence_path"], mixed["score_evidence_commit"]),
                         ("", "", "579", "USER_CONFIRMED_SUBMITTED", "False",
                          "user_report", "repo_text_claim",
                          "submissions/candidates/G2/mixed.score-report.txt", "030518f"))
        g3 = rows["submissions/teammates/teammate-1/G3/submitted-v3.json"]
        self.assertEqual((g3["displayed_score"], g3["attempt"], g3["status"]),
                         ("773", "", "REPORTED_SUBMITTED"))
        g4 = rows["submissions/candidates/G4/direct.feedback.json"]
        self.assertEqual((g4["displayed_score"], g4["owner"], g4["attempt"]),
                         ("0", "", ""))

    def test_cli_forwards_owner_and_user_report_without_recording(self):
        note = self.repo / "note.txt"
        note.write_text("Native CPU MPS chi32.", encoding="utf-8")
        script = Path(__file__).resolve().parents[1] / "scripts/record_submission.py"
        argv = [str(script), "--problem", "G2", "--attempt", "1", "--csv", str(self.source),
                "--note-file", str(note), "--score", "498", "--owner", "teammate_reported",
                "--evidence-source", "user_report", "--note-evidence", "prepared_explanation",
                "--time-penalty-hours", "3.48"]
        result = {"problem":"G2", "attempt":1, "displayed_score":498, "owner":"teammate_reported",
                  "status":"USER_REPORTED"}
        with patch("sys.argv", argv), patch("otoc.submission_registry.record_submission", return_value=result) as mocked:
            with redirect_stdout(io.StringIO()) as output:
                runpy.run_path(str(script), run_name="__main__")
        self.assertEqual(mocked.call_args.kwargs, {"owner":"teammate_reported", "evidence_source":"user_report",
                                                 "note_evidence":"prepared_explanation", "time_penalty_hours":3.48})
        self.assertIn("USER_REPORTED", output.getvalue())
        self.assertFalse((self.repo / "submissions").exists())
