"""M7 video preparation and PowerPoint-style region editor regression checks."""
from pathlib import Path
import pytest
from PySide6.QtCore import Qt,QPoint
from PySide6.QtGui import QImage
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication
from slide_core.models import Rect
from gui.preparation import prepare_first_frame
from gui.regions import RegionCanvas,adjust_rect
from gui.window import Window
from gui.state import State
import time
VIDEO=Path('/tmp/slide-m1-fixtures/scene-change.mp4')
def spin(app,predicate,timeout=15):
    started=time.monotonic()
    while time.monotonic()-started<timeout:
        app.processEvents()
        if predicate():return
        time.sleep(.005)
    raise AssertionError('Qt operation timeout')


@pytest.mark.parametrize(('handle','delta','expected'),[
    ('nw',(-10,-5),Rect(10,15,50,35)),
    ('n',(100,-5),Rect(20,15,40,35)),
    ('ne',(10,-5),Rect(20,15,50,35)),
    ('e',(10,100),Rect(20,20,50,30)),
    ('se',(10,5),Rect(20,20,50,35)),
    ('s',(100,5),Rect(20,20,40,35)),
    ('sw',(-10,5),Rect(10,20,50,35)),
    ('w',(-10,100),Rect(10,20,50,30)),
    ('move',(10,5),Rect(30,25,40,30))
])
def test_eight_resize_handles_and_move(handle,delta,expected):
    assert adjust_rect(Rect(20,20,40,30),handle,*delta,100,90)==expected


def test_handles_clamp_to_image_and_minimum_area():
    source=Rect(20,20,40,30)
    assert adjust_rect(source,'move',(0),(-500),100,90).y==0
    assert adjust_rect(source,'se',1000,1000,100,90)==Rect(20,20,80,70)
    assert adjust_rect(source,'nw',1000,1000,100,90)==Rect(59,49,1,1)


def test_canvas_hit_detection_and_resize(qtbot=None):
    app=QApplication.instance() or QApplication([])
    canvas=RegionCanvas(QImage(200,100,QImage.Format.Format_RGB888),initial=Rect(40,20,80,60))
    canvas.resize(600,300)
    canvas.show()
    try:
        app.processEvents()
        scale,ox,oy=canvas._geometry()
        def point(x,y):return QPoint(round(ox+x*scale),round(oy+y*scale))
        assert canvas._hit((point(40,20).x(),point(40,20).y()))=='nw'
        assert canvas._hit((point(120,80).x(),point(120,80).y()))=='se'
        assert canvas._hit((point(80,50).x(),point(80,50).y()))=='move'
        QTest.mousePress(canvas,Qt.MouseButton.LeftButton,pos=point(120,80))
        QTest.mouseMove(canvas,point(130,85))
        QTest.mouseRelease(canvas,Qt.MouseButton.LeftButton,pos=point(130,85))
        assert canvas.selection==Rect(40,20,90,65)
    finally:
        canvas.close()


def test_prepare_before_analyze_and_default_fps():
    if not VIDEO.is_file():pytest.skip('FFmpeg fixture unavailable')
    app=QApplication.instance() or QApplication([])
    window=Window();window.show()
    try:
        assert window.settings.fps==0.5
        assert window.fps.currentIndex()==1
        window.open_source(VIDEO)
        spin(app,lambda:window.controller.state==State.SOURCE_READY)
        assert window._first_frame is not None
        assert window._auto_roi is not None
        assert window._first_frame.width()>0
        assert window._suggested_roi==window._auto_roi
        assert window.crop_button.isEnabled()
        assert window.mask_button.isEnabled()
        assert window.analyze_button.isEnabled()
    finally:
        window.close()
        spin(app,lambda:not window.isVisible())
