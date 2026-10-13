"""Real Qt Save options and keyframe paired export after page editing."""
from pathlib import Path
import json
import pytest
from PySide6.QtWidgets import QApplication,QDialog,QCheckBox,QComboBox,QFileDialog,QMessageBox
from gui.window import Window
from gui.state import State
from tests.media_fixtures import make_scene_video
from tests.qt_fixtures import spin
from slide_core.editing import merge_pages
from pypdf import PdfReader

@pytest.fixture(params=["masked-anchor-tile-v1","spatial-groups-v1"])
def window(tmp_path,monkeypatch,request):
 app=QApplication.instance() or QApplication([])
 warnings=[]
 monkeypatch.setattr(QMessageBox,'warning',lambda *a,**kw:warnings.append(a[2]))
 from slide_core.config import AnalysisSettings,DetectorConfig
 w=Window(settings=AnalysisSettings(detector=DetectorConfig(algorithm=request.param)));w.show();path=make_scene_video(tmp_path/'video.mp4')
 w.open_source(path);spin(app,lambda:w.controller.state==State.SOURCE_READY)
 w.analyze();spin(app,lambda:w.controller.state==State.REVIEW_READY,timeout=30)
 assert not warnings
 yield app,w,warnings
 w.close();spin(app,lambda:not w.isVisible())

@pytest.mark.parametrize('accept',[False,True])
def test_save_options_v4_do_not_reanalyze_or_destroy_edit_history(window,monkeypatch,accept):
 app,w,warnings=window;p=w.controller.project
 before=(p,tuple(p.pages),p.revision,p.samples,w._sample_preparation,w.settings)
 def choose(dialog):
  boxes=dialog.findChildren(QCheckBox);combos=dialog.findChildren(QComboBox)
  assert len(boxes)==1 and len(combos)==1
  boxes[0].setChecked(True);assert combos[0].isEnabled()
  assert ('v6' if p.settings.detector.algorithm=='spatial-groups-v1' else 'v4') in combos[0].itemText(1)
  combos[0].setCurrentIndex(1)
  return QDialog.DialogCode.Accepted if accept else QDialog.DialogCode.Rejected
 monkeypatch.setattr(QDialog,'exec',choose);w.open_save_options()
 assert (w.controller.project,tuple(p.pages),p.revision,p.samples,w._sample_preparation,w.settings)==before
 assert w.json_enabled is accept
 assert w.json_format==('detailed' if accept else 'simple')
 assert not warnings

@pytest.mark.parametrize('format',['simple','detailed'])
def test_real_gui_saves_json_for_current_merged_pdf(window,tmp_path,monkeypatch,format):
 app,w,warnings=window;p=w.controller.project
 detected_before=tuple(p.transitions)
 w.page_view.selectAll();w.merge_selected_pages()
 assert len(p.pages)==1
 target=tmp_path/'수업.pdf'
 def choose(dialog):
  box=dialog.findChildren(QCheckBox)[0];combo=dialog.findChildren(QComboBox)[0]
  box.setChecked(True);combo.setCurrentIndex(0 if format=='simple' else 1)
  return QDialog.DialogCode.Accepted
 monkeypatch.setattr(QDialog,'exec',choose);w.open_save_options()
 assert w.json_enabled and w.json_format==format
 monkeypatch.setattr(QFileDialog,'getSaveFileName',lambda *a,**kw:(str(target),'PDF'))
 w.export_pending()
 spin(app,lambda:w.controller.state==State.REVIEW_READY and w.jobs.worker is None,timeout=40)
 assert target.is_file() and target.with_suffix('.json').is_file() and not warnings
 assert len(PdfReader(target).pages)==1
 value=json.loads(target.with_suffix('.json').read_bytes())
 if format=='detailed':
  from slide_core.keyframe_json import loads
  value=loads(target.with_suffix('.json').read_bytes(),pdf_bytes=target.read_bytes())
  assert value['schema_version']==(6 if p.settings.detector.algorithm=='spatial-groups-v1' else 4) and len(value['detected_boundaries'])==len(detected_before)>0
  assert [x['observed_at_s'] for x in value['detected_boundaries']]==[float(t.observed_time) for t in detected_before]
  assert value['pages'][0]['page_id']==p.pages[0].page_id
 else:assert value=={'slides':[{'page':1,'start':0.0,'end':6.0}]}
 assert not list(tmp_path.glob('*.lock'))
