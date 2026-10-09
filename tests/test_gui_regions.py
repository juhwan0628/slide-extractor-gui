from gui.regions import drag_rect,view_to_display

def test_letterbox_ignored_and_reverse_drag():
    # 16:9 source in a square view has letterboxing above and below.
    assert view_to_display((50,5),400,400,160,90) is None
    a=drag_rect((350,300),(50,100),160,90,400,400)
    b=drag_rect((50,100),(350,300),160,90,400,400)
    assert a==b and a.width>0 and a.height>0

def test_outside_press_ignored_and_end_clamped():
    assert drag_rect((20,10),(200,200),100,100,300,200) is None
    region=drag_rect((150,100),(9999,9999),100,100,300,200)
    assert region.x+region.width==100 and region.y+region.height==100

def test_tiny_zero_rect_is_invalid():
    assert drag_rect((20,20),(20,20),100,100,200,200) is None
