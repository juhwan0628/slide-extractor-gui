from fractions import Fraction
from pathlib import Path
import pytest
from slide_core.keyframe_index import choose_policy,index_key_packets
from slide_core.preparation import prepare_samples
from slide_core.analysis import analyze_project
from slide_core.config import AnalysisSettings
from tests.test_native_keyframes_integration import make,helper

@pytest.mark.parametrize('keys,duration,wanted',[
    ([0,1,2],3,'half'),([0,2,4],6,'all'),([0,3],5,'all'),
    ([0],1,'half'),([0],2,'all'),([1,2],3,'half'),([2,3],4,'all'),
])
def test_gop_policy_threshold(keys,duration,wanted):
    assert choose_policy(tuple(Fraction(x) for x in keys),Fraction(duration))==wanted


def test_native_half_default_has_complete_index_without_skipped_jpegs(tmp_path,monkeypatch,helper):
    source=make(tmp_path/'v.mp4',duration=4)
    monkeypatch.setenv('SLIDE_NATIVE_KEYFRAME_HELPER',str(helper))
    p=prepare_samples(source,tmp_path/'cache')
    try:
        assert p.selection_policy=='half' and p.decoder_backend=='native-idr'
        assert len(p.samples)==(len(p.keyframe_index)+1)//2
        assert [s.source_pts for s in p.samples]==[s.source_pts for s in p.keyframe_index[::2]]
        assert len(list(p.directory.glob('*.jpg')))==len(p.samples)
        assert all(not Path(s.cache_path).exists() for s in p.keyframe_index[1::2])
        project,_=analyze_project(source,AnalysisSettings(roi_mode='full'),tmp_path/'cache',prepared=p)
        assert project.samples is p.keyframe_index
        assert project.observation_sample_ids==tuple(s.sample_id for s in p.samples)
        assert project.selection_policy=='half'
        q,_=analyze_project(source,AnalysisSettings(roi_mode='full'),tmp_path/'cache',previous=project)
        assert q.samples is project.samples and q.observation_sample_ids==project.observation_sample_ids
    finally:p.discard()


def test_real_two_second_gop_uses_all(tmp_path,monkeypatch,helper):
    import subprocess
    from slide_core.media import probe_source
    path=tmp_path/'long.mp4'
    subprocess.run(['ffmpeg','-v','error','-y','-f','lavfi','-i','testsrc2=size=96x64:rate=8:duration=5',
        '-c:v','libx264','-preset','ultrafast','-g','16','-x264-params','scenecut=0',str(path)],check=True)
    monkeypatch.setenv('SLIDE_NATIVE_KEYFRAME_HELPER',str(helper))
    prep=prepare_samples(probe_source(path),tmp_path/'cache')
    try:
        assert prep.selection_policy=='all'
        assert len(prep.keyframe_index)==len(prep.samples)==3
        assert len(list(prep.directory.glob('*.jpg')))==3
    finally:prep.discard()
