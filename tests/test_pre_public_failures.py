"""Real Qt failure paths must retain edits and show recoverable errors."""
import time
from pathlib import Path
import pytest
from PySide6.QtWidgets import QApplication,QFileDialog,QMessageBox
from gui.window import Window
from gui.state import State
from slide_core.models import CancelledError
from slide_core.cache import LeaseBusy
from slide_core.export import RecoveryRequired
from tests.test_sampling import make_video

def wait(app,done,timeout=15):
    start=time.monotonic()
    while time.monotonic()-start<timeout:
        app.processEvents()
        if done():return
        time.sleep(.005)
    raise AssertionError('Qt operation timed out')

@pytest.fixture
def edited_window(tmp_path,monkeypatch):
    app=QApplication.instance() or QApplication([])
    warnings=[]
    monkeypatch.setattr(QMessageBox,'warning',lambda *args:warnings.append(args[2]))
    source=make_video(tmp_path/'source.mp4',duration=4,fps=4)
    w=Window();w.show()
    w.open_source(source.path);wait(app,lambda:w.controller.state==State.SOURCE_READY)
    w.analyze();wait(app,lambda:w.controller.state==State.REVIEW_READY)
    project=w.controller.project
    w.delete_page()
    assert w.history.undo_stack
    try:yield app,w,project,warnings
    finally:
        w.close();wait(app,lambda:not w.isVisible())

def test_failed_video_open_preserves_history_and_can_undo(edited_window,tmp_path):
    app,w,project,_=edited_window
    pages=tuple(project.pages);history=tuple(w.history.undo_stack)
    first_frame=w._first_frame
    w.open_source(tmp_path/'missing.mp4')
    wait(app,lambda:w.controller.state==State.REVIEW_READY)
    assert w.controller.project is project and tuple(project.pages)==pages
    assert tuple(w.history.undo_stack)==history
    assert w._first_frame is first_frame
    w.undo_edit()
    assert tuple(project.pages)==history[-1][0].pages

def test_cancelled_video_probe_preserves_history(edited_window,monkeypatch,tmp_path):
    app,w,project,_=edited_window
    history=tuple(w.history.undo_stack)
    def slow_probe(path,*,cancel_token):
        while not cancel_token.cancelled:time.sleep(.005)
        raise CancelledError('Cancelled')
    monkeypatch.setattr(Window,'_prepare_source',staticmethod(slow_probe))
    w.open_source(tmp_path/'new.mp4');w.cancel()
    wait(app,lambda:w.controller.state==State.REVIEW_READY)
    assert w.controller.project is project
    assert tuple(w.history.undo_stack)==history

def test_successful_video_open_clears_old_history(edited_window):
    app,w,project,_=edited_window
    w.open_source(project.source.path)
    wait(app,lambda:w.controller.state==State.SOURCE_READY)
    assert not w.history.undo_stack and not w.history.redo_stack

@pytest.mark.parametrize('failure',[LeaseBusy('Output already locked'),PermissionError('Denied'),RecoveryRequired('Needs manual recovery')])
def test_recovery_failure_is_announced_without_export(edited_window,tmp_path,monkeypatch,failure):
    app,w,project,warnings=edited_window
    target=tmp_path/'out.pdf';target.write_bytes(b'original-output')
    journal=tmp_path/'.slide-export-review.journal.json';journal.write_text('{}')
    monkeypatch.setattr(QFileDialog,'getSaveFileName',lambda *a,**k:(str(target),'PDF'))
    monkeypatch.setattr(QMessageBox,'question',lambda *a,**k:QMessageBox.StandardButton.Yes)
    def failing_recovery(parent):raise failure
    monkeypatch.setattr('gui.window.recover_export',failing_recovery)
    w.export_pending()
    assert warnings and str(failure) in warnings[-1]
    assert w.jobs.worker is None and w.controller.state==State.REVIEW_READY
    assert target.read_bytes()==b'original-output' and journal.read_text()=='{}'
