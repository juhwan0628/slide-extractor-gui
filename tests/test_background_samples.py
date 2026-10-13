import time
from threading import Event
from dataclasses import replace
from fractions import Fraction
from pathlib import Path
import pytest
from slide_core.config import AnalysisSettings
from slide_core.analysis import analyze_project
from slide_core.media import probe_source,MediaError
from slide_core.models import CancelToken,CancelledError
from tests.media_fixtures import make_video


def test_ready_samples_analyze_without_second_decoder(tmp_path,monkeypatch):
    from slide_core.preparation import prepare_samples
    source=make_video(tmp_path/'video.mp4',duration=4,fps=4)
    prepared=prepare_samples(source,tmp_path/'cache')
    def forbidden(*a,**kw):raise AssertionError('second decoder')
    monkeypatch.setattr('slide_core.analysis.keyframe_stream',forbidden)
    project,_=analyze_project(source,AnalysisSettings(roi_mode='full'),tmp_path/'cache',prepared=prepared)
    assert project.samples==prepared.samples
    assert project.cache_generation==prepared.cache_generation
    assert len(project.samples)==4
    again,_=analyze_project(source,AnalysisSettings(roi_mode='manual',effective_roi=project.settings.effective_roi),tmp_path/'cache',prepared=prepared)
    assert again.samples==project.samples


def test_prepared_source_and_algorithm_must_match(tmp_path):
    from slide_core.preparation import prepare_samples
    source=make_video(tmp_path/'video.mp4',duration=2,fps=4)
    prepared=prepare_samples(source,tmp_path/'cache')
    with pytest.raises(ValueError,match='algorithm'):
        analyze_project(source,AnalysisSettings(),tmp_path/'cache',prepared=replace(prepared,sampling_algorithm='bucket-first-v1'))
    other=make_video(tmp_path/'other.mp4',duration=3,fps=4)
    with pytest.raises(MediaError,match='SourceChanged'):
        analyze_project(other,AnalysisSettings(),tmp_path/'cache',prepared=prepared)


def test_analysis_waits_for_same_running_preparation(tmp_path,monkeypatch):
    from gui import sample_preparation as background
    source=make_video(tmp_path/'video.mp4',duration=2,fps=4)
    entered=Event();release=Event();calls=[];real=background.prepare_samples
    def delayed(*a,**kw):
        calls.append(1);entered.set();assert release.wait(3);return real(*a,**kw)
    monkeypatch.setattr(background,'prepare_samples',delayed)
    task=background.BackgroundSamples(source,tmp_path/'cache')
    try:
        assert entered.wait(3) and not task.ready.is_set()
        release.set();prepared=task.wait(CancelToken())
        project,_=analyze_project(source,AnalysisSettings(roi_mode='full'),tmp_path/'cache',prepared=prepared)
        assert len(calls)==1 and len(project.samples)==2
    finally:
        task.close();assert task.done.wait(3)
    assert not list((tmp_path/'cache').rglob('*.jpg'))


def test_cancelled_waiter_does_not_block(tmp_path,monkeypatch):
    from gui import sample_preparation as background
    entered=Event();release=Event()
    def delayed(*a,**kw):
        entered.set();release.wait(3);kw['cancel_token'].raise_if_cancelled()
    monkeypatch.setattr(background,'prepare_samples',delayed)
    task=background.BackgroundSamples(None,tmp_path/'cache')
    try:
        assert entered.wait(3)
        token=CancelToken();token.cancel()
        with pytest.raises(CancelledError):task.wait(token)
    finally:
        task.close();release.set();assert task.done.wait(3)


@pytest.mark.parametrize('early',[True,False])
def test_window_silent_preparation_and_analyze_click(tmp_path,monkeypatch,early):
    from PySide6.QtWidgets import QApplication,QMessageBox
    from gui.window import Window
    from gui.state import State
    from gui import sample_preparation as background
    from slide_core import pts
    from tests.qt_fixtures import spin
    app=QApplication.instance() or QApplication([])
    source=make_video(tmp_path/'video.mp4',duration=4,fps=4)
    entered=Event();release=Event();calls=[];warnings=[]
    real_prepare=background.prepare_samples;real_ffmpeg=pts._ffmpeg
    def delayed(*args,**kwargs):
        entered.set()
        while not release.wait(.01):kwargs['cancel_token'].raise_if_cancelled()
        return real_prepare(*args,**kwargs)
    def command(*args,**kwargs):
        calls.append(1);return real_ffmpeg(*args,**kwargs)
    monkeypatch.setattr(background,'prepare_samples',delayed)
    monkeypatch.setattr(pts,'_ffmpeg',command)
    monkeypatch.setattr(QMessageBox,'warning',lambda *a,**kw:warnings.append(a[2]))
    window=Window();window.show()
    try:
        window.open_source(source.path)
        spin(app,lambda:window.controller.state==State.SOURCE_READY and entered.is_set())
        text=window.info.text()
        assert window.stage=='preparation' and window.analyze_button.isEnabled()
        assert window.advanced_button.isEnabled() and window.jobs.worker is None
        app.processEvents();assert window.info.text()==text
        if not early:
            release.set();spin(app,lambda:window._sample_preparation.ready.is_set())
        window.analyze()
        assert window.stage=='analyzing'
        release.set();spin(app,lambda:window.controller.state==State.REVIEW_READY,timeout=10)
        assert len(calls)==2 and len(window.controller.project.samples)==4
        assert not warnings
    finally:
        release.set();window.close();spin(app,lambda:not window.isVisible())
