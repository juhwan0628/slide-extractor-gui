"""Real offscreen Qt + synthetic video end-to-end GUI M4; no native UI claim."""
from pathlib import Path
import time
import pytest
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer
from slide_core.config import DetectorConfig
from dataclasses import replace
from tests.media_fixtures import make_scene_video
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




def test_cancel_worker_preserves_previous_project(tmp_path,monkeypatch):
    from PySide6.QtWidgets import QMessageBox
    monkeypatch.setattr(QMessageBox,'question',lambda *args,**kwargs: QMessageBox.StandardButton.Yes)
    video=make_scene_video(tmp_path/'scene.mp4')
    app=QApplication.instance() or QApplication([])
    w=Window();w.show()
    try:
        w.open_source(video);spin(app,lambda:w.controller.state==State.SOURCE_READY)
        w.analyze();spin(app,lambda:w.controller.state==State.REVIEW_READY)
        old=w.controller.project
        w.settings=replace(w.settings,detector=replace(DetectorConfig(),candidate_mad=.01))
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
    video=make_scene_video(tmp_path/'scene.mp4')
    from gui import window as module
    from slide_core.models import Rect
    import cv2
    app=QApplication.instance() or QApplication([])
    w=Window();w.show()
    try:
        w.open_source(video);spin(app,lambda:w.controller.state==State.SOURCE_READY)
        w.analyze();spin(app,lambda:w.controller.state==State.REVIEW_READY)
        key=w._image_key(0)
        w.images.request(key,w.controller.project.samples[0].cache_path)
        spin(app,lambda:w.images.cached(key) is not None)
        w._first_frame=None  # Exercise the JPEG-only region editor fallback.
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
