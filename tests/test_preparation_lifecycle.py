from pathlib import Path
from dataclasses import replace
from fractions import Fraction
from slide_core.models import CancelToken
from tests.test_sampling import make_video


def test_ready_one_fps_compacts_without_decode(tmp_path,monkeypatch):
    from gui import sample_preparation as background
    source=make_video(tmp_path/'video.mp4',duration=6,fps=4)
    first=background.BackgroundSamples(source,tmp_path/'cache',fps=1)
    original=first.wait(CancelToken())
    def forbidden(*a,**kw):raise AssertionError('unnecessary decoder')
    monkeypatch.setattr(background,'prepare_samples',forbidden)
    second=background.BackgroundSamples(source,tmp_path/'cache',fps=.5,predecessor=first)
    try:
        assert first.done.wait(3)
        result=second.wait(CancelToken())
        assert result.directory==original.directory
        assert [s.actual_time for s in result.samples]==[Fraction(0),Fraction(2),Fraction(4)]
        assert len(list(result.directory.glob('*.jpg')))==3
        assert result.cache_generation!=original.cache_generation
    finally:
        first.close();second.close();assert second.done.wait(3)
    assert not original.directory.exists()


def test_replacement_removes_cache_before_new_decode(tmp_path,monkeypatch):
    from gui import sample_preparation as background
    source=make_video(tmp_path/'video.mp4',duration=4,fps=4)
    first=background.BackgroundSamples(source,tmp_path/'cache',fps=.5)
    original=first.wait(CancelToken())
    real=background.prepare_samples
    def checked(*a,**kw):
        assert not original.directory.exists()
        return real(*a,**kw)
    monkeypatch.setattr(background,'prepare_samples',checked)
    second=background.BackgroundSamples(source,tmp_path/'cache',fps=1,predecessor=first)
    try:
        assert first.done.wait(3)
        assert len(second.wait(CancelToken()).samples)==4
    finally:
        first.close();second.close();assert second.done.wait(3)


def test_sparse_samples_use_time_buckets_not_array_parity(tmp_path):
    from slide_core.preparation import prepare_samples,compact_samples
    source=make_video(tmp_path/'video.mp4',duration=6,fps=4)
    original=prepare_samples(source,tmp_path/'cache',fps=1)
    sparse=replace(original,samples=tuple(original.samples[i] for i in (0,2,3,5)))
    try:
        result=compact_samples(sparse,fps=.5)
        assert [s.actual_time for s in result.samples]==[Fraction(0),Fraction(2),Fraction(5)]
        assert [s.grid_index for s in result.samples]==[0,1,2]
        assert len(list(result.directory.glob('*.jpg')))==3
    finally:original.discard()


def test_window_fps_change_compacts_adopted_cache_and_close_removes_it(tmp_path,monkeypatch):
    from PySide6.QtWidgets import QApplication,QMessageBox
    from gui.window import Window
    from gui.state import State
    from tests.test_gui_smoke import spin
    app=QApplication.instance() or QApplication([])
    source=make_video(tmp_path/'video.mp4',duration=6,fps=4)
    monkeypatch.setattr(QMessageBox,'question',lambda *a,**kw:QMessageBox.StandardButton.Yes)
    window=Window();window.show()
    try:
        window._fps_changed(0);window.open_source(source.path)
        spin(app,lambda:window.controller.state==State.SOURCE_READY)
        assert window._current_image is not None
        window.analyze();spin(app,lambda:window.controller.state==State.REVIEW_READY)
        directory=window._sample_preparation.result.directory
        # Backend reanalysis still compacts safely; Start over now discards the source.
        window._fps_changed(1);window.analyze()
        spin(app,lambda:window.controller.state==State.REVIEW_READY)
        prepared=window._sample_preparation.wait(CancelToken())
        assert window.controller.project.samples==prepared.samples
        assert prepared.directory==directory and len(prepared.samples)==3
        assert len(list(directory.glob('*.jpg')))==3
    finally:
        window.close();spin(app,lambda:not window.isVisible())
    assert not directory.exists()


def test_reader_barrier_waits_for_inflight_file(tmp_path,monkeypatch):
    import threading
    from PySide6.QtWidgets import QApplication
    from gui import images
    app=QApplication.instance() or QApplication([])
    entered=threading.Event();release=threading.Event();drained=threading.Event()
    real=images.QImage
    path=tmp_path/'image.jpg';real(10,10,real.Format.Format_RGB888).save(str(path))
    def delayed(*a,**kw):
        if a and isinstance(a[0],str):entered.set();release.wait(3)
        return real(*a,**kw)
    delayed.Format=real.Format
    monkeypatch.setattr(images,'QImage',delayed)
    loader=images.ImageLoader();loader.switch('old');loader.request(('old',1),path)
    try:
        assert entered.wait(3)
        loader.switch(None)
        thread=threading.Thread(target=lambda:(loader.wait_idle(),drained.set()),daemon=True)
        thread.start()
        assert not drained.wait(.05)
        release.set();assert drained.wait(3)
    finally:release.set();loader.stop()


def test_running_fps_change_drains_decoder_before_restart(tmp_path,monkeypatch):
    from threading import Event
    from gui import sample_preparation as background
    from slide_core.models import CancelledError
    entered=Event();release=Event();finished=Event();calls=[]
    source=make_video(tmp_path/'video.mp4',duration=4,fps=4)
    real=background.prepare_samples
    def delayed(*a,**kw):
        calls.append(kw['fps'])
        if len(calls)==1:
            entered.set();assert release.wait(3)
            try:kw['cancel_token'].raise_if_cancelled()
            finally:finished.set()
        assert finished.is_set()
        return real(*a,**kw)
    monkeypatch.setattr(background,'prepare_samples',delayed)
    first=background.BackgroundSamples(source,tmp_path/'cache',fps=1)
    assert entered.wait(3)
    second=background.BackgroundSamples(source,tmp_path/'cache',fps=.5,predecessor=first)
    try:
        assert not second.ready.wait(.05)
        release.set()
        assert len(second.wait(CancelToken()).samples)==2
        assert calls==[1,.5] and first.done.is_set()
    finally:release.set();second.close();assert second.done.wait(3)


def test_cleanup_failure_prevents_second_decoder(tmp_path,monkeypatch):
    from gui import sample_preparation as background
    import pytest
    source=make_video(tmp_path/'video.mp4',duration=4,fps=4)
    first=background.BackgroundSamples(source,tmp_path/'cache',fps=.5)
    original=first.wait(CancelToken())
    real_discard=type(original).discard
    def blocked(self):raise OSError('blocked cache')
    monkeypatch.setattr(type(original),'discard',blocked)
    def forbidden(*a,**kw):raise AssertionError('second cache allocated')
    monkeypatch.setattr(background,'prepare_samples',forbidden)
    second=background.BackgroundSamples(source,tmp_path/'cache',fps=1,predecessor=first)
    try:
        with pytest.raises(OSError,match='blocked cache'):second.wait(CancelToken())
        second.close();assert second.done.wait(3)
        third=background.BackgroundSamples(source,tmp_path/'cache',fps=.5,predecessor=second)
        try:
            with pytest.raises(OSError,match='blocked cache'):third.wait(CancelToken())
        finally:third.close();assert third.done.wait(3)
    finally:
        second.close();assert second.done.wait(3)
        real_discard(original)


def test_quick_fps_changes_leave_only_final_cache(tmp_path):
    from gui.sample_preparation import BackgroundSamples
    source=make_video(tmp_path/'video.mp4',duration=6,fps=4)
    first=BackgroundSamples(source,tmp_path/'cache',fps=1)
    first.wait(CancelToken())
    second=BackgroundSamples(source,tmp_path/'cache',fps=.5,predecessor=first)
    third=BackgroundSamples(source,tmp_path/'cache',fps=1,predecessor=second)
    try:
        result=third.wait(CancelToken())
        assert len(result.samples)==6
        assert len(list((tmp_path/'cache').glob('session-*')))==1
    finally:third.close();assert third.done.wait(3)
    assert not list((tmp_path/'cache').glob('session-*'))


def test_cancelled_decode_cleanup_failure_blocks_successor(tmp_path,monkeypatch):
    from gui import sample_preparation as background
    from slide_core import cache
    from slide_core.media import MediaError
    from slide_core.models import CancelledError
    import pytest
    source=make_video(tmp_path/'video.mp4',duration=4,fps=4)
    real=background.prepare_samples;remove=cache.discard_cache;calls=[]
    def cancelled(*a,**kw):
        calls.append(1)
        if len(calls)>1:raise AssertionError('decoder started with orphaned cache')
        return real(*a,**kw,progress=lambda *args:kw['cancel_token'].cancel())
    monkeypatch.setattr(background,'prepare_samples',cancelled)
    monkeypatch.setattr(cache,'discard_cache',lambda *a,**kw:False)
    first=background.BackgroundSamples(source,tmp_path/'cache',fps=1)
    second=None
    try:
        with pytest.raises((CancelledError,MediaError,OSError)):first.wait(CancelToken())
        first.close();assert first.done.wait(3)
        assert first.cleanup_error is not None
        second=background.BackgroundSamples(source,tmp_path/'cache',fps=.5,predecessor=first)
        with pytest.raises(OSError,match='cache'):second.wait(CancelToken())
        assert len(calls)==1
    finally:
        if second is not None:second.close();assert second.done.wait(3)
        for directory in (tmp_path/'cache').glob('session-*'):assert remove(tmp_path/'cache',directory)


def test_post_sampling_cancellation_reports_failed_cleanup(tmp_path,monkeypatch):
    from slide_core import preparation
    from slide_core.cache import CacheCleanupError,discard_cache
    import pytest
    source=make_video(tmp_path/'video.mp4',duration=2,fps=4)
    real=preparation.sample_stream;created=[];token=CancelToken()
    def cancel_after_sampling(*a,**kw):
        result=real(*a,**kw);created.append(result[1]);token.cancel();return result
    monkeypatch.setattr(preparation,'sample_stream',cancel_after_sampling)
    monkeypatch.setattr(preparation,'discard_cache',lambda *a,**kw:False)
    try:
        with pytest.raises(CacheCleanupError,match='cache'):
            preparation.prepare_samples(source,tmp_path/'cache',cancel_token=token)
    finally:
        for directory in created:assert discard_cache(tmp_path/'cache',directory)


def test_source_replacement_and_failed_probe_preserve_ownership(tmp_path,monkeypatch):
    from PySide6.QtWidgets import QApplication,QMessageBox
    from gui.window import Window
    from gui.state import State
    from tests.test_gui_smoke import spin
    app=QApplication.instance() or QApplication([])
    source=make_video(tmp_path/'video.mp4',duration=4,fps=4)
    other=make_video(tmp_path/'other.mp4',duration=6,fps=4)
    monkeypatch.setattr(QMessageBox,'warning',lambda *a,**kw:None)
    window=Window();window.show()
    try:
        window.open_source(source.path)
        spin(app,lambda:window.controller.state==State.SOURCE_READY)
        window.analyze();spin(app,lambda:window.controller.state==State.REVIEW_READY)
        original=window.controller.project;directory=window._sample_preparation.result.directory
        window.open_source(tmp_path/'missing.mp4')
        spin(app,lambda:window.jobs.worker is None)
        assert window.controller.project is original and directory.exists()
        window.open_source(other.path)
        spin(app,lambda:window.controller.state==State.SOURCE_READY and window._sample_preparation.ready.is_set())
        prepared=window._sample_preparation.wait(CancelToken())
        assert prepared.source==other and not directory.exists()
        new_directory=prepared.directory
    finally:window.close();spin(app,lambda:not window.isVisible())
    assert not new_directory.exists()
