"""M11 full user journey: source preparation, ROI/mask, review/edit and PDF."""
from pathlib import Path
import time
from PySide6.QtWidgets import QApplication,QFileDialog
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from pypdf import PdfReader
from gui.window import Window
from gui.state import State
from slide_core.models import Rect

VIDEO=Path('/tmp/slide-m1-fixtures/scene-change.mp4')

def wait(app,predicate,timeout=20):
    start=time.monotonic()
    while time.monotonic()-start<timeout:
        app.processEvents()
        if predicate():return
        time.sleep(.005)
    raise AssertionError('M11 Qt operation timed out')

def test_full_prepare_mask_analyze_review_edit_export(tmp_path,monkeypatch):
    if not VIDEO.is_file():return
    app=QApplication.instance() or QApplication([])
    w=Window();w.show()
    try:
        w.fps.setCurrentIndex(0) # 1fps to exercise the four-sample fixture.
        assert not w.json_enabled
        w.open_source(VIDEO)
        wait(app,lambda:w.controller.state==State.SOURCE_READY)
        assert w.stage=='preparation' and w._first_frame is not None
        assert w._auto_roi is not None
        # User reviews auto ROI and adds a small exclusion rectangle before analysis.
        class ApprovedMask:
            def __init__(self,*args,**kwargs): pass
            def exec(self):return 1
            def value(self):return Rect(2,2,12,12)
        monkeypatch.setattr('gui.window.RegionDialog',ApprovedMask)
        w.choose_region(True)
        assert len(w.settings.masks)==1
        w.analyze()
        wait(app,lambda:w.controller.state==State.REVIEW_READY)
        assert w.stage=='review'
        assert w.page_view.currentIndex().row()==0
        assert len(w.controller.project.pages)>=2
        assert not w.progress.isVisible()
        original_count=len(w.controller.project.pages)
        # Keep focus while scrubbing; add a missed page, then remove one.
        first_id=w.controller.focus_page_id
        included={p.representative_sample_id for p in w.controller.project.pages}
        free=next(i for i,s in enumerate(w.controller.project.samples) if s.sample_id not in included)
        w.seek_index(free)
        assert w.controller.focus_page_id==first_id
        w.add_page()
        assert len(w.controller.project.pages)==original_count+1
        w.navigate_page(1)
        focused=w.controller.focus_page_id
        w.delete_page()
        assert w.history.undo_stack
        assert len(w.controller.project.pages)==original_count
        w.undo_delete()
        assert len(w.controller.project.pages)==original_count+1
        assert w.controller.focus_page_id==focused
        w.delete_page()
        assert len(w.controller.project.pages)==original_count
        # Actual default GUI save must create PDF only, preserving any existing JSON.
        target=tmp_path/'course.pdf'
        sidecar=target.with_suffix('.json')
        sidecar.write_text('unrelated JSON',encoding='utf-8')
        monkeypatch.setattr(QFileDialog,'getSaveFileName',lambda *a,**k:(str(target),'PDF'))
        w.export_pending()
        wait(app,lambda:w.controller.state==State.REVIEW_READY and target.is_file(),timeout=30)
        assert len(PdfReader(str(target)).pages)==original_count
        assert sidecar.read_text(encoding='utf-8')=='unrelated JSON'
        assert 'complete' in w.info.text().lower()
    finally:
        w.close()
        wait(app,lambda:not w.isVisible())
