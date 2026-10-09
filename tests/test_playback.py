from gui.playback import PlaybackClock

def test_monotonic_skip_intermediate_frames():
    now=[0.]
    clock=PlaybackClock([0.,.5,1.5,3.5,5.],6,clock=lambda:now[0])
    clock.play();now[0]=4.9
    assert clock.tick()==3
    now[0]=5.8
    assert clock.tick()==4
    now[0]=7.
    assert clock.tick()==4 and not clock.playing
    clock.play();assert clock.index()==0

def test_seek_tie_earlier_pause_and_resume():
    now=[0.]
    clock=PlaybackClock([0,1,3,4],5,clock=lambda:now[0])
    clock.play();now[0]=2
    assert clock.seek_seconds(2)==1 and not clock.playing
    clock.play();now[0]=2.25;assert clock.tick()==1
    clock.pause();old=clock.target();now[0]=10
    assert clock.target()==old
    assert clock.seek_index(99)==3

def test_nonuniform_gap_and_empty():
    clock=PlaybackClock([0,2,6],7)
    assert clock.seek_seconds(4)==1
    assert clock.seek_index(-99)==0
    empty=PlaybackClock([],0);empty.play();assert empty.tick()==-1
