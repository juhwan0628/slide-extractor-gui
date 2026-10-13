"""M1 regression coverage for real publication, live recovery and durable status."""
import errno
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import threading
import time

import pytest
from slide_core import export, export_v3, pdf_only_export
from slide_core.cache import LeaseBusy
from slide_core.models import CancelToken
from tests.export_fixtures import make_project, extract_stub


def project_at(root, monkeypatch):
    root.mkdir(exist_ok=True)
    project = make_project(root)
    monkeypatch.setattr(export_v3, "extract_selected", extract_stub(project))
    monkeypatch.setattr(pdf_only_export, "extract_selected", extract_stub(project))
    return project


def test_pair_publication_contends_with_pdf_only_lock(tmp_path, monkeypatch):
    project = project_at(tmp_path / "project", monkeypatch)
    destination = tmp_path / "slides.pdf"
    lock = export.output_lock_path(destination)
    with export.export_file_lease(lock):
        with pytest.raises(LeaseBusy):
            export_v3.export_project(project, destination)
    assert not destination.exists()
    assert not destination.with_suffix(".json").exists()


def test_live_prepared_transaction_is_not_recovered(tmp_path):
    source = tmp_path / "source.mp4"; source.write_bytes(b"source")
    tx = export.ExportTransaction(source, export.snapshot_export(source, tmp_path / "slides.pdf"))
    try:
        tx.prepare(b"pdf", b"json")
        staged = {p.name: p.read_bytes() for p in tx.stage.iterdir()}
        journal = tx.journal_path.read_bytes()
        assert export.recover_export(tmp_path) == ()
        assert tx.journal_path.read_bytes() == journal
        assert {p.name: p.read_bytes() for p in tx.stage.iterdir()} == staged
        tx.commit()
    finally:
        tx.close()
    export.recover_export(tmp_path)


def test_auto_cleanup_does_not_recover_another_live_export(tmp_path, monkeypatch):
    project = project_at(tmp_path / "project", monkeypatch)
    a_extracting = threading.Event()
    release_a = threading.Event()
    b_prepared = threading.Event()
    release_b = threading.Event()
    original_extract = export_v3.extract_selected
    def extract(source, selections, root, **kwargs):
        if threading.current_thread().name == "export-A":
            a_extracting.set()
            assert release_a.wait(10)
        return original_extract(source, selections, root, **kwargs)
    monkeypatch.setattr(export_v3, "extract_selected", extract)
    original_prepare = export.ExportTransaction.prepare
    def prepare(tx, *args, **kwargs):
        result = original_prepare(tx, *args, **kwargs)
        if tx.paths[0].name == "B.pdf":
            b_prepared.set()
            assert release_b.wait(10)
        return result
    monkeypatch.setattr(export.ExportTransaction, "prepare", prepare)
    outcomes = {}
    def run(name):
        try:
            outcomes[name] = export_v3.export_project(project, tmp_path / (name + ".pdf"))
        except BaseException as exc:
            outcomes[name] = exc
    a = threading.Thread(target=run, args=("A",), name="export-A")
    b = threading.Thread(target=run, args=("B",), name="export-B")
    try:
        a.start(); assert a_extracting.wait(10)
        b.start(); assert b_prepared.wait(10)
        release_a.set(); a.join(10)
        assert not a.is_alive()
        assert not isinstance(outcomes.get("A"), BaseException), outcomes.get("A")
        release_b.set(); b.join(10)
        assert not b.is_alive()
        assert not isinstance(outcomes.get("B"), BaseException), outcomes.get("B")
        for name in ("A", "B"):
            pdf = tmp_path / (name + ".pdf")
            sidecar = json.loads(pdf.with_suffix(".json").read_text())
            assert sidecar["artifact"]["pdf_sha256"] == hashlib.sha256(pdf.read_bytes()).hexdigest()
        assert not list(tmp_path.glob(".slide-export-*"))
    finally:
        release_a.set(); release_b.set()
        if a.ident is not None: a.join(10)
        if b.ident is not None: b.join(10)


def test_pdf_sync_failure_reports_already_published_output(tmp_path, monkeypatch):
    project = project_at(tmp_path / "project", monkeypatch)
    target = tmp_path / "slides.pdf"; target.write_bytes(b"previous pdf")
    token = CancelToken()
    def fail_sync(path):
        raise OSError(errno.EIO, "injected directory sync failure")
    monkeypatch.setattr(pdf_only_export, "sync_directory", fail_sync)
    with pytest.raises(Exception) as raised:
        pdf_only_export.export_pdf_only(project, target, overwrite=True, cancel_token=token)
    assert token.committed
    assert getattr(raised.value, "committed", False)
    assert raised.value.outputs == (target,)
    assert "saved" in str(raised.value).lower()
    assert target.read_bytes().startswith(b"%PDF")
    assert not list(tmp_path.glob("*.lock"))


@pytest.mark.parametrize("existing", [False, True])
def test_unsupported_hardlinks_reject_cleanly_before_outputs_change(tmp_path, monkeypatch, existing):
    project = project_at(tmp_path / "project", monkeypatch)
    target = tmp_path / "slides.pdf"
    if existing:
        target.write_bytes(b"old pdf")
        target.with_suffix(".json").write_bytes(b"old json")
    def unsupported(*args, **kwargs):
        raise OSError(errno.EOPNOTSUPP, "hard links not supported")
    monkeypatch.setattr(export.os, "link", unsupported)
    with pytest.raises(Exception) as raised:
        export_v3.export_project(project, target, overwrite=existing)
    assert "PDF-only" in str(raised.value)
    if existing:
        assert target.read_bytes() == b"old pdf"
        assert target.with_suffix(".json").read_bytes() == b"old json"
    else:
        assert not target.exists()
        assert not target.with_suffix(".json").exists()
    assert not list(tmp_path.glob(".slide-export-*"))
    assert not list(tmp_path.glob(".pts-render-*"))


def test_separate_processes_do_not_publish_over_same_pdf(tmp_path):
    """Hold real PDF-only publication while a second process attempts a pair."""
    program = r"""
import json, os, sys, time
from pathlib import Path
from slide_core import export_v3, pdf_only_export
from tests.export_fixtures import make_project, extract_stub
root = Path(sys.argv[1]); mode = sys.argv[2]
work = root / mode; work.mkdir()
project = make_project(work)
export_v3.extract_selected = extract_stub(project)
pdf_only_export.extract_selected = extract_stub(project)
target = root / "slides.pdf"
if mode == "first":
    real_replace = os.replace
    def hold(src, dst, *args, **kwargs):
        if Path(dst) == target:
            (root / "locked").write_text("yes")
            deadline = time.monotonic() + 15
            while not (root / "release").exists():
                if time.monotonic() > deadline: raise RuntimeError("release timed out")
                time.sleep(.01)
        return real_replace(src, dst, *args, **kwargs)
    pdf_only_export.os.replace = hold
    pdf_only_export.export_pdf_only(project, target)
else:
    try:
        export_v3.export_project(project, target)
    except BaseException as exc:
        (root / "second-outcome").write_text(type(exc).__name__)
    else:
        (root / "second-outcome").write_text("success")
"""
    first = subprocess.Popen([sys.executable, "-c", program, str(tmp_path), "first"],
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        deadline = time.monotonic() + 10
        while not (tmp_path / "locked").exists() and time.monotonic() < deadline:
            if first.poll() is not None: break
            time.sleep(.01)
        assert (tmp_path / "locked").exists(), first.poll()
        second = subprocess.run([sys.executable, "-c", program, str(tmp_path), "second"],
                                capture_output=True, timeout=10)
        assert second.returncode == 0, second.stderr.decode()
        assert (tmp_path / "second-outcome").read_text() == "LeaseBusy"
        assert not (tmp_path / "slides.json").exists()
    finally:
        (tmp_path / "release").write_text("yes")
        stdout, stderr = first.communicate(timeout=15)
        assert first.returncode == 0, stderr.decode()
    assert (tmp_path / "slides.pdf").read_bytes().startswith(b"%PDF")
    assert not list(tmp_path.glob("*.lock"))
    export.recover_export(tmp_path)
    assert not list(tmp_path.glob(".slide-export-*"))


def test_gui_does_not_call_published_pdf_cancelled_or_failed(tmp_path, monkeypatch):
    from PySide6.QtWidgets import QApplication, QMessageBox
    from gui.window import Window
    from gui.state import State
    project = project_at(tmp_path / "project", monkeypatch)
    target = tmp_path / "slides.pdf"
    def fail_sync(path):
        raise OSError(errno.EIO, "injected directory sync failure")
    monkeypatch.setattr(pdf_only_export, "sync_directory", fail_sync)
    with pytest.raises(Exception) as raised:
        pdf_only_export.export_pdf_only(project, target)
    qt = QApplication.instance() or QApplication([])
    window = Window()
    window.controller.project = project
    window.controller.source = project.source
    window.controller.state = State.REVIEW_READY
    window.controller.begin_export("export-job")
    window.controller.cancel()
    window._job_id = "export-job"; window._job_type = "export"
    warnings = []
    monkeypatch.setattr(QMessageBox, "warning", lambda *args: warnings.append(args[1:]))
    try:
        window._job_finished("export-job", None, raised.value)
        assert window.controller.state == State.REVIEW_READY
        assert warnings and warnings[0][0] == "Export saved with warning"
        assert "Cancelled" not in window.info.text()
        assert str(target) in window.info.text()
        assert window.progress.value() == 1
    finally:
        window.close()


def test_pair_busy_does_not_leave_a_recovery_journal(tmp_path, monkeypatch):
    project = project_at(tmp_path / "project", monkeypatch)
    target = tmp_path / "slides.pdf"
    with export.export_file_lease(export.output_lock_path(target)):
        with pytest.raises(LeaseBusy):
            export_v3.export_project(project, target)
        assert not list(tmp_path.glob(".slide-export-*"))


def test_pdf_lock_cleanup_failure_reports_published_file(tmp_path, monkeypatch):
    project = project_at(tmp_path / "project", monkeypatch)
    target = tmp_path / "slides.pdf"
    real_unlink = Path.unlink
    def fail_lock(path, *args, **kwargs):
        if path == export.output_lock_path(target):
            raise PermissionError("injected lock cleanup failure")
        return real_unlink(path, *args, **kwargs)
    monkeypatch.setattr(Path, "unlink", fail_lock)
    token = CancelToken()
    with pytest.raises(Exception) as raised:
        pdf_only_export.export_pdf_only(project, target, cancel_token=token)
    assert token.committed
    assert getattr(raised.value, "committed", False)
    assert raised.value.outputs == (target,)
    assert target.read_bytes().startswith(b"%PDF")


def test_pair_cleanup_failure_reports_published_pair(tmp_path, monkeypatch):
    project = project_at(tmp_path / "project", monkeypatch)
    target = tmp_path / "slides.pdf"
    def fail_cleanup(*args, **kwargs):
        raise OSError(errno.EIO, "injected pair cleanup failure")
    monkeypatch.setattr(export_v3, "_recover_one", fail_cleanup)
    token = CancelToken()
    with pytest.raises(Exception) as raised:
        export_v3.export_project(project, target, cancel_token=token)
    assert token.committed
    assert getattr(raised.value, "committed", False)
    assert raised.value.outputs == (target, target.with_suffix(".json"))
    payload = json.loads(target.with_suffix(".json").read_text())
    assert payload["artifact"]["pdf_sha256"] == hashlib.sha256(target.read_bytes()).hexdigest()


def test_macos_case_and_unicode_aliases_share_output_lock(tmp_path, monkeypatch):
    monkeypatch.setattr(sys, "platform", "darwin")
    assert export.output_lock_path(tmp_path / "Slides.pdf") == export.output_lock_path(tmp_path / "slides.pdf")
    assert export.output_lock_path(tmp_path / "caf\u00e9.pdf") == export.output_lock_path(tmp_path / "cafe\u0301.pdf")


def test_recovery_skips_live_preparation_in_separate_process(tmp_path):
    program = r"""
import os, sys, time
from pathlib import Path
from slide_core.export import ExportTransaction, snapshot_export
root = Path(sys.argv[1])
source = root / "source.mp4"; source.write_bytes(b"source")
tx = ExportTransaction(source, snapshot_export(source, root / "slides.pdf"))
tx.prepare(b"new-pdf", b"new-json")
(root / "prepared").write_text(tx.export_id)
deadline = time.monotonic() + 15
while not (root / "release").exists():
    if time.monotonic() > deadline: raise RuntimeError("release timed out")
    time.sleep(.01)
tx.commit()
"""
    child = subprocess.Popen([sys.executable, "-c", program, str(tmp_path)],
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        deadline = time.monotonic() + 10
        while not (tmp_path / "prepared").exists() and time.monotonic() < deadline:
            if child.poll() is not None: break
            time.sleep(.01)
        assert (tmp_path / "prepared").exists(), child.poll()
        export_id = (tmp_path / "prepared").read_text()
        journal = tmp_path / (".slide-export-" + export_id + ".journal.json")
        before = journal.read_bytes()
        assert export.recover_export(tmp_path) == ()
        assert journal.read_bytes() == before
        assert not (tmp_path / "slides.pdf").exists()
    finally:
        (tmp_path / "release").write_text("yes")
        stdout, stderr = child.communicate(timeout=15)
        assert child.returncode == 0, stderr.decode()
    assert export.recover_export(tmp_path) == ((export_id, "committed"),)
    assert (tmp_path / "slides.pdf").read_bytes() == b"new-pdf"
    assert (tmp_path / "slides.json").read_bytes() == b"new-json"
    assert not list(tmp_path.glob(".slide-export-*"))
    assert not list(tmp_path.glob("*.lock"))


@pytest.mark.parametrize("interference", ["changed_pdf", "unknown_stage"])
def test_rejected_committed_cleanup_retains_verified_backups(tmp_path, monkeypatch, interference):
    project = project_at(tmp_path / "project", monkeypatch)
    target = tmp_path / "slides.pdf"
    target.write_bytes(b"old pdf")
    target.with_suffix(".json").write_bytes(b"old json")
    real_cleanup = export_v3._recover_one
    stages = []
    def interfere(journal, parent, **kwargs):
        record, stage, paths = export._read_journal(journal, parent)
        stages.append(stage)
        assert (stage / "0.old").read_bytes() == b"old pdf"
        if interference == "changed_pdf":
            target.write_bytes(b"external content")
        else:
            (stage / "unknown.txt").write_bytes(b"keep me")
        return real_cleanup(journal, parent, **kwargs)
    monkeypatch.setattr(export_v3, "_recover_one", interfere)
    token = CancelToken()
    with pytest.raises(export.ExportPublishedError):
        export_v3.export_project(project, target, overwrite=True, cancel_token=token)
    assert token.committed
    assert len(stages) == 1
    assert (stages[0] / "0.old").read_bytes() == b"old pdf"
    assert (stages[0] / "1.old").read_bytes() == b"old json"
    assert len(list(tmp_path.glob(".slide-export-*.journal.json"))) == 1
    if interference == "changed_pdf":
        assert target.read_bytes() == b"external content"
    else:
        assert (stages[0] / "unknown.txt").read_bytes() == b"keep me"
