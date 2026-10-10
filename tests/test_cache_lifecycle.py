"""Regression coverage for public-beta cache ownership and automatic cleanup."""
import gc,json,time,subprocess,sys
from pathlib import Path
from fractions import Fraction
import pytest
from slide_core.cache import CacheSession,CacheBudgetExceeded,prune_cache
from slide_core.analysis import analyze_project
from slide_core.config import AnalysisSettings
from slide_core.models import CancelToken
from slide_core.media import MediaError
from slide_core.pts import sample_stream
from tests.test_cache import jpeg
from tests.test_sampling import make_video

def expire(session):
    path=session.directory/'manifest.json'
    m=json.loads(path.read_text());m['updated_at']=time.time()-100000
    path.write_text(json.dumps(m))

def test_sampling_session_automatically_prunes_expired_cache(tmp_path):
    old=CacheSession(tmp_path,min_free_bytes=0)
    old.write_jpeg(0,jpeg());old.complete();old.close();expire(old)
    with CacheSession(tmp_path,min_free_bytes=0,auto_prune=True) as new:
        assert not old.directory.exists()
        assert new.write_jpeg(0,jpeg()).is_file()

def test_pressure_evicts_only_unused_cache_and_preserves_live_pin(tmp_path):
    live=CacheSession(tmp_path,min_free_bytes=0,root_limit=4096)
    live_path=live.write_jpeg(0,jpeg());live.complete()
    pin=live.retain();live.close();expire(live)
    try:
        for i in range(12):
            with CacheSession(tmp_path,min_free_bytes=0,root_limit=4096,auto_prune=True) as new:
                new.write_jpeg(0,jpeg());new.complete()
            assert live_path.read_bytes()==jpeg()
    finally:pin.close()
    assert live.directory in prune_cache(tmp_path,now=time.time()+100000)

def test_failed_writer_discards_partial_cache_without_hiding_error(tmp_path):
    with pytest.raises(ValueError,match='original'):
        with CacheSession(tmp_path,min_free_bytes=0,discard_on_error=True) as new:
            new.write_jpeg(0,jpeg())
            raise ValueError('original')
    assert not list(tmp_path.glob('session-*'))

def test_sampling_cancel_discards_partial_cache(tmp_path,monkeypatch):
    source=make_video(tmp_path/'source.mp4',duration=2,fps=4)
    token=CancelToken()
    original=CacheSession.write_jpeg
    def write_and_cancel(self,index,data):
        result=original(self,index,data);token.cancel();return result
    monkeypatch.setattr(CacheSession,'write_jpeg',write_and_cancel)
    with pytest.raises(MediaError,match="Cancelled"):
        sample_stream(source,tmp_path/'cache',cancelled=token,fps=Fraction(1))
    assert not list((tmp_path/'cache').glob('session-*'))

def test_cached_reanalysis_shares_project_lifetime_protection(tmp_path):
    source=make_video(tmp_path/'source.mp4',duration=2,fps=4)
    root=tmp_path/'cache'
    first,_=analyze_project(source,AnalysisSettings(roi_mode='full'),root)
    directory=Path(first.samples[0].cache_path).parent
    assert prune_cache(root,now=time.time()+100000)==()
    second,_=analyze_project(source,AnalysisSettings(roi_mode='full'),root,previous=first)
    del first;gc.collect()
    assert prune_cache(root,now=time.time()+100000)==()
    assert Path(second.samples[0].cache_path).is_file()
    del second;gc.collect()
    assert directory in prune_cache(root,now=time.time()+100000)

def test_other_process_cannot_prune_project_pin(tmp_path):
    session=CacheSession(tmp_path,min_free_bytes=0)
    file=session.write_jpeg(0,jpeg());session.complete()
    pin=session.retain();session.close();expire(session)
    try:
        code="from slide_core.cache import prune_cache; import sys,time; assert prune_cache(sys.argv[1],now=time.time()+100000)==()"
        subprocess.run([sys.executable,'-c',code,str(tmp_path)],check=True,timeout=10)
        assert file.is_file()
    finally:pin.close()

def test_locked_capacity_fails_without_deleting_active_session(tmp_path):
    with CacheSession(tmp_path,min_free_bytes=0,root_limit=4096) as active:
        path=active.write_jpeg(0,jpeg())
        with CacheSession(tmp_path,min_free_bytes=0,root_limit=4096,auto_prune=True) as other:
            with pytest.raises(CacheBudgetExceeded):other.write_jpeg(0,jpeg())
        assert path.read_bytes()==jpeg()

def test_cleanup_error_preserves_original_failure(tmp_path,monkeypatch):
    from contextlib import contextmanager
    from slide_core.cache import LeaseBusy
    @contextmanager
    def blocked(root):
        raise LeaseBusy('Another maintenance operation')
        yield
    with pytest.raises(ValueError,match='original decode failure'):
        with CacheSession(tmp_path,min_free_bytes=0,discard_on_error=True) as session:
            session.write_jpeg(0,jpeg())
            monkeypatch.setattr('slide_core.cache._budget_lock',blocked)
            raise ValueError('original decode failure')

def test_failed_prune_keeps_owner_manifest_for_retry(tmp_path,monkeypatch):
    session=CacheSession(tmp_path,min_free_bytes=0)
    session.write_jpeg(0,jpeg());session.complete();session.close();expire(session)
    original=Path.unlink
    def denied(self,*a,**k):
        if self.suffix=='.jpg':raise PermissionError('temporary denial')
        return original(self,*a,**k)
    with monkeypatch.context() as m:
        m.setattr(Path,'unlink',denied)
        assert prune_cache(tmp_path)==()
    assert (session.directory/'manifest.json').is_file()
    assert session.directory in prune_cache(tmp_path)

def test_disk_pressure_reclaims_unused_cache_before_free_reserve_failure(tmp_path,monkeypatch):
    from collections import namedtuple
    old=CacheSession(tmp_path,min_free_bytes=0)
    old.write_jpeg(0,jpeg());old.complete();old.close()
    live=CacheSession(tmp_path,min_free_bytes=0)
    kept=live.write_jpeg(0,jpeg());live.complete()
    pin=live.retain();live.close()
    usage=namedtuple('usage','total used free')
    try:
        with CacheSession(tmp_path,min_free_bytes=1024,auto_prune=True) as new:
            monkeypatch.setattr('slide_core.cache.shutil.disk_usage',
                                lambda _:usage(100000,0,192 if old.directory.exists() else 100000))
            assert new.write_jpeg(0,jpeg()).is_file()
        assert not old.directory.exists()
        assert kept.read_bytes()==jpeg()
    finally:pin.close()

def test_manifest_publication_failure_discards_partial_cache(tmp_path,monkeypatch):
    import slide_core.cache as cache
    original=cache.os.replace
    def denied(source,target):
        if Path(source).name=='manifest.tmp':raise OSError('manifest publish failure')
        return original(source,target)
    with pytest.raises(OSError,match='manifest publish failure'):
        with CacheSession(tmp_path,min_free_bytes=0,discard_on_error=True) as session:
            session.write_jpeg(0,jpeg())
            monkeypatch.setattr(cache.os,'replace',denied)
            session.complete()
    assert not list(tmp_path.glob('session-*'))
