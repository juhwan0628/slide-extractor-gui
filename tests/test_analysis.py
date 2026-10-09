from fractions import Fraction
from pathlib import Path
import pytest
from slide_core.config import AnalysisSettings
from slide_core.analysis import analyze_project,requires_reanalysis
from slide_core.media import probe_source,MediaError
from slide_core.models import Rect, CancelToken
from tests.test_sampling import make_video


def test_cached_reanalysis_does_not_decode_source(tmp_path):
    source=make_video(tmp_path/'video.mp4',duration=4,fps=4)
    full=AnalysisSettings(roi_mode='full')
    project,_=analyze_project(source,full,tmp_path/'cache')
    changed=AnalysisSettings(roi_mode='manual',effective_roi=Rect(2,2,85,52))
    def prohibited(*args,**kwargs):raise AssertionError('Second video decoding forbidden')
    second,_=analyze_project(source,changed,tmp_path/'cache',previous=project,sampler=prohibited)
    assert second.cache_generation==project.cache_generation
    assert second.analysis_generation!=project.analysis_generation
    assert second.settings.effective_roi==changed.effective_roi
    assert project.settings.roi_mode=='full'
    assert requires_reanalysis(project,changed)


def test_fps_change_requires_new_cache_generation(tmp_path):
    source=make_video(tmp_path/'video.mp4',duration=4,fps=4)
    a,_=analyze_project(source,AnalysisSettings(roi_mode='full'),tmp_path/'cache')
    b,_=analyze_project(source,AnalysisSettings(fps=.5,roi_mode='full'),
                        tmp_path/'cache',previous=a)
    assert a.cache_generation!=b.cache_generation
    assert len(a.samples)==4 and len(b.samples)==2


def test_failure_keeps_previous_project_unchanged(tmp_path):
    source=make_video(tmp_path/'video.mp4',duration=3,fps=4)
    project,_=analyze_project(source,AnalysisSettings(roi_mode='full'),tmp_path/'cache')
    before=(project.pages[:],project.revision,project.cache_generation)
    target=AnalysisSettings(roi_mode='manual',effective_roi=Rect(0,0,10,10))
    with pytest.raises(ValueError,match='64x36'):
        analyze_project(source,target,tmp_path/'cache',previous=project)
    assert before==(project.pages,project.revision,project.cache_generation)


def test_missing_cache_fails_closed(tmp_path):
    source=make_video(tmp_path/'video.mp4',duration=2,fps=4)
    project,_=analyze_project(source,AnalysisSettings(roi_mode='full'),tmp_path/'cache')
    Path(project.samples[0].cache_path).unlink()
    with pytest.raises(MediaError,match='CacheUnavailable'):
        analyze_project(source,AnalysisSettings(roi_mode='full'),tmp_path/'cache',previous=project)


def test_initial_black_frame_fallback_and_cancel(tmp_path):
    source=make_video(tmp_path/'video.mp4',duration=2,fps=4)
    project,_=analyze_project(source,AnalysisSettings(roi_mode='auto'),tmp_path/'cache')
    assert project.pages and project.settings.effective_roi is not None
    cancel=CancelToken();cancel.cancel()
    with pytest.raises(Exception):
        analyze_project(source,AnalysisSettings(roi_mode='full'),tmp_path/'cache',cancel_token=cancel)


def test_auto_derived_roi_does_not_mark_same_user_settings_dirty(tmp_path):
    source=make_video(tmp_path/'video.mp4',duration=2,fps=4)
    requested=AnalysisSettings(roi_mode='auto')
    project,_=analyze_project(source,requested,tmp_path/'cache')
    assert not requires_reanalysis(project,requested)


def test_reanalysis_rejects_replacement_source(tmp_path):
    first=make_video(tmp_path/'first.mp4',duration=2,fps=4)
    second=make_video(tmp_path/'second.mp4',duration=3,fps=4)
    project,_=analyze_project(first,AnalysisSettings(roi_mode='full'),tmp_path/'cache')
    with pytest.raises(MediaError,match='SourceChanged'):
        analyze_project(second,AnalysisSettings(roi_mode='full'),tmp_path/'cache',previous=project)


def test_analysis_failure_removes_only_newly_created_cache(tmp_path):
    source=make_video(tmp_path/'video.mp4',duration=2,fps=4)
    with pytest.raises(ValueError,match='64x36'):
        analyze_project(source,AnalysisSettings(roi_mode='manual',effective_roi=Rect(0,0,12,12)),tmp_path/'cache')
    assert not list((tmp_path/'cache').glob('session-*'))
