"""M12 export completion state and recovery paths."""
import time
from pathlib import Path
from PySide6.QtWidgets import QApplication,QFileDialog,QMessageBox
from gui.window import Window
from gui.state import State

VIDEO=Path('/tmp/slide-m1-fixtures/scene-change.mp4')
def wait(app,pred,timeout=20):
    start=time.monotonic()
    while time.monotonic()-start<timeout:
        app.processEvents()
        if pred():return
        time.sleep(.005)
    raise AssertionError('timed out')

def test_export_completion_screen_and_return(tmp_path,monkeypatch):
    if not VIDEO.is_file():return
    app=QApplication.instance() or QApplication([])
    w=Window();w.show()
    try:
        w.open_source(VIDEO);wait(app,lambda:w.controller.state==State.SOURCE_READY)
        assert w.stage=='preparation'
        w.analyze();assert w.stage=='analyzing'
        wait(app,lambda:w.controller.state==State.REVIEW_READY)
        assert w.stage=='review'
        target=tmp_path/'finished.pdf'
        monkeypatch.setattr(QFileDialog,'getSaveFileName',lambda *a,**kw:(str(target),'PDF'))
        w.export_pending()
        assert w.stage=='exporting' and w.work_area.currentIndex()==2
        wait(app,lambda:w.stage=='complete')
        assert w.work_area.currentIndex()==3
        assert 'finished.pdf' in w.complete_details.text()
        assert 'pages' in w.complete_details.text()
        assert str(tmp_path) in w.complete_details.text()
        opened=[]
        monkeypatch.setattr('gui.window.subprocess.Popen',lambda args,**kw:opened.append(args))
        w.open_export_folder()
        assert opened and str(tmp_path) in opened[0]
        w.return_to_review()
        assert w.stage=='review'
        assert w.controller.project is not None
    finally:
        w.close();wait(app,lambda:not w.isVisible())

def test_export_failure_must_not_display_complete(tmp_path,monkeypatch):
    if not VIDEO.is_file():return
    app=QApplication.instance() or QApplication([])
    w=Window();w.show()
    try:
        w.open_source(VIDEO);wait(app,lambda:w.controller.state==State.SOURCE_READY)
        w.analyze();wait(app,lambda:w.controller.state==State.REVIEW_READY)
        target=tmp_path/'broken.pdf'
        monkeypatch.setattr(QFileDialog,'getSaveFileName',lambda *a,**kw:(str(target),'PDF'))
        monkeypatch.setattr(QMessageBox,'warning',lambda *a,**kw:None)
        def failure(*a,**kw):raise RuntimeError('deliberately failed')
        monkeypatch.setattr('gui.window.export_pdf_only',failure)
        w.export_pending()
        assert w.stage=='exporting'
        wait(app,lambda:w.controller.state==State.REVIEW_READY)
        assert w.stage=='review'
        assert w._last_export is None
        assert not target.exists()
    finally:
        w.close();wait(app,lambda:not w.isVisible())
