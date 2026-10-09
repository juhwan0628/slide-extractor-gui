"""Real offscreen Qt + synthetic video end-to-end GUI M4; no native UI claim."""
from pathlib import Path
import time
import pytest
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer
from gui.window import Window
from gui.state import State

VIDEO=Path('/tmp/slide-m1-fixtures/scene-change.mp4')

def spin(app,condition,timeout=15):
    started=time.monotonic()
    while time.monotonic()-started<timeout:
        app.processEvents()
        if condition():return
        time.sleep(.005)
    raise AssertionError('Qt operation timeout')


def test_open_analyze_edit_play_close(tmp_path):
    if not VIDEO.is_file():pytest.skip('Standalone FFmpeg fixture not available')
    app=QApplication.instance() or QApplication([])
    w=Window();w.show()
    ticks=[]
    heartbeat=QTimer()
    heartbeat.timeout.connect(lambda:ticks.append(time.monotonic()))
    heartbeat.start(25)
    try:
        w.fps.setCurrentIndex(0)  # This legacy sampling fixture expects 1 FPS; M7 GUI defaults to 0.5.
        w.open_source(VIDEO)
        spin(app,lambda:w.controller.state==State.SOURCE_READY)
        w.analyze()
        spin(app,lambda:w.controller.state==State.REVIEW_READY)
        assert len(w.controller.project.samples)==4
        assert w.page_model.rowCount()==2
        assert w.export_button.isEnabled() is True # M5 exact-PTS export
        assert len(ticks)>=2
        w.seek_index(2)
        assert w.current_index==2
        w.add_page()
        assert w.page_model.rowCount()==3
        assert w.controller.project.revision==1
        w._page_clicked(w.page_model.index(0))
        focus=w.controller.focus_page_id
        w.seek_index(3)
        assert w.controller.focus_page_id==focus
        w.delete_page()
        assert w.page_model.rowCount()==2
        w._fps_changed(1)
        assert w.controller.state==State.REVIEW_DIRTY
        assert not w.controller.actions()['export']
        w._fps_changed(0)
        assert w.controller.state==State.REVIEW_READY
    finally:
        heartbeat.stop()
        w.close()
        spin(app,lambda:not w.isVisible())


def test_cancel_worker_preserves_previous_project(tmp_path,monkeypatch):
    from PySide6.QtWidgets import QMessageBox
    monkeypatch.setattr(QMessageBox,'question',lambda *args,**kwargs: QMessageBox.StandardButton.Yes)
    if not VIDEO.is_file():pytest.skip('Standalone FFmpeg fixture unavailable')
    app=QApplication.instance() or QApplication([])
    w=Window();w.show()
    try:
        w.open_source(VIDEO);spin(app,lambda:w.controller.state==State.SOURCE_READY)
        w.analyze();spin(app,lambda:w.controller.state==State.REVIEW_READY)
        old=w.controller.project
        w.fps.setCurrentIndex(1)
        w.analyze()
        w.cancel()
        spin(app,lambda:w.controller.state in {State.REVIEW_READY,State.REVIEW_DIRTY})
        assert w.controller.project is old
    finally:
        w.close();spin(app,lambda:not w.isVisible())


def test_close_while_probe_is_running(tmp_path,monkeypatch):
    from gui import window as module
    app=QApplication.instance() or QApplication([])
    class FakeSource:
        def __init__(self):
            self.path=tmp_path/'video.mp4';self.width=64;self.height=36
    def slow_probe(path,*,cancel_token=None):
        time.sleep(.13)
        cancel_token.raise_if_cancelled()
        return FakeSource()
    monkeypatch.setattr(module,'probe_source',slow_probe)
    w=Window();w.show()
    w.open_source(tmp_path/'video.mp4')
    assert w.controller.state==State.PROBING
    w.close()
    assert w.isVisible() and w._close_later
    spin(app,lambda:not w.isVisible())
    assert w.jobs.close_ready() and w.controller.state==State.CLOSED


def test_roi_dialog_uses_existing_cached_jpeg_only(tmp_path,monkeypatch):
    if not VIDEO.is_file():pytest.skip('Fixture unavailable')
    from gui import window as module
    from slide_core.models import Rect
    import cv2
    app=QApplication.instance() or QApplication([])
    w=Window();w.show()
    try:
        w.open_source(VIDEO);spin(app,lambda:w.controller.state==State.SOURCE_READY)
        w.analyze();spin(app,lambda:w.controller.state==State.REVIEW_READY)
        key=w._image_key(0)
        spin(app,lambda:w.images.cached(key) is not None)
        def forbid(*args,**kwargs):raise AssertionError('VideoCapture must never read during ROI selection')
        monkeypatch.setattr(cv2,'VideoCapture',forbid)
        class Dialog:
            def __init__(self,*a):pass
            def exec(self):return 1
            def value(self):return Rect(6,6,60,30)
        monkeypatch.setattr(module,'RegionDialog',Dialog)
        w.choose_region(False)
        assert w.settings.roi_mode=='manual'
        assert w.controller.state==State.REVIEW_DIRTY
        w._reset_roi()
        assert w.controller.state==State.REVIEW_READY
    finally:
        w.close();spin(app,lambda:not w.isVisible())


def test_m5_gui_export_exact_pts_pdf_json(tmp_path,monkeypatch):
    if not VIDEO.is_file():pytest.skip('Synthetic FFmpeg fixture unavailable')
    from gui import window as module
    from slide_core.timeline_json import loads
    from pypdf import PdfReader
    app=QApplication.instance() or QApplication([])
    w=Window();w.show()
    try:
        w.open_source(VIDEO);spin(app,lambda:w.controller.state==State.SOURCE_READY)
        w.analyze();spin(app,lambda:w.controller.state==State.REVIEW_READY)
        w.json_enabled=True;w.json_format='detailed'  # Explicit advanced legacy export.
        target=tmp_path/'GUI export.pdf'
        monkeypatch.setattr(module.QFileDialog,'getSaveFileName',lambda *a,**kw:(str(target),'PDF'))
        w.export_pending()
        spin(app,lambda:w.controller.state==State.REVIEW_READY and target.exists(),timeout=20)
        value=loads(target.with_suffix('.json').read_bytes(),pdf_bytes=target.read_bytes())
        assert value['schema_version']==3
        assert len(PdfReader(target).pages)==len(w.controller.project.pages)
        assert w.export_button.isEnabled()
        assert 'complete' in w.info.text().lower()
    finally:
        w.close();spin(app,lambda:not w.isVisible())
