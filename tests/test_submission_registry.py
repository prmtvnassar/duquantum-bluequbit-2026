import csv
from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import runpy
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from otoc.submission_registry import archive_submission, record_submission


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

    def test_legacy_browser_receipts_keep_default_identity_and_remain_immutable(self):
        original = self.record()
        workflow_path = self.workflow / "official_submissions/G2-01.json"
        for path in (workflow_path, self.archive_path()):
            value = json.loads(path.read_text())
            for key in ("owner", "evidence_source", "status", "verification_note", "timestamp_note",
                        "note_evidence", "method_note_verification"):
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
        legacy = self.repo / "submissions/teammates/kevin/G1/submitted-v1.json"
        legacy.parent.mkdir(parents=True)
        legacy.write_text(json.dumps({"owner":"kevin", "problem":"G1", "maximum_points":300,
                                     "source_commit":"abc123", "reported_score_fraction":1}), encoding="utf-8")
        self.record(owner="teammate_reported", evidence_source="user_report")
        indexed = {row["owner"]:row for row in self.index()}
        self.assertEqual(indexed["kevin"]["status"], "REPORTED_BY_TEAMMATE")
        self.assertEqual(indexed["kevin"]["displayed_score"], "")
        self.assertEqual(indexed["teammate_reported"]["status"], "USER_REPORTED")

    def test_cli_forwards_owner_and_user_report_without_recording(self):
        note = self.repo / "note.txt"
        note.write_text("Native CPU MPS chi32.", encoding="utf-8")
        script = Path(__file__).resolve().parents[1] / "scripts/record_submission.py"
        argv = [str(script), "--problem", "G2", "--attempt", "1", "--csv", str(self.source),
                "--note-file", str(note), "--score", "498", "--owner", "teammate_reported",
                "--evidence-source", "user_report", "--note-evidence", "prepared_explanation"]
        result = {"problem":"G2", "attempt":1, "displayed_score":498, "owner":"teammate_reported",
                  "status":"USER_REPORTED"}
        with patch("sys.argv", argv), patch("otoc.submission_registry.record_submission", return_value=result) as mocked:
            with redirect_stdout(io.StringIO()) as output:
                runpy.run_path(str(script), run_name="__main__")
        self.assertEqual(mocked.call_args.kwargs, {"owner":"teammate_reported", "evidence_source":"user_report",
                                                 "note_evidence":"prepared_explanation"})
        self.assertIn("USER_REPORTED", output.getvalue())
        self.assertFalse((self.repo / "submissions").exists())
