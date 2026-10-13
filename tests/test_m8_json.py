from copy import deepcopy
from dataclasses import replace
from hashlib import sha256
from uuid import uuid4
import pytest
from tests.test_keyframe_json import irregular_project
from slide_core.config import DetectorConfig
from slide_core.models import make_export_snapshot
from slide_core.keyframe_json import payload_keyframes,loads,dumps,validate,InvalidTimeline


def spatial_project(tmp_path):
    p=irregular_project(tmp_path)
    p.settings=replace(p.settings,detector=DetectorConfig(algorithm='spatial-groups-v1'))
    p.transitions=(replace(p.transitions[0],reason='spatial_change',persistence_samples=1,
        scores=(('changed_fraction',.4),('changed_cell_fraction',.6))),)
    return p


def encode(p,tmp_path):
    return payload_keyframes(make_export_snapshot(p),tmp_path/'slides.pdf',sha256(b'pdf').hexdigest(),str(uuid4()))


def test_spatial_v6_serializes_effective_all_policy(tmp_path):
    p=spatial_project(tmp_path);value=encode(p,tmp_path)
    assert value['schema_version']==6
    assert value['sampling']['selection_policy']=='all'
    assert loads(dumps(value))==value


def test_legacy_half_v6_is_truthful_not_v4_all(tmp_path):
    p=replace(irregular_project(tmp_path),selection_policy='half',decoder_backend='native-idr',keyframe_index_complete=False)
    value=encode(p,tmp_path)
    assert value['schema_version']==6
    assert value['sampling']['selection_policy']=='half'
    assert value['detector']['algorithm']=='masked-anchor-tile-v1'
    assert loads(dumps(value))==value


@pytest.mark.parametrize('mutation',[
    lambda x:x['sampling'].pop('selection_policy'),
    lambda x:x['sampling'].update(selection_policy='half'),
    lambda x:x['sampling'].update(selection_policy=True),
    lambda x:x['sampling'].update(selection_policy='bogus'),
    lambda x:x['sampling'].update(fps=1),
])
def test_v6_invalid_policy_rejected(tmp_path,mutation):
    value=encode(spatial_project(tmp_path),tmp_path)
    mutation(value)
    with pytest.raises(InvalidTimeline):validate(value)


def test_old_v5_still_valid_without_policy_field(tmp_path):
    value=encode(spatial_project(tmp_path),tmp_path)
    value['schema_version']=5;value['sampling'].pop('selection_policy')
    assert loads(dumps(value))==value
