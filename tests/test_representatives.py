import numpy as np
from slide_core.representatives import select_representative
from slide_core.config import SpatialConfig

def pick(a,stats=None):
    return select_representative(lambda i:a[i],0,len(a),np.ones(a.shape[1:],bool),SpatialConfig(),lambda:None,diagnostics=stats)

def test_completed_writing_and_pointer():
    a=np.full((6,100,100),255,np.uint8);a[1:,:5,:10]=0;a[4:,10:15,:10]=0
    assert pick(a)==5
    a[-1,40:45,40:45]=0
    assert pick(a)==4

def test_single_and_erased_content():
    assert pick(np.full((1,100,100),255,np.uint8))==0
    a=np.full((6,100,100),255,np.uint8);a[:3,:5,:10]=0;a[3:,10:15,:10]=0
    stats={};pick(a,stats)
    assert stats['missing_supported_pixels']==50

def test_overlay_does_not_win():
    a=np.full((6,100,100),255,np.uint8)
    for y in range(10,40,4):a[:,y,10:60]=0
    a[-2:,5:45,5:65]=120
    assert pick(a)==3
