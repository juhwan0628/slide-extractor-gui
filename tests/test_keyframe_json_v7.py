from hashlib import sha256
from uuid import uuid4
import pytest
from slide_core.preparation import prepare_samples
from slide_core.analysis import analyze_project
from slide_core.config import AnalysisSettings
from slide_core.models import make_export_snapshot
from slide_core.keyframe_json import payload_keyframes,validate,InvalidTimeline
from tests.test_native_keyframes_integration import make,helper

@pytest.mark.parametrize('mutation',[
    lambda x:x['sampling'].update(selection_policy='all'),
    lambda x:x['sampling'].update(keyframe_index_complete='true'),
    lambda x:x['samples'][1].update(is_analysis_observation=True),
    lambda x:x['samples'][1].update(is_analysis_observation='false'),
    lambda x:x['detector'].update(input_policy='all'),
    lambda x:x['detected_segments'][0].update(auto_representative_sample_id='s000001'),
])
def test_v7_rejects_forged_observation_membership(tmp_path,monkeypatch,helper,mutation):
    source=make(tmp_path/'v.mp4');monkeypatch.setenv('SLIDE_NATIVE_KEYFRAME_HELPER',str(helper))
    prep=prepare_samples(source,tmp_path/'cache')
    try:
        p,_=analyze_project(source,AnalysisSettings(roi_mode='full'),tmp_path/'cache',prepared=prep)
        value=payload_keyframes(make_export_snapshot(p),tmp_path/'v.pdf',sha256(b'pdf').hexdigest(),str(uuid4()))
        mutation(value)
        with pytest.raises(InvalidTimeline):validate(value)
    finally:prep.discard()
