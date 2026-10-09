"""M14 review screen is single-timeline and fixed-edit-control only."""
from pathlib import Path
import time
from PySide6.QtWidgets import QApplication
from gui.window import Window
from gui.state import State

VIDEO=Path('/tmp/slide-m1-fixtures/scene-change.mp4')
def wait(app,fn,timeout=15):
    start=time.monotonic()
    while time.monotonic()-start<timeout:
        app.processEvents()
        if fn():return
        time.sleep(.005)
    raise AssertionError('Timeout')

def test_review_layout_is_stable_when_scrubbing():
    if not VIDEO.exists():return
    app=QApplication.instance() or QApplication([])
    w=Window();w.show()
    try:
        w.open_source(VIDEO)
        wait(app,lambda:w.controller.state==State.SOURCE_READY)
        w.analyze()
        wait(app,lambda:w.controller.state==State.REVIEW_READY)
        assert w.stage=='review'
        assert w.timeline.isVisible() and w.time_label.isVisible()
        assert not w.slider.isVisible() and not w.play_button.isVisible()
        assert w.add_button.isVisible() and w.replace_button.isVisible()
        assert not w.page_menu.isVisible()
        assert not w.crop_button.isVisible() and not w.analyze_button.isVisible()
        assert not w.open_button.isVisible() and not w.advanced_button.isVisible()
        assert w.export_button.isVisible() and w.back_to_preparation.isVisible()
        heights=(w.add_button.geometry().y(),w.replace_button.geometry().y())
        for index in range(len(w.controller.project.samples)):
            w.seek_index(index);app.processEvents()
            assert w.add_button.isVisible() and w.replace_button.isVisible()
            assert heights==(w.add_button.geometry().y(),w.replace_button.geometry().y())
        w.return_to_preparation()
        assert w.stage=='preparation'
        assert w.analyze_button.isVisible()
        assert not w.timeline.isVisible()
    finally:
        w.close()
        wait(app,lambda:not w.isVisible())
