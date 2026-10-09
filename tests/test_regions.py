import numpy as np
import pytest
from slide_core.models import Rect
from slide_core.roi import build_detection_region,automatic_roi

def test_roi_odd_edges_and_mask_intersection():
    region=build_detection_region(1024,768,640,480,Rect(101,43,511,401),Rect(250,60,500,100))
    assert region.display_roi.width==511
    assert region.cache_roi.width>=319
    assert region.detector_roi.width<=320
    assert region.outside_mask_warning
    assert (~region.valid).any() and region.valid.any()


def test_full_mask_and_small_roi_rejected():
    with pytest.raises(ValueError,match='Insufficient'):
        build_detection_region(640,480,640,480,mask=Rect(0,0,640,480))
    with pytest.raises(ValueError,match='64x36'):
        build_detection_region(640,480,640,480,roi=Rect(0,0,30,30))


def test_outside_mask_no_effect():
    r=build_detection_region(640,480,640,480,roi=Rect(0,0,300,300),mask=Rect(400,300,20,20))
    assert r.valid.all() and r.outside_mask_warning


def test_black_intro_fallback():
    roi,reason=automatic_roi([np.zeros((80,120),dtype=np.uint8)]*4)
    assert roi==Rect(0,0,120,80) and reason=='black_intro'


def test_border_detection():
    a=np.zeros((120,160),dtype=np.uint8);a[10:110,15:150]=240
    roi,reason=automatic_roi([a]*5)
    assert roi==Rect(15,10,135,100) and reason is None
