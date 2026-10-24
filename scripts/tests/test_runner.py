"""Runner tests. Free: no BlueQubit calls (offline backend and a fake client).

Run: python -m pytest scripts/tests -q
"""

import shutil
import sys
import zipfile
from pathlib import Path
from types import SimpleNamespace
from xml.etree import ElementTree as ET

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

try:  # the workbook exporter was retired on main; its compatibility tests skip without it
    import export_submission  # noqa: E402
except ModuleNotFoundError:
    export_submission = None
from runner.backends import CloudBackend, OfflineBackend  # noqa: E402
from runner.config import load_config  # noqa: E402
from runner.core import Job, execute, job_key, setup_workbook  # noqa: E402
from runner.ledger import Ledger  # noqa: E402
from runner.targets import Context, build_targets  # noqa: E402
from runner.workbook import ESTIMATES, JOBS, Workbook  # noqa: E402


@pytest.fixture
def book(tmp_path):
    template = ROOT / "runs" / "sample_1.xlsx"
    if not template.exists():
        pytest.skip("run workbooks were retired on main")
    path = tmp_path / "sample_1.xlsx"
    shutil.copy(template, path)
    return path


@pytest.fixture
def cfg():
    return load_config()


def demo_targets(cfg, n=4):
    c = {"provider": "demo", "n_qubits": n, "depth": 2, "butterfly": 0, "seed": 3, "qubits": "all"}
    return build_targets("sample_1", c, Context(cfg, lambda: None, lambda _: []))


def test_cells_round_trip_and_rest_of_file_unchanged(book):
    original = {n: zipfile.ZipFile(book).read(n) for n in zipfile.ZipFile(book).namelist()}
    wb = Workbook(book)
    row = wb.append_row(ESTIMATES, [3, "MPS", 64, None, None, -0.25, "job <&>", 1])
    wb.save(backup_dir=None)
    wb = Workbook(book)
    assert row == 5
    assert wb.table(ESTIMATES["sheet"], 5, 5, ESTIMATES["cols"])[5] == [3.0, "MPS", 64.0, None, None, -0.25, "job <&>", 1.0]
    assert wb.append_row(ESTIMATES, [4, "MPS", 64, None, None, 0.5, "j2", 1]) == 6
    after = zipfile.ZipFile(book)
    for name, data in original.items():
        if name.endswith((".xml", ".rels")):
            ET.fromstring(after.read(name))
        if name not in ("xl/workbook.xml", "xl/worksheets/sheet3.xml"):
            assert after.read(name) == data, name
    assert b"fullCalcOnLoad" in after.read("xl/workbook.xml")


def test_offline_ladder_feeds_team_exporter(book, cfg, tmp_path):
    if export_submission is None:
        pytest.skip("export_submission.py was retired on main")
    targets = demo_targets(cfg)
    wb = Workbook(book)
    setup_workbook(wb, "sample_1", [t.qubit for t in targets], force=True)  # copy may hold real data
    wb.save(backup_dir=None)
    settings = [float(s) for s in wb.settings("mps")]
    jobs = [Job("sample_1", t, "mps", s, None, "mps.cpu", job_key(cfg, t, "mps", s, None))
            for s in settings for t in targets]
    ledger = Ledger(tmp_path / "ledger.csv")
    summary = execute(jobs, OfflineBackend(cfg), ledger, {"sample_1": Workbook(book)}, cfg, log=lambda *_: None)
    assert summary["succeeded"] == len(jobs) and summary["failed"] == 0
    assert len(ledger.succeeded("offline")) == len(jobs)

    wb = Workbook(book)
    wb.set("Status", "B6", "MPS 3")
    wb.save(backup_dir=None)
    circuit, qubits, values = export_submission.selected_run(book, "sample")
    assert circuit == "sample_1" and qubits == {t.qubit for t in targets} and len(values) == len(targets)


def test_rerun_marks_old_estimate_unaccepted(book, cfg, tmp_path):
    if export_submission is None:
        pytest.skip("export_submission.py was retired on main")
    targets = demo_targets(cfg, n=2)
    wb = Workbook(book)
    setup_workbook(wb, "sample_1", [t.qubit for t in targets], force=True)  # copy may hold real data
    wb.save(backup_dir=None)
    jobs = [Job("sample_1", t, "mps", 32.0, None, "mps.cpu", job_key(cfg, t, "mps", 32.0, None)) for t in targets]
    for _ in range(2):
        execute(list(jobs), OfflineBackend(cfg), Ledger(tmp_path / "l.csv"), {"sample_1": Workbook(book)}, cfg,
                log=lambda *_: None)
    rows = Workbook(book).table(ESTIMATES["sheet"], 5, 10, ESTIMATES["cols"])
    accepted = [v[7] for v in rows.values() if v[0] is not None]
    assert accepted == [0.0, 0.0, 1.0, 1.0]
    wb = Workbook(book)
    wb.set("Status", "B6", "MPS 1")
    wb.save(backup_dir=None)
    export_submission.selected_run(book, "sample")  # no duplicate-estimate error


class FakeClient:
    """Mimics the parts of bluequbit.BQClient the runner uses."""

    def __init__(self, final):
        self.final, self.calls = final, []

    def run(self, circuit, **kw):
        self.calls.append(kw)
        return SimpleNamespace(job_id=f"j{len(self.calls)}", run_status="QUEUED", cost=None, run_time_ms=None,
                               error_message=None, expectation_value=None)

    def get(self, ids):
        return [SimpleNamespace(job_id=i, **self.final) for i in ids]


def test_cloud_backend_options_and_results(cfg, tmp_path):
    targets = demo_targets(cfg, n=2)
    client = FakeClient(dict(run_status="COMPLETED", cost=0.5, run_time_ms=1500, error_message=None,
                             expectation_value=[0.42]))
    cfg = {**cfg, "limits": {**cfg["limits"], "poll_interval_s": 0}}
    jobs = [Job("sample_1", t, "pps", 0.003, 2, "pauli-path", job_key(cfg, t, "pps", 0.003, 2)) for t in targets]
    summary = execute(jobs, CloudBackend(cfg, client), Ledger(tmp_path / "l.csv"), {}, cfg, log=lambda *_: None)
    assert summary["succeeded"] == 2 and summary["credits"] == 1.0
    call = client.calls[0]
    assert call["device"] == "pauli-path" and call["asynchronous"] is True
    assert call["options"] == {"pauli_path_truncation_threshold": 0.003, "pauli_path_circuit_transpilation_level": 2}
    assert call["pauli_sum"] == [("IZ", 1.0)]


def test_cloud_failure_is_recorded_not_raised(cfg, tmp_path):
    targets = demo_targets(cfg, n=1)
    client = FakeClient(dict(run_status="NOT_ENOUGH_FUNDS", cost=None, run_time_ms=None,
                             error_message="balance too low", expectation_value=None))
    cfg = {**cfg, "limits": {**cfg["limits"], "poll_interval_s": 0}}
    jobs = [Job("sample_1", targets[0], "mps", 64.0, None, "mps.cpu", "k")]
    ledger = Ledger(tmp_path / "l.csv")
    summary = execute(jobs, CloudBackend(cfg, client), ledger, {}, cfg, log=lambda *_: None)
    assert summary["failed"] == 1
    assert "NOT_ENOUGH_FUNDS" in ledger.latest_by_job()["j1"]["error"]


def test_little_endian_observable(cfg):
    labels = [t.pauli_sum[0][0] for t in demo_targets(cfg, n=3)]
    assert labels == ["IIZ", "IZI", "ZII"]  # qubit 0 is the rightmost character
