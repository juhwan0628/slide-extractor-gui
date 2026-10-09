"""FFmpeg showinfo color fields must not include unrelated trailing changes."""
import pytest
from slide_core.pts import _frame_color_signature,_validate_frame_color
from slide_core.media import MediaError

def test_showinfo_extra_fields_are_ignored():
    first='[showinfo@audit] color_range:tv color_space:bt709 color_primaries:bt709 color_trc:bt709 SAR 1:1'
    second='[showinfo@audit] color_range:tv color_space:bt709 color_primaries:bt709 color_trc:bt709 extra:some_other_value'
    state=_validate_frame_color(first,{})
    assert _validate_frame_color(second,state)==state
    assert _frame_color_signature(first)=={'color_range':'tv','color_space':'bt709',
                                           'color_primaries':'bt709','color_trc':'bt709'}

def test_actual_color_changes_are_rejected():
    before=_validate_frame_color('[showinfo@audit] color_range:tv color_space:bt709',{})
    with pytest.raises(MediaError,match='dynamic color metadata'):
        _validate_frame_color('[showinfo@audit] color_range:pc color_space:bt709',before)

def test_hdr_metadata_is_still_rejected():
    with pytest.raises(MediaError,match='unsupported HDR'):
        _validate_frame_color('[showinfo@audit] color_range:tv color_space:bt2020nc color_trc:smpte2084',{})

def test_missing_fields_do_not_cause_false_transition():
    old=_validate_frame_color('[showinfo@audit] color_range:tv color_trc:bt709',{})
    assert _validate_frame_color('[showinfo@audit] color_range:tv',old)==old
