from copy import deepcopy
from dataclasses import replace
import hashlib
from uuid import uuid4
import pytest
from tests.test_keyframe_json import irregular_project,payload
from slide_core.models import make_export_snapshot
from slide_core.config import DetectorConfig
from slide_core.keyframe_json import payload_keyframes,dumps,loads,validate,InvalidTimeline

def spatial_payload(tmp_path):
    p=irregular_project(tmp_path)
    p.settings=replace(p.settings,detector=DetectorConfig(algorithm='spatial-groups-v1'))
    p.transitions=(replace(p.transitions[0],reason='spatial_change',persistence_samples=1,scores=(('changed_fraction',.4),('changed_cell_fraction',.6))),)
    value=payload_keyframes(make_export_snapshot(p),tmp_path/'s.pdf',hashlib.sha256(b'pdf').hexdigest(),str(uuid4()))
    value['schema_version']=5;value['sampling'].pop('selection_policy')
    return value

def test_spatial_v5_roundtrip(tmp_path):
    value=spatial_payload(tmp_path)
    assert value['schema_version']==5
    assert value['detector']['algorithm']=='spatial-groups-v1'
    assert value['detector']['input_policy']=='all'
    assert value['detector']['spatial']['changed_fraction']==.06
    assert value['detector']['spatial']['cell_fraction']==.30
    b=value['detected_boundaries'][0]
    assert b['status']=='spatial_change' and b['persistence_samples']==1
    assert b['spatial_metrics']=={'changed_fraction':.4,'changed_cell_fraction':.6}
    assert 'anchor_metrics' not in b
    assert loads(dumps(value))==value

def test_v4_legacy_roundtrip_unchanged(tmp_path):
    p,value,raw=payload(tmp_path)
    assert value['schema_version']==4 and loads(dumps(value))==value

@pytest.mark.parametrize('mutation',[
    lambda x:x['detected_boundaries'][0].update(status='confirmed'),
    lambda x:x['detector']['spatial'].pop('cell_fraction'),
    lambda x:x['detector'].update(input_policy='half'),
    lambda x:x['detector']['spatial'].update(changed_fraction=True),
    lambda x:x['detector']['representative'].update(support_samples=0),
    lambda x:x['detected_boundaries'][0]['spatial_metrics'].update(changed_fraction=0),
    lambda x:x['detected_boundaries'][0].update(left_sample_id='s000003'),
])
def test_reject_invalid_v5(mutation,tmp_path):
    value=spatial_payload(tmp_path);mutation(value)
    with pytest.raises(InvalidTimeline):validate(value)
