from dataclasses import replace
import numpy as np
import pytest
from slide_core.analysis import analyze_project,requires_reanalysis
from slide_core.config import AnalysisSettings,DetectorConfig
from slide_core.models import CancelToken
from slide_core.media import MediaError
from slide_core.preparation import prepare_samples
from tests.media_fixtures import make_video

def settings():
    return AnalysisSettings(roi_mode='full',detector=DetectorConfig(algorithm='spatial-groups-v1'))

def test_explicit_spatial_analysis_preserves_brief_page(tmp_path,monkeypatch):
    source=make_video(tmp_path/'v.mp4',duration=4,fps=4)
    def images(samples,region,*args):
        for value in (255,255,0,255):yield np.full(region.valid.shape,value,np.uint8)
    monkeypatch.setattr('slide_core.analysis._prepared',images)
    events=[]
    p,_=analyze_project(source,settings(),tmp_path/'cache',progress=lambda *x:events.append(x))
    assert len(p.pages)==3
    assert all(t.reason=='spatial_change' for t in p.transitions)
    assert p.settings.detector.algorithm=='spatial-groups-v1'
    assert not requires_reanalysis(p,settings())

def test_detector_change_invalidates_detection(tmp_path):
    source=make_video(tmp_path/'v.mp4',duration=3,fps=4)
    p,_=analyze_project(source,settings(),tmp_path/'cache')
    assert requires_reanalysis(p,replace(settings(),detector=DetectorConfig()))
    assert not requires_reanalysis(p,settings())

def test_spatial_accepts_half_prepared(tmp_path):
    source=make_video(tmp_path/'v.mp4',duration=3,fps=4)
    prepared=prepare_samples(source,tmp_path/'cache')
    try:
        observations=tuple(replace(s,ordinal=i) for i,s in enumerate(prepared.samples[::2]))
        p,_=analyze_project(source,settings(),tmp_path/'cache',prepared=replace(prepared,samples=observations,selection_policy='half',decoder_backend='native-idr'))
        assert p.selection_policy=='half' and p.observation_sample_ids==tuple(s.sample_id for s in observations)
        assert prepared.samples
    finally:prepared.discard()

def test_cancel_preserves_previous_project(tmp_path):
    source=make_video(tmp_path/'v.mp4',duration=3,fps=4)
    p,_=analyze_project(source,settings(),tmp_path/'cache')
    before=(p.pages[:],p.revision,p.cache_generation)
    token=CancelToken();token.cancel()
    with pytest.raises(Exception):analyze_project(source,settings(),tmp_path/'cache',previous=p,cancel_token=token)
    assert before==(p.pages,p.revision,p.cache_generation)

def test_progress_is_monotonic_and_cancel_in_rank(tmp_path):
    source=make_video(tmp_path/'v.mp4',duration=10,fps=4)
    p,_=analyze_project(source,settings(),tmp_path/'cache')
    before=(p.pages[:],p.cache_generation)
    token=CancelToken();ratios=[]
    def progress(stage,done,total):
        if stage in ('grouping','representative_selection') and total:
            ratios.append(done/total)
            if done/total>=.5:token.cancel()
    with pytest.raises(Exception):
        analyze_project(source,settings(),tmp_path/'cache',previous=p,cancel_token=token,progress=progress)
    assert ratios==sorted(ratios)
    assert before==(p.pages,p.cache_generation)
    assert all(__import__('pathlib').Path(s.cache_path).is_file() for s in p.samples)

def test_spatial_profile_has_pass_and_disk_accounting(tmp_path):
    from slide_core.profiling import AnalysisProfile
    source=make_video(tmp_path/'v.mp4',duration=3,fps=4);profile=AnalysisProfile()
    p,_=analyze_project(source,settings(),tmp_path/'cache',profile=profile)
    report=profile.report()
    assert report['seconds']['representative_selection']>0
    assert report['seconds']['gray_staging']>0
    assert report['gray_stage_bytes']==len(p.samples)*96*64

@pytest.mark.parametrize('scan',[0,1,2])
def test_rank_scan_cancel_preserves_project_and_closes_stage(tmp_path,monkeypatch,scan):
    import slide_core.spatial_groups as module
    source=make_video(tmp_path/'v.mp4',duration=4,fps=4)
    # Constant images ensure one group, so each scan reads the complete timeline.
    def images(samples,region,*args):
        for _ in samples:yield np.full(region.valid.shape,255,np.uint8)
    monkeypatch.setattr('slide_core.analysis._prepared',images)
    p,_=analyze_project(source,settings(),tmp_path/'cache')
    before=(p.pages[:],p.revision,p.cache_generation,p.samples)
    token=CancelToken();opened=[];real_file=module.tempfile.TemporaryFile
    def tracked(*a,**kw):
        f=real_file(*a,**kw);opened.append(f);return f
    monkeypatch.setattr(module.tempfile,'TemporaryFile',tracked)
    real_rank=module.select_representative;checks=[]
    def ranking(read,start,end,valid,config,advance):
        def check():
            checks.append(1)
            if len(checks)==1+scan*(end-start):token.cancel()
            advance()
        return real_rank(read,start,end,valid,config,check)
    monkeypatch.setattr(module,'select_representative',ranking)
    from slide_core.models import CancelledError
    with pytest.raises(CancelledError):
        analyze_project(source,settings(),tmp_path/'cache',previous=p,cancel_token=token)
    assert len(checks)==1+scan*len(p.samples)
    assert opened and all(f.closed for f in opened)
    assert before==(p.pages,p.revision,p.cache_generation,p.samples)
    assert all(__import__('pathlib').Path(s.cache_path).is_file() for s in p.samples)
