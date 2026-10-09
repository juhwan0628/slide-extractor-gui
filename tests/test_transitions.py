from fractions import Fraction
from uuid import uuid4
import numpy as np
import pytest
from slide_core.models import Sample
from slide_core.transitions import streaming_detect

def fixture(states,times=None):
    times=times or list(range(len(states)))
    samples=[Sample(str(uuid4()),int(t),int(t),Fraction(1),Fraction(t),str(t),80,48) for t in times]
    frames=(np.full((48,80),int(v),np.uint8) for v in states)
    return samples,frames


def detect(states,times=None):
    samples,frames=fixture(states,times)
    ts,ss=streaming_detect(samples,frames,duration=Fraction(max(times or list(range(len(states))))+1))
    return samples,ts,ss


def test_three_persistent_states_aba():
    samples,ts,ss=detect([20,20,180,180,20,20])
    assert [t.observed_time for t in ts]==[2,4]
    assert all(t.reason=='confirmed' and t.persistence_samples==2 for t in ts)
    assert len(ss)==3
    assert [(x.start_time,x.end_time) for x in ss]==[(0,2),(2,4),(4,6)]
    assert [x.representative_sample_id for x in ss]==[samples[1].sample_id,samples[3].sample_id,samples[5].sample_id]


def test_one_frame_transient_is_not_new_segment():
    samples,ts,ss=detect([20,20,180,20,20])
    assert ts==() and len(ss)==1


def test_eof_unconfirmed_when_last_sample_changes():
    _,ts,ss=detect([20,20,180])
    assert len(ts)==1 and ts[0].reason=='eof_unconfirmed'
    assert len(ss)==2


def test_missing_grid_bucket_must_not_confirm():
    _,ts,ss=detect([20,20,180,180],times=[0,1,2,5])
    assert ts==() and len(ss)==1


def test_single_sample():
    samples,ts,ss=detect([10])
    assert ts==() and len(ss)==1 and ss[0].representative_sample_id==samples[0].sample_id


def test_subthreshold_cumulative_anchor():
    _,ts,ss=detect([30,32,34,40,42,43])
    assert ts==() and len(ss)==1


def test_streaming_detector_rejects_mismatched_frame_count():
    samples,frames=fixture([10,20,30])
    with pytest.raises(ValueError,match='cardinality'):
        streaming_detect(samples,iter([np.zeros((48,80),dtype=np.uint8)]),duration=4)
    with pytest.raises(ValueError,match='cardinality'):
        streaming_detect(samples,iter([np.zeros((48,80),dtype=np.uint8)]*4),duration=4)
