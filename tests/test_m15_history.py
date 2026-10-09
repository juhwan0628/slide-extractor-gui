"""M15 multi-step undo/redo across add, replace and delete."""
import time
from pathlib import Path
from PySide6.QtWidgets import QApplication
from gui.window import Window
from gui.state import State
from gui.history import EditHistory,Snapshot
VIDEO=Path('/tmp/slide-m1-fixtures/scene-change.mp4')
def wait(app,condition,timeout=15):
    start=time.monotonic()
    while time.monotonic()-start<timeout:
        app.processEvents()
        if condition():return
        time.sleep(.005)
    raise AssertionError('timeout')
def test_multistep_edit_history_and_redo(tmp_path):
    if not VIDEO.exists():return
    app=QApplication.instance() or QApplication([])
    w=Window();w.show()
    try:
        w.fps.setCurrentIndex(0)
        w.open_source(VIDEO);wait(app,lambda:w.controller.state==State.SOURCE_READY)
        w.analyze();wait(app,lambda:w.controller.state==State.REVIEW_READY)
        project=w.controller.project
        originals=tuple(project.pages)
        available=[i for i,s in enumerate(project.samples) if s.sample_id not in {p.representative_sample_id for p in originals}]
        assert len(available)>=2
        initial_revision=project.revision
        w.seek_index(available[0]);w.add_page()
        add=tuple(project.pages);assert len(add)==len(originals)+1
        w.seek_index(available[1]);w.replace_page()
        replaced=tuple(project.pages);assert replaced!=add
        focus_before_delete=w.controller.focus_page_id
        w.delete_page()
        deleted=tuple(project.pages);assert len(deleted)==len(originals)
        assert len(w.history.undo_stack)==3 and not w.history.redo_stack
        for expected in (replaced,add,originals):
            w.undo_edit()
            assert tuple(project.pages)==expected
            assert [w.page_model.data(w.page_model.index(i),w.page_model.PageId) for i in range(len(expected))]==[p.page_id for p in expected]
        assert not w.undo_button.isEnabled() and w.redo_button.isEnabled()
        for expected in (add,replaced,deleted):
            w.redo_edit()
            assert tuple(project.pages)==expected
        assert project.revision==initial_revision+9
        assert len(w.history.undo_stack)==3 and not w.history.redo_stack
        w.undo_edit()
        assert tuple(project.pages)==replaced
        w.delete_page()
        assert not w.history.redo_stack
        assert len(w.history.undo_stack)==3
        # Saving a PDF never clears history; changing video does.
        from slide_core.pdf_only_export import export_pdf_only
        export_pdf_only(project,tmp_path/'history.pdf')
        assert len(w.history.undo_stack)==3
        w.open_source(VIDEO);wait(app,lambda:w.controller.state==State.SOURCE_READY)
        assert not w.history.undo_stack and not w.history.redo_stack
    finally:
        w.close();wait(app,lambda:not w.isVisible())
def test_history_limit_and_noop_branch():
    h=EditHistory(limit=2);project=object();h.reset(project)
    a=Snapshot(('a',),'a');b=Snapshot(('b',),'b')
    assert h.record(project,a,a) is False
    assert not h.undo_stack
    for i in range(4):h.record(project,Snapshot((i,),None),Snapshot((i+1,),None))
    assert len(h.undo_stack)==2
    assert h.undo(project)==Snapshot((3,),None)
    assert h.redo(project)==Snapshot((4,),None)
