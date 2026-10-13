import json
from pathlib import Path
from types import SimpleNamespace
import pytest
from slide_core import cache
from slide_core.preparation import prepare_samples
from slide_core.analysis import analyze_project
from slide_core.config import AnalysisSettings
from slide_core.lazy_frames import ensure_sample_image
from tests.test_native_keyframes_integration import make,helper

@pytest.fixture
def half_project(tmp_path,monkeypatch,helper):
    source=make(tmp_path/'v.mp4');monkeypatch.setenv('SLIDE_NATIVE_KEYFRAME_HELPER',str(helper))
    prepared=prepare_samples(source,tmp_path/'cache')
    p,_=analyze_project(source,AnalysisSettings(roi_mode='full'),tmp_path/'cache',prepared=prepared)
    yield p,prepared
    prepared.discard()


def test_lazy_write_honors_free_disk_reserve(half_project,monkeypatch):
    p,prepared=half_project;target=p.samples[1]
    before=(prepared.directory/'manifest.json').read_bytes()
    monkeypatch.setattr(cache.shutil,'disk_usage',lambda _:SimpleNamespace(free=0))
    with pytest.raises(cache.CacheBudgetExceeded):ensure_sample_image(p,target)
    assert not Path(target.cache_path).exists()
    assert (prepared.directory/'manifest.json').read_bytes()==before


def test_lazy_write_updates_completed_manifest_bytes(half_project):
    p,prepared=half_project;target=p.samples[1]
    before=json.loads((prepared.directory/'manifest.json').read_text())['bytes']
    ensure_sample_image(p,target)
    after=json.loads((prepared.directory/'manifest.json').read_text())
    assert after['complete'] is True
    assert after['bytes']==before+Path(target.cache_path).stat().st_size


def test_interrupted_lazy_temporary_is_prunable(half_project):
    p,prepared=half_project
    (prepared.directory/'skipped_000001.tmp').write_bytes(b'partial jpeg')
    prepared.cache_pin.close()
    try:
        assert prepared.directory in cache.prune_cache(prepared.cache_root,now=10**12)
        assert not prepared.directory.exists()
    finally:(prepared.directory/'skipped_000001.tmp').unlink(missing_ok=True)

@pytest.mark.parametrize('limit',['session','root'])
def test_completed_owner_keeps_original_budget_limits(tmp_path,limit):
    from tests.test_cache import jpeg
    data=jpeg()
    with cache.CacheSession(tmp_path,min_free_bytes=0,session_limit=len(data) if limit=='session' else 10*len(data),root_limit=1500 if limit=='root' else 100000) as session:
        session.write_jpeg(0,data);session.complete();pin=session.retain()
    try:
        with pytest.raises(cache.CacheBudgetExceeded):pin.write_lazy_jpeg(1,data)
        assert not (session.directory/'skipped_000001.jpg').exists()
    finally:pin.close()


def test_lazy_write_cannot_use_another_generation_owner(half_project,tmp_path):
    p,prepared=half_project
    with cache.CacheSession(tmp_path/'foreign',min_free_bytes=0) as other:
        other.complete();pin=other.retain()
    try:
        with pytest.raises(Exception):ensure_sample_image(p,p.samples[1],cache_pin=pin)
        assert not (other.directory/'skipped_000001.jpg').exists()
        assert not Path(p.samples[1].cache_path).exists()
    finally:pin.close()
