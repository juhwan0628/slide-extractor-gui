import numpy as np
from scripts.representative_probe import choose_representative

def frames(n):
    return np.full((n,100,100),255,np.uint8)

def test_completed_writing_wins_over_long_early_state():
    a=frames(6);a[1:,:5,:10]=0;a[4:,10:15,:10]=0
    assert choose_representative(a,np.ones((100,100),bool))['index']==5

def test_last_transient_pointer_does_not_replace_complete_content():
    a=frames(5);a[1:,:5,:10]=0;a[-1,40:45,40:45]=0
    assert choose_representative(a,np.ones((100,100),bool))['index']==3

def test_single_observation_slide_is_preserved():
    a=frames(1)
    assert choose_representative(a,np.ones((100,100),bool))['index']==0

def test_erased_persistent_content_is_reported_as_incomplete_coverage():
    a=frames(6);a[:3,:5,:10]=0;a[3:,10:15,:10]=0
    assert choose_representative(a,np.ones((100,100),bool))['missing_supported_pixels']==50

def test_overlay_covering_static_text_is_penalized():
    a=frames(6)
    for y in range(10,40,4):a[:,y,10:60]=0
    a[-2:,5:45,5:65]=120
    assert choose_representative(a,np.ones((100,100),bool))['index']==3
