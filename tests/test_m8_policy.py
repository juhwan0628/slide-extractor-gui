from dataclasses import replace
from pathlib import Path
import pytest
from slide_core.analysis import analyze_project
from slide_core.config import AnalysisSettings,DetectorConfig
from slide_core.models import make_export_snapshot
from slide_core.preparation import prepare_samples
from slide_core.profiling import AnalysisProfile
from slide_core.media import MediaError
from tests.media_fixtures import make_video


def test_effective_policy_survives_reanalysis_and_snapshot(tmp_path):
    source=make_video(tmp_path/'v.mp4',duration=3,fps=4)
    prepared=prepare_samples(source,tmp_path/'cache')
    try:
        p,_=analyze_project(source,AnalysisSettings(roi_mode='full'),tmp_path/'cache',prepared=prepared)
        q,_=analyze_project(source,AnalysisSettings(roi_mode='full'),tmp_path/'cache',previous=p)
        assert q.samples is p.samples
        assert q.cache_generation==p.cache_generation
        assert q.selection_policy=='all'
        assert q.decoder_backend==prepared.decoder_backend
        snap=make_export_snapshot(q)
        assert snap.selection_policy=='all' and snap.decoder_backend==prepared.decoder_backend
    finally:prepared.discard()


def test_previous_prepared_policy_mismatch_fails_without_touching_cache(tmp_path):
    source=make_video(tmp_path/'v.mp4',duration=3,fps=4)
    prepared=prepare_samples(source,tmp_path/'cache')
    try:
        settings=AnalysisSettings(roi_mode='full',detector=DetectorConfig())
        p,_=analyze_project(source,settings,tmp_path/'cache',prepared=prepared)
        half=replace(prepared,selection_policy='half',decoder_backend='native-idr')
        before=(p.pages[:],p.revision,p.samples,p.cache_generation)
        with pytest.raises(MediaError,match='SelectionPolicyMismatch'):
            analyze_project(source,settings,tmp_path/'cache',previous=p,prepared=half)
        assert before==(p.pages,p.revision,p.samples,p.cache_generation)
        assert all(Path(s.cache_path).is_file() for s in prepared.samples)
    finally:prepared.discard()


def test_profile_reports_prepared_provenance_and_reuse(tmp_path):
    source=make_video(tmp_path/'v.mp4',duration=3,fps=4)
    prepared=prepare_samples(source,tmp_path/'cache')
    try:
        # This verifies propagation independently of the decoder implementation.
        native=replace(prepared,decoder_backend='native-idr')
        profile=AnalysisProfile()
        p,_=analyze_project(source,AnalysisSettings(roi_mode='full'),tmp_path/'cache',prepared=native,profile=profile)
        report=profile.report()
        assert report['decoder_backend']=='native-idr'
        assert report['selection_policy']=='all' and report['cache_reused'] is True
        assert p.decoder_backend=='native-idr'
    finally:prepared.discard()


@pytest.mark.parametrize('updates',[
    {'selection_policy':'bogus'}, {'decoder_backend':'bogus'},
    {'selection_policy':'half','decoder_backend':'cpu-keyframes'},
])
def test_invalid_preparation_provenance_rejected(tmp_path,updates):
    source=make_video(tmp_path/'v.mp4',duration=2,fps=4)
    prepared=prepare_samples(source,tmp_path/'cache')
    try:
        with pytest.raises(ValueError):replace(prepared,**updates)
    finally:prepared.discard()
