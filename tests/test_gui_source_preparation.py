from tests.cli_fixtures import video

def test_shared_first_frame_remains_gui_compatible(tmp_path):
    from slide_core.source_preparation import prepare_first_frame
    from gui.preparation import prepare_first_frame as gui_prepare
    source=video(tmp_path/'source.mkv')
    assert gui_prepare is prepare_first_frame
    assert prepare_first_frame(source)[1:]==gui_prepare(source)[1:]
