from pathlib import Path
from PySide6.QtWidgets import QApplication,QMessageBox
from gui.window import Window
from gui.state import State
from slide_core.config import AnalysisSettings
from tests.qt_fixtures import spin
from tests.test_native_keyframes_integration import make,helper


def test_gui_seeks_uncached_skipped_key_without_dirtying_project(tmp_path,monkeypatch,helper):
    source=make(tmp_path/'v.mp4',duration=6);monkeypatch.setenv('SLIDE_NATIVE_KEYFRAME_HELPER',str(helper))
    app=QApplication.instance() or QApplication([]);warnings=[]
    monkeypatch.setattr(QMessageBox,'warning',lambda *a,**kw:warnings.append(a))
    w=Window(settings=AnalysisSettings(roi_mode='full'));w.show()
    try:
        w.open_source(source.path);spin(app,lambda:w.controller.state==State.SOURCE_READY)
        w.analyze();spin(app,lambda:w.controller.state==State.REVIEW_READY,timeout=30)
        p=w.controller.project
        assert p.selection_policy=='half'
        ids=p.observation_sample_ids
        missing=next(s for s in reversed(p.samples) if s.sample_id not in ids and not Path(s.cache_path).exists())
        w.seek_index(missing.ordinal)
        spin(app,lambda:Path(missing.cache_path).exists() and w.images.cached(w._image_key(missing.ordinal)) is not None,timeout=20)
        assert w.controller.state==State.REVIEW_READY
        assert p.observation_sample_ids==ids and not warnings
    finally:w.close();spin(app,lambda:not w.isVisible())
