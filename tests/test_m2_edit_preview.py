"""Selection and rapid scrubbing regressions using real offscreen Qt."""
from dataclasses import replace
from fractions import Fraction
from uuid import UUID
P0=str(UUID(int=1));P2=str(UUID(int=2));P4=str(UUID(int=3))
from threading import Event
import pytest
from PIL import Image
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from gui.window import Window
from gui.state import State
from gui.playback import PlaybackClock
from tests.export_fixtures import make_project
from tests.qt_fixtures import spin

@pytest.fixture
def editor(tmp_path):
    app=QApplication.instance() or QApplication([])
    project=make_project(tmp_path)
    samples=[]
    for i in range(80):
        path=tmp_path/f'{i}.png'
        Image.new('RGB',(80,48),(i*3,20,30)).save(path)
        samples.append(replace(project.samples[0],sample_id=f's{i}',source_pts=i,ordinal=i,
                               cache_path=str(path)))
    project.samples=tuple(samples)
    project.pages=[replace(project.pages[0],page_id={0:P0,2:P2,4:P4}[i],representative_sample_id=f's{i}') for i in (0,2,4)]
    project.source=replace(project.source,metadata=tuple((k,80 if k=='duration_s' else v) for k,v in project.source.metadata))
    w=Window();w.show()
    w.controller.project=project;w.controller.source=project.source
    w.controller.state=State.REVIEW_READY;w.controller.focus_page_id=P0
    w.settings=project.settings;w.history.reset(project)
    w.page_model.set_project(project);w.timeline.set_project(project)
    w.images.switch(project.analysis_generation)
    w.player=PlaybackClock([s.actual_time for s in samples],80)
    w.slider.setRange(0,79);w._set_stage('review')
    w._select_page_ids((P0,),P0)
    try:yield app,w,project
    finally:
        w.close();spin(app,lambda:not w.isVisible())

def test_replace_uses_selected_page_and_restores_history(editor):
    app,w,p=editor
    def click(row,mod=Qt.KeyboardModifier.NoModifier):
        w.page_view.scrollTo(w.page_model.index(row));app.processEvents()
        QTest.mouseClick(w.page_view.viewport(),Qt.MouseButton.LeftButton,mod,
                        w.page_view.visualRect(w.page_model.index(row)).center())
        app.processEvents()
    click(0);click(1,Qt.KeyboardModifier.ControlModifier);click(1,Qt.KeyboardModifier.ControlModifier)
    assert w.selected_page_ids()==(P0,)
    assert w.controller.focus_page_id==P2
    w.seek_index(7)
    before={x.page_id:x.representative_sample_id for x in p.pages}
    assert w.replace_button.isEnabled()
    QTest.mouseClick(w.replace_button,Qt.MouseButton.LeftButton)
    after={x.page_id:x.representative_sample_id for x in p.pages}
    assert after=={**before,P0:'s7'}
    assert w.selected_page_ids()==(P0,)
    w.undo_edit()
    assert {x.page_id:x.representative_sample_id for x in p.pages}==before
    assert w.selected_page_ids()==(P0,) and w.controller.focus_page_id==P2
    assert w.current_index==7
    w.redo_edit()
    assert {x.page_id:x.representative_sample_id for x in p.pages}==after
    assert w.selected_page_ids()==(P0,) and w.controller.focus_page_id==P0

@pytest.mark.parametrize('selection,state',[((),State.REVIEW_READY),((P0,P2),State.REVIEW_READY),((P0,),State.EXPORTING)])
def test_replace_direct_call_rejects_invalid_selection_or_state(editor,selection,state):
    app,w,p=editor
    w._select_page_ids(selection,P0);w.seek_index(7)
    w.controller.state=state;w._refresh_actions()
    before=tuple(p.pages);revision=p.revision
    try:
        assert not w.replace_button.isEnabled()
        w.replace_page()
        assert tuple(p.pages)==before and p.revision==revision
    finally:w.controller.state=State.REVIEW_READY

def test_last_scrub_frame_is_painted_and_thumbnails_finish(editor,monkeypatch):
    from gui import images
    app,w,p=editor
    real=images.QImage;entered=Event();release=Event()
    def delayed(*args,**kwargs):
        if args and isinstance(args[0],str):
            entered.set()
            assert release.wait(5)
        return real(*args,**kwargs)
    delayed.Format=real.Format
    monkeypatch.setattr(images,'QImage',delayed)
    try:
        w.seek_index(0);assert entered.wait(2)
        for i in range(1,80):w.seek_index(i)
        w._pump_all_thumbs()
        with w.images._cv:assert len(w.images._pending)<=16
        release.set()
        spin(app,lambda:not w.images._pending and not w.images._reading and w.images._awaiting_delivery==0)
        assert w.images.cached(w._image_key(79)) is not None
        assert not w.preview.pixmap().isNull()
        assert w._current_image.pixelColor(0,0).red()==237
        spin(app,lambda:w._thumb_cursor==len(p.pages))
    finally:release.set()
