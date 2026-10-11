"""Preparation retry and strictly owned interrupted-cache regressions."""
import os,sys,subprocess,time
from pathlib import Path
import pytest
from slide_core import cache
from tests.test_cache import jpeg

@pytest.mark.parametrize('temporary',['00000001.tmp','manifest.tmp'])
def test_crashed_writer_cache_is_pruned(tmp_path,temporary):
    code="""
import os,sys
from pathlib import Path
from slide_core.cache import CacheSession
from tests.test_cache import jpeg
s=CacheSession(Path(sys.argv[1]),min_free_bytes=0)
s.write_jpeg(0,jpeg())
original=os.replace
def crash(src,dst):
    if Path(src).name==sys.argv[2]:os._exit(77)
    return original(src,dst)
os.replace=crash
if sys.argv[2]=='manifest.tmp':s.complete()
else:s.write_jpeg(1,jpeg())
"""
    result=subprocess.run([sys.executable,'-c',code,str(tmp_path),temporary],
                          cwd=Path(__file__).resolve().parents[1],timeout=10)
    assert result.returncode==77
    directory=next(tmp_path.glob('session-*'))
    assert (directory/temporary).is_file()
    assert cache.prune_cache(tmp_path,now=time.time()+100000)==(directory,)
    assert not directory.exists()

def test_live_writer_with_temporary_is_not_removed(tmp_path):
    s=cache.CacheSession(tmp_path,min_free_bytes=0)
    try:
        (s.directory/'00000001.tmp').write_bytes(b'partial')
        assert cache.prune_cache(tmp_path,now=time.time()+100000)==()
        assert not cache.discard_cache(tmp_path,s.directory)
        assert (s.directory/'00000001.tmp').read_bytes()==b'partial'
    finally:s.close()
    assert cache.discard_cache(tmp_path,s.directory)

@pytest.mark.parametrize('name',['1.tmp','1234567.tmp','custom.tmp','00000001.tmp.bak'])
def test_unknown_temporary_is_preserved(tmp_path,name):
    s=cache.CacheSession(tmp_path,min_free_bytes=0);s.close()
    foreign=s.directory/name;foreign.write_bytes(b'keep')
    assert cache.prune_cache(tmp_path,now=time.time()+100000)==()
    assert not cache.discard_cache(tmp_path,s.directory)
    assert foreign.read_bytes()==b'keep'

@pytest.mark.parametrize('link',['symlink','hardlink'])
def test_linked_temporary_is_preserved(tmp_path,link):
    s=cache.CacheSession(tmp_path,min_free_bytes=0);s.close()
    precious=tmp_path/'precious';precious.write_bytes(b'keep')
    temp=s.directory/'00000001.tmp'
    if link=='symlink':temp.symlink_to(precious)
    else:os.link(precious,temp)
    assert not cache.discard_cache(tmp_path,s.directory)
    assert temp.exists() and precious.read_bytes()==b'keep'

def test_lock_cleanup_denial_can_be_retried(tmp_path,monkeypatch):
    s=cache.CacheSession(tmp_path,min_free_bytes=0)
    s.write_jpeg(0,jpeg());s.complete();s.close()
    original=Path.unlink
    def denied(self,*a,**kw):
        if self==s.directory/'lease.lock':raise PermissionError('temporary denial')
        return original(self,*a,**kw)
    with monkeypatch.context() as m:
        m.setattr(Path,'unlink',denied)
        assert cache.prune_cache(tmp_path,now=time.time()+100000)==()
    assert (s.directory/'manifest.json').is_file()
    assert cache.prune_cache(tmp_path,now=time.time()+100000)==(s.directory,)
    assert not s.directory.exists()

def test_analyze_retries_transient_preparation_failure(tmp_path,monkeypatch):
    from PySide6.QtWidgets import QApplication,QMessageBox
    from gui import window as wm,sample_preparation as bg
    from gui.state import State
    from slide_core.media import MediaError
    from tests.test_sampling import make_video
    from tests.test_gui_smoke import spin
    app=QApplication.instance() or QApplication([])
    monkeypatch.setattr(wm,'gettempdir',lambda:str(tmp_path))
    monkeypatch.setattr(QMessageBox,'warning',lambda *a,**kw:None)
    monkeypatch.setattr(QMessageBox,'question',lambda *a,**kw:QMessageBox.StandardButton.Yes)
    source=make_video(tmp_path/'video.mp4',duration=4,fps=4)
    real=bg.prepare_samples;calls=[]
    def transient(*a,**kw):
        calls.append(1)
        if len(calls)==1:raise MediaError('temporary decoder failure',code='DecodeFailed')
        return real(*a,**kw)
    monkeypatch.setattr(bg,'prepare_samples',transient)
    w=wm.Window();w.show()
    try:
        w.open_source(source.path)
        spin(app,lambda:w.controller.state==State.SOURCE_READY and w._sample_preparation.ready.is_set())
        failed=w._sample_preparation
        assert failed.error is not None
        # The first Analyze after a failed silent preparation is itself a retry.
        w.analyze()
        spin(app,lambda:w.jobs.worker is None)
        assert w.controller.state==State.REVIEW_READY
        assert w._sample_preparation is not failed and failed.done.is_set()
        assert len(calls)==2
        directory=w._sample_preparation.result.directory
        w.seek_index(1);w.add_page();w.return_to_preparation()
        spin(app,lambda:w._sample_preparation.done.is_set())
        assert w.stage=='empty' and not directory.exists()
    finally:
        w.close();spin(app,lambda:not w.isVisible())


def test_cancelled_preparation_retries_after_decoder_drains(tmp_path,monkeypatch):
    from threading import Event
    from PySide6.QtWidgets import QApplication,QMessageBox
    from gui import window as wm,sample_preparation as bg
    from gui.state import State
    from tests.test_sampling import make_video
    from tests.test_gui_smoke import spin
    app=QApplication.instance() or QApplication([])
    monkeypatch.setattr(wm,'gettempdir',lambda:str(tmp_path))
    monkeypatch.setattr(QMessageBox,'warning',lambda *a,**kw:None)
    source=make_video(tmp_path/'video.mp4',duration=4,fps=4)
    entered=Event();drained=Event();calls=[];real=bg.prepare_samples
    def delayed(*a,**kw):
        calls.append(1)
        if len(calls)==1:
            entered.set()
            try:
                while not kw['cancel_token'].cancelled:time.sleep(.005)
                kw['cancel_token'].raise_if_cancelled()
            finally:drained.set()
        assert drained.is_set()
        return real(*a,**kw)
    monkeypatch.setattr(bg,'prepare_samples',delayed)
    w=wm.Window();w.show()
    try:
        w.open_source(source.path)
        spin(app,lambda:w.controller.state==State.SOURCE_READY and entered.is_set())
        first=w._sample_preparation
        w.analyze();w.cancel()
        spin(app,lambda:w.jobs.worker is None)
        assert first.token.cancelled
        w.analyze();spin(app,lambda:w.controller.state==State.REVIEW_READY)
        assert len(calls)==2 and first.done.is_set()
        directory=w._sample_preparation.result.directory
    finally:
        w.close();spin(app,lambda:not w.isVisible())
    assert not directory.exists()

def test_cleanup_failure_blocks_gui_retry_without_second_decoder(tmp_path,monkeypatch):
    from PySide6.QtWidgets import QApplication,QMessageBox
    from gui import window as wm,sample_preparation as bg
    from gui.state import State
    from tests.test_sampling import make_video
    from tests.test_gui_smoke import spin
    app=QApplication.instance() or QApplication([])
    monkeypatch.setattr(wm,'gettempdir',lambda:str(tmp_path))
    warnings=[]
    monkeypatch.setattr(QMessageBox,'warning',lambda *a,**kw:warnings.append(a[2]))
    source=make_video(tmp_path/'video.mp4',duration=2,fps=4)
    calls=[]
    def failed(*a,**kw):
        calls.append(1);raise cache.CacheCleanupError('Owned cache cleanup blocked')
    monkeypatch.setattr(bg,'prepare_samples',failed)
    w=wm.Window();w.show()
    try:
        w.open_source(source.path)
        spin(app,lambda:w.controller.state==State.SOURCE_READY and w._sample_preparation.ready.is_set())
        w.analyze();spin(app,lambda:w.jobs.worker is None)
        w.analyze();spin(app,lambda:w.jobs.worker is None)
        assert len(calls)==1 and len(warnings)==2
        assert all('cleanup blocked' in x for x in warnings)
        assert w.controller.state==State.SOURCE_READY
    finally:w.close();spin(app,lambda:not w.isVisible())
