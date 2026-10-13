import numpy as np
from scripts.revisit_probe import link_occurrences

def test_return_links_identity_without_deleting_occurrence():
    a=np.zeros((20,20),np.uint8);b=a.copy();b[:10]=255
    r=link_occurrences([a,b,a.copy()])
    assert len(r)==3
    assert [x['identity'] for x in r]==[0,1,0]
    assert r[2]['revisit_of']==0

def test_small_content_revision_is_not_exactly_merged():
    a=np.zeros((20,20),np.uint8);b=a.copy();b[3,3]=255
    r=link_occurrences([a,b])
    assert [x['identity'] for x in r]==[0,1]
    assert r[1]['similar_candidate']==0
