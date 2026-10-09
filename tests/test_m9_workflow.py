"""M9 keyboard navigation, timeline scrubbing and reversible page deletion."""
import time
from pathlib import Path
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt,QPoint
from PySide6.QtTest import QTest
from gui.window import Window
from gui.state import State
from gui.timeline import Timeline
VIDEO=Path('/tmp/slide-m1-fixtures/scene-change.mp4')

def spin(app,condition,timeout=15):
    start=time.monotonic()
    while time.monotonic()-start<timeout:
        app.processEvents()
        if condition():return
        time.sleep(.005)
    raise AssertionError('timeout')

def test_keyboard_page_focus_and_delete_undo():
    if not VIDEO.exists():return
    app=QApplication.instance() or QApplication([])
    w=Window();w.show()
    try:
        w.fps.setCurrentIndex(0)
        w.open_source(VIDEO)
        spin(app,lambda:w.controller.state==State.SOURCE_READY)
        w.analyze()
        spin(app,lambda:w.controller.state==State.REVIEW_READY)
        assert len(w.controller.project.pages)>=2
        start=w.controller.focus_page_id
        w.navigate_page(1)
        assert w.controller.focus_page_id!=start
        assert w.page_view.currentIndex().row()==1
        assert w.controller.project.samples[w.current_index].sample_id==w.controller.project.pages[1].representative_sample_id
        w.navigate_page(-1)
        assert w.controller.focus_page_id==start
        w.seek_index(len(w.controller.project.samples)-1)
        assert w.controller.focus_page_id==start
        old_ids=[p.page_id for p in w.controller.project.pages]
        w.delete_page()
        assert w.undo_button.isVisible()
        assert len(w.controller.project.pages)==len(old_ids)-1
        w.undo_delete()
        assert [p.page_id for p in w.controller.project.pages]==old_ids
        assert w.controller.focus_page_id==start
        assert not w.undo_button.isEnabled()
        assert w.redo_button.isEnabled()
    finally:
        w.close()
        spin(app,lambda:not w.isVisible())

def test_timeline_single_track_scrubbing():
    from types import SimpleNamespace
    from fractions import Fraction
    app=QApplication.instance() or QApplication([])
    project=SimpleNamespace(source=SimpleNamespace(metadata=(('duration_s',10),)),
        pages=[SimpleNamespace(page_id='p',representative_sample_id='s')],
        transitions=[SimpleNamespace(lower_time=Fraction(2),upper_time=Fraction(3),observed_time=Fraction(3))],
        sample_time=lambda _:Fraction(5))
    t=Timeline()
    t.resize(800,34);t.set_project(project);t.show()
    seek=[]
    t.seekRequested.connect(seek.append)
    try:
        assert t.height()==34
        QTest.mousePress(t,Qt.MouseButton.LeftButton,pos=QPoint(160,16))
        QTest.mouseMove(t,QPoint(640,16))
        QTest.mouseRelease(t,Qt.MouseButton.LeftButton,pos=QPoint(640,16))
        assert len(seek)>=2
        assert abs(seek[-1]-8)<0.1
        assert t.boundary_tooltip(200) is not None # internal boundary helper remains nonvisual
    finally:t.close()
