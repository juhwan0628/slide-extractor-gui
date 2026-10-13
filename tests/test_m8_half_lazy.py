from pathlib import Path
import pytest
from slide_core.preparation import prepare_samples
from slide_core.analysis import analyze_project
from slide_core.config import AnalysisSettings
from slide_core.editing import add_page,replace_page
from slide_core.lazy_frames import ensure_sample_image
from slide_core.models import CancelToken
from slide_core.keyframe_export import export_project
from slide_core.keyframe_json import loads
from tests.test_native_keyframes_integration import make,helper


def test_skipped_key_lazy_preview_edit_export_and_stable_analysis(tmp_path,monkeypatch,helper):
    source=make(tmp_path/'v.mp4',duration=4);monkeypatch.setenv('SLIDE_NATIVE_KEYFRAME_HELPER',str(helper))
    prep=prepare_samples(source,tmp_path/'cache')
    try:
        p,_=analyze_project(source,AnalysisSettings(roi_mode='full'),tmp_path/'cache',prepared=prep)
        before=p.observation_sample_ids
        skipped=p.samples[1]
        assert not Path(skipped.cache_path).exists()
        ensure_sample_image(p,skipped)
        assert Path(skipped.cache_path).is_file()
        assert p.observation_sample_ids==before
        added=add_page(p,skipped.actual_time);assert added.status=='changed'
        other=p.samples[3];assert not Path(other.cache_path).exists()
        assert replace_page(p,added.focus_page_id,other.actual_time).status=='changed'
        # Export itself materializes an unviewed selected skipped key.
        pdf,sidecar=export_project(p,tmp_path/'edited.pdf')
        value=loads(sidecar.read_bytes(),pdf_bytes=pdf.read_bytes())
        assert Path(other.cache_path).is_file()
        assert value['schema_version']==7 and value['sampling']['selection_policy']=='half'
        assert value['sampling']['keyframe_index_complete'] is True
        assert [x['is_analysis_observation'] for x in value['samples']]==[i%2==0 for i in range(len(p.samples))]
        assert value['detector']['input_policy']=='half'
        q,_=analyze_project(source,p.settings,tmp_path/'cache',previous=p)
        assert q.observation_sample_ids==before and q.samples is p.samples
    finally:prep.discard()


def test_cancelled_lazy_key_does_not_create_image(tmp_path,monkeypatch,helper):
    source=make(tmp_path/'v.mp4');monkeypatch.setenv('SLIDE_NATIVE_KEYFRAME_HELPER',str(helper))
    prep=prepare_samples(source,tmp_path/'cache')
    try:
        p,_=analyze_project(source,AnalysisSettings(roi_mode='full'),tmp_path/'cache',prepared=prep)
        token=CancelToken();token.cancel()
        with pytest.raises(Exception):ensure_sample_image(p,p.samples[1],token)
        assert not Path(p.samples[1].cache_path).exists()
    finally:prep.discard()


def test_lazy_rejects_cache_target_outside_generation(tmp_path,monkeypatch,helper):
    from dataclasses import replace
    source=make(tmp_path/'v.mp4');monkeypatch.setenv('SLIDE_NATIVE_KEYFRAME_HELPER',str(helper))
    prep=prepare_samples(source,tmp_path/'cache')
    try:
        p,_=analyze_project(source,AnalysisSettings(roi_mode='full'),tmp_path/'cache',prepared=prep)
        bad=replace(p.samples[1],cache_path=str(tmp_path/'skipped_000001.jpg'))
        p.samples=(p.samples[0],bad,*p.samples[2:])
        with pytest.raises(Exception,match='CacheUnavailable'):ensure_sample_image(p,bad)
        assert not Path(bad.cache_path).exists()
    finally:prep.discard()


def test_lazy_cancellation_after_decode_closes_without_partial_image(tmp_path,monkeypatch,helper):
    import slide_core.lazy_frames as module
    source=make(tmp_path/'v.mp4');monkeypatch.setenv('SLIDE_NATIVE_KEYFRAME_HELPER',str(helper))
    prep=prepare_samples(source,tmp_path/'cache')
    try:
        p,_=analyze_project(source,AnalysisSettings(roi_mode='full'),tmp_path/'cache',prepared=prep)
        target=p.samples[1];token=CancelToken();closed=[]
        def frames(*a,**kw):
            try:
                yield target.source_pts,b'\xff'*(target.width*target.height*3)
                token.cancel()
            finally:closed.append(True)
        monkeypatch.setattr(module,'_decode_stream',frames)
        with pytest.raises(Exception):ensure_sample_image(p,target,token)
        assert closed and not Path(target.cache_path).exists()
        assert not list(prep.directory.glob('.lazy-*'))
    finally:prep.discard()
