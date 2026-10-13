from slide_core.analysis import analyze_project,requires_reanalysis
from slide_core.config import AnalysisSettings,DetectorConfig
from tests.media_fixtures import make_video

def test_new_analysis_default_is_spatial(tmp_path):
    source=make_video(tmp_path/'v.mp4',duration=3,fps=4)
    p,_=analyze_project(source,AnalysisSettings(roi_mode='full'),tmp_path/'cache')
    assert p.settings.detector.algorithm=='spatial-groups-v1'
    assert not requires_reanalysis(p,AnalysisSettings(roi_mode='full'))

def test_v4_reanalysis_stays_legacy(tmp_path):
    source=make_video(tmp_path/'v.mp4',duration=3,fps=4)
    legacy=AnalysisSettings(roi_mode='full',detector=DetectorConfig())
    p,_=analyze_project(source,legacy,tmp_path/'cache')
    q,_=analyze_project(source,AnalysisSettings(roi_mode='full'),tmp_path/'cache',previous=p)
    assert q.settings.detector.algorithm=='masked-anchor-tile-v1'
    assert not requires_reanalysis(p,AnalysisSettings(roi_mode='full'))

def test_default_input_remains_all(tmp_path):
    source=make_video(tmp_path/'v.mp4',duration=3,fps=4)
    p,_=analyze_project(source,AnalysisSettings(roi_mode='full'),tmp_path/'cache')
    assert p._selection_policy=='all'
