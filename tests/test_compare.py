import numpy as np
import pytest
from slide_core.compare import local_change_metrics

def test_masked_only_changes_are_excluded():
    a=np.zeros((40,40),np.uint8);b=a.copy();b[:,:20]=255
    valid=np.ones((40,40),bool);valid[:,:20]=False
    m=local_change_metrics(a,b,valid_mask=valid)
    assert (m.global_mad,m.changed_fraction,m.max_tile_mad)==(0.,0.,0.)


def test_small_unmasked_tile_change_is_detected():
    a=np.zeros((100,100),np.uint8);b=a.copy();b[20:40,20:40]=255
    m=local_change_metrics(a,b)
    assert m.global_mad == pytest.approx(.04)
    assert m.max_tile_mad == pytest.approx(1.)
    assert m.changed_fraction == pytest.approx(.04)


def test_uint8_signed_safe_and_half_valid_tiles():
    a=np.full((20,20),255,np.uint8);b=np.zeros_like(a)
    valid=np.zeros_like(a,bool);valid[:10,:]=True
    m=local_change_metrics(a,b,valid_mask=valid)
    assert m.global_mad==1. and m.max_tile_mad==1.
    valid[:9,:]=False
    m=local_change_metrics(a,b,valid_mask=valid)
    assert m.max_tile_mad==0.


def test_zero_valid_and_shape_rejected():
    a=np.zeros((30,30),np.uint8)
    with pytest.raises(ValueError):local_change_metrics(a,a,valid_mask=np.zeros_like(a,bool))
    with pytest.raises(ValueError):local_change_metrics(a,np.zeros((10,20),np.uint8))
