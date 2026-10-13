import numpy as np
from scripts.detector_grouping_probe import group_candidates

def blank(n):
    return np.full((n,100,100),255,np.uint8)

def test_brief_slide_preserves_return_occurrence():
    x=blank(3);x[1,:70,:70]=0
    assert [g['start'] for g in group_candidates(x,np.ones((100,100),bool),[0,1,2])]==[0,1,2]

def test_small_persistent_replacement_remains_reviewable():
    x=blank(3);x[1:,20:25,20:40]=0
    groups=group_candidates(x,np.ones((100,100),bool),[0,1])
    assert len(groups)==1
    assert groups[0]['alternatives']==[0,1]
    assert groups[0]['events'][0]['evidence']=='unresolved_change'

def test_local_reversion_does_not_delete_candidate():
    x=blank(3);x[1,:5,:5]=0
    g=group_candidates(x,np.ones((100,100),bool),[0,1])[0]
    assert g['events'][0]['evidence']=='localized_reversion'
    assert g['alternatives']==[0,1]

def test_accumulating_changes_do_not_move_structural_anchor():
    x=blank(4)
    for i in range(1,4):x[i,:5,:i*10]=0
    g=group_candidates(x,np.ones((100,100),bool),[1,2,3])[0]
    assert g['start']==0
    assert g['alternatives']==[0,1,2,3]

def test_distributed_small_change_splits_but_local_writing_does_not():
    x=blank(2)
    for y in range(0,100,20):
        for z in range(0,100,20):x[1,y:y+5,z:z+5]=0
    groups=group_candidates(x,np.ones((100,100),bool),[0,1],small_pixel_fraction=.06)
    assert [g['start'] for g in groups]==[0,1]
    local=blank(2);local[1,:25,:25]=0
    assert len(group_candidates(local,np.ones((100,100),bool),[0,1],small_pixel_fraction=.06))==1
