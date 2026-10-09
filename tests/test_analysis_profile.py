import json
from pathlib import Path
from slide_core.analysis import analyze_project
from slide_core.config import AnalysisSettings
from tests.test_sampling import make_video

def test_profile_preserves_output_and_reports_sampling_and_detection(tmp_path):
    from slide_core.profiling import AnalysisProfile
    source=make_video(tmp_path/'private-name.mp4',duration=4,fps=4)
    p=AnalysisProfile()
    a,_=analyze_project(source,AnalysisSettings(roi_mode='full'),tmp_path/'cache',profile=p)
    report=p.report()
    assert report['status']=='success'
    assert report['sample_count']==4
    assert report['page_count']==len(a.pages)
    for key in ('total','sampling','decode_wait','jpeg_encode','cache_write','roi','detection','cache_prepare','assembly'):
        assert report['seconds'][key]>=0
    assert report['seconds']['sampling']>=report['seconds']['jpeg_encode']+report['seconds']['cache_write']
    assert report['seconds']['detection']>=report['seconds']['cache_prepare']
    target=tmp_path/'profile.json';p.save(target)
    assert json.loads(target.read_text())==report
    assert str(tmp_path) not in target.read_text()
    assert source.path.name not in target.read_text()
    p2=AnalysisProfile()
    b,_=analyze_project(source,AnalysisSettings(roi_mode='full'),tmp_path/'cache',previous=a,profile=p2)
    assert p2.report()['cache_reused'] is True
    assert p2.report()['seconds'].get('sampling',0)==0
    assert [x.representative_sample_id for x in a.pages]==[x.representative_sample_id for x in b.pages]

def test_failed_analysis_profile_reports_failure(tmp_path):
    from slide_core.profiling import AnalysisProfile
    from slide_core.models import CancelToken
    import pytest
    p=AnalysisProfile();cancel=CancelToken();cancel.cancel()
    with pytest.raises(Exception):
        analyze_project(tmp_path/'absent.mp4',AnalysisSettings(),tmp_path/'cache',cancel_token=cancel,profile=p)
    assert p.report()['status']=='failed'
    assert p.report()['seconds']['total']>=0
