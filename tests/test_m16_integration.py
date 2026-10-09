"""M16 end-to-end completion and cancel recovery regressions."""
from pathlib import Path
import time

from PySide6.QtWidgets import QApplication,QFileDialog,QMessageBox
from gui.window import Window
from gui.state import State,Controller
from pypdf import PdfReader

VIDEO=Path('/tmp/slide-m1-fixtures/scene-change.mp4')

def wait(app,condition,timeout=25):
    start=time.monotonic()
    while time.monotonic()-start<timeout:
        app.processEvents()
        if condition():return
        time.sleep(.004)
    raise AssertionError('GUI timeout')

def test_export_cancel_state_returns_to_review():
    from types import SimpleNamespace
    c=Controller(state=State.REVIEW_READY,source='video',project=SimpleNamespace(pages=[object()],samples=[object()]))
    c.begin_export('job')
    assert c.state==State.EXPORTING
    assert c.cancel() and c.state==State.CANCELLING
    assert c.fail_job('job')
    assert c.state==State.REVIEW_READY
    assert c.pending_job is None

def test_full_v04_edit_export_complete_then_edit_and_export_again(tmp_path,monkeypatch):
    if not VIDEO.is_file():return
    app=QApplication.instance() or QApplication([])
    w=Window();w.show()
    try:
        w.open_source(VIDEO);wait(app,lambda:w.controller.state==State.SOURCE_READY)
        assert w.stage=='preparation'
        w.analyze();assert w.stage=='analyzing'
        wait(app,lambda:w.stage=='review')
        assert w.timeline.isVisible() and not w.play_button.isVisible()
        pages_before=tuple(w.controller.project.pages)
        w.delete_page()
        assert len(w.controller.project.pages)==len(pages_before)-1
        w.undo_edit();assert tuple(w.controller.project.pages)==pages_before
        w.redo_edit();assert len(w.controller.project.pages)==len(pages_before)-1
        w.undo_edit()
        assert tuple(w.controller.project.pages)==pages_before
        dest=tmp_path/'첫 결과.pdf'
        monkeypatch.setattr(QFileDialog,'getSaveFileName',lambda *a,**k:(str(dest),'PDF'))
        w.export_pending()
        assert w.stage=='exporting'
        wait(app,lambda:w.stage=='complete')
        assert len(PdfReader(dest).pages)==len(pages_before)
        assert not dest.with_suffix('.json').exists()
        assert '첫 결과.pdf' in w.complete_details.text()
        w.return_to_review()
        assert w.stage=='review' and w.redo_button.isEnabled()
        # Editing continues normally after a successful export.
        w.redo_edit()
        assert len(w.controller.project.pages)==len(pages_before)-1
        dest2=tmp_path/'수정 결과.pdf'
        monkeypatch.setattr(QFileDialog,'getSaveFileName',lambda *a,**k:(str(dest2),'PDF'))
        w.export_pending();wait(app,lambda:w.stage=='complete')
        assert len(PdfReader(dest2).pages)==len(pages_before)-1
        assert not dest2.with_suffix('.json').exists()
    finally:
        w.close();wait(app,lambda:not w.isVisible())
