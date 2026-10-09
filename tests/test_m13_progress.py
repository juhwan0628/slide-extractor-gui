"""M13 signals report only observable work, with no invented percent."""
from pathlib import Path
import time
from PySide6.QtWidgets import QApplication
from gui.window import Window
from gui.state import State
VIDEO=Path('/tmp/slide-m1-fixtures/scene-change.mp4')
def until(app,check,timeout=20):
    started=time.monotonic()
    while time.monotonic()-started<timeout:
        app.processEvents()
        if check():return
        time.sleep(.004)
    raise AssertionError('timeout')
def test_analysis_and_export_emit_real_stage_events(tmp_path,monkeypatch):
    if not VIDEO.is_file():return
    app=QApplication.instance() or QApplication([])
    w=Window();w.show()
    events=[]
    w.jobs.progress.connect(lambda jid,data:events.append((jid,*data)))
    try:
        w.open_source(VIDEO);until(app,lambda:w.controller.state==State.SOURCE_READY)
        w.analyze();until(app,lambda:w.controller.state==State.REVIEW_READY)
        names=[v[1] for v in events]
        assert 'sampling' in names and 'detecting' in names and 'assembling' in names
        detecting=[v for v in events if v[1]=='detecting' and v[3] is not None]
        assert detecting and detecting[-1][2]==detecting[-1][3]
        from PySide6.QtWidgets import QFileDialog
        monkeypatch.setattr(QFileDialog,'getSaveFileName',lambda *a,**kw:(str(tmp_path/'done.pdf'),'PDF'))
        events.clear()
        w.export_pending()
        until(app,lambda:w.stage=='complete')
        names=[v[1] for v in events]
        assert {'extracting','writing','verifying','publishing'}<=set(names)
        extracting=[v for v in events if v[1]=='extracting']
        assert extracting[-1][2]==extracting[-1][3]==len(w.controller.project.pages)
        w._job_progress('irrelevant',('extracting',1,2))
        assert w.stage=='complete'
    finally:
        w.close();until(app,lambda:not w.isVisible())
def test_indeterminate_and_measured_progress_modes():
    app=QApplication.instance() or QApplication([])
    w=Window()
    try:
        w._job_id='one'
        w._set_stage('analyzing')
        w._job_progress('one',('sampling',None,None))
        assert w.analysis_progress.minimum()==0 and w.analysis_progress.maximum()==0
        w._job_progress('one',('detecting',3,6))
        assert w.analysis_progress.value()==50 and w.analysis_progress.maximum()==100
        w._job_progress('other',('detecting',4,6))
        assert w.analysis_progress.value()==50
    finally:w.close()
