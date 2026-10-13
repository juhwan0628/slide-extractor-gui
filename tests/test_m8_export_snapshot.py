from pathlib import Path
import pytest
from slide_core import keyframe_export as engine
from tests.export_fixtures import make_project,extract_stub


@pytest.mark.parametrize('field',['selection_policy','decoder_backend'])
def test_changed_provenance_during_render_does_not_publish(tmp_path,monkeypatch,field):
    p=make_project(tmp_path)
    p.decoder_backend='native-idr';p.keyframe_index_complete=False
    extract=extract_stub(p)
    def mutate(*args,**kwargs):
        frames=extract(*args,**kwargs)
        if field=='selection_policy':p.selection_policy='half'
        else:p.decoder_backend='cpu-keyframes'
        p.validate()
        return frames
    monkeypatch.setattr(engine,'extract_selected',mutate)
    with pytest.raises(RuntimeError,match='Project changed during export'):
        engine.export_project(p,tmp_path/'slides.pdf')
    assert not (tmp_path/'slides.pdf').exists()
    assert not (tmp_path/'slides.json').exists()
    assert not list(tmp_path.glob('.slide-export-*'))
