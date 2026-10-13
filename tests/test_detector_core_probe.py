import numpy as np
from scripts.detector_core_probe import broad_candidates

def frames(*changes):
    result=np.full((len(changes),100,100),255,dtype=np.uint8)
    for i,(h,w) in enumerate(changes):
        result[i,:h,:w]=0
    return result

def test_single_observation_slide_and_return_are_both_candidates():
    x=frames((0,0),(70,70),(0,0))
    assert broad_candidates(x,np.ones((100,100),bool),pixel_fraction=.1,tile_fraction=.2)==[1,2]

def test_small_transient_pointer_is_not_a_broad_candidate():
    x=frames((0,0),(5,5),(0,0))
    assert broad_candidates(x,np.ones((100,100),bool),pixel_fraction=.1,tile_fraction=.2)==[]

def test_local_persistent_writing_does_not_emit_each_state():
    x=frames((0,0),(5,5),(5,10),(5,15))
    assert broad_candidates(x,np.ones((100,100),bool),pixel_fraction=.1,tile_fraction=.2)==[]
