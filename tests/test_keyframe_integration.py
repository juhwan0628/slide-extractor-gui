"""Keyframe preparation/analysis integration with actual decoder and Qt flow."""
from dataclasses import replace
from pathlib import Path
from threading import Event
import pytest
from slide_core.config import AnalysisSettings,DetectorConfig
from slide_core.analysis import analyze_project,requires_reanalysis
from slide_core.preparation import prepare_samples
from slide_core.models import CancelToken,Rect
from tests.test_keyframe_sampling import video,keyframes
from tests.qt_fixtures import spin

def settings(**kw):return AnalysisSettings(roi_mode='full',**kw)

def test_ready_keyframe_cache_reused_for_roi_and_sensitivity(tmp_path):
 source=video(tmp_path/'source.mkv',vfr=True)
 prepared=prepare_samples(source,tmp_path/'cache')
 try:
  def forbidden(*a,**kw):raise AssertionError('second decoder')
  p,_=analyze_project(source,settings(),tmp_path/'cache',prepared=prepared)
  assert [s.source_pts for s in p.samples]==keyframes(source)
  changed=replace(p.settings,roi_mode='manual',effective_roi=Rect(0,0,80,48),detector=replace(DetectorConfig(),candidate_mad=.01))
  q,_=analyze_project(source,changed,tmp_path/'cache',previous=p)
  assert q.samples is p.samples and q.cache_generation==prepared.cache_generation
  assert requires_reanalysis(p,changed)
  assert not requires_reanalysis(p,replace(p.settings))
 finally:prepared.discard()




@pytest.mark.parametrize('early',[False,True])
def test_keyframe_window_silent_prepare_analyze_and_irregular_preview(tmp_path,monkeypatch,early):
 from PySide6.QtWidgets import QApplication,QMessageBox
 from gui.window import Window
 from gui.state import State
 from gui import sample_preparation as bg
 from slide_core import pts
 from slide_core.pdf_only_export import export_pdf_only
 from pypdf import PdfReader
 app=QApplication.instance() or QApplication([])
 source=video(tmp_path/'source.mkv',vfr=True);entered=Event();release=Event();commands=[]
 real=bg.prepare_samples;ff=pts._ffmpeg
 def delayed(*a,**kw):
  entered.set()
  while not release.wait(.01):kw['cancel_token'].raise_if_cancelled()
  return real(*a,**kw)
 def command(*a,**kw):
  commands.append((kw.get('decode_options') or {}).get('backend'));return ff(*a,**kw)
 monkeypatch.setattr(bg,'prepare_samples',delayed);monkeypatch.setattr(pts,'_ffmpeg',command)
 monkeypatch.setattr(QMessageBox,'warning',lambda *a,**kw:pytest.fail(str(a[2])))
 w=Window(settings=settings());w.show()
 try:
  w.open_source(source.path);spin(app,lambda:w.controller.state==State.SOURCE_READY and entered.is_set())
  task=w._sample_preparation
  assert not w.analysis_progress.isVisible()
  if not early:release.set();spin(app,task.ready.is_set)
  w.analyze();release.set();spin(app,lambda:w.controller.state==State.REVIEW_READY,timeout=10)
  p=w.controller.project;directory=task.result.directory
  assert commands and all(c in (None,'cpu-keyframes') for c in commands)
  assert [s.source_pts for s in p.samples]==keyframes(source)
  assert w.player.times==tuple(float(s.actual_time) for s in p.samples)
  w.player.seek_seconds(float(p.samples[-1].actual_time))
  assert w.player.index()==len(p.samples)-1
  before=p.samples;generation=p.cache_generation
  w.settings=replace(w.settings,roi_mode='manual',effective_roi=Rect(0,0,80,48),settings_revision=1)
  monkeypatch.setattr(QMessageBox,'question',lambda *a,**kw:QMessageBox.StandardButton.Yes)
  w.analyze();spin(app,lambda:w.controller.state==State.REVIEW_READY,timeout=10)
  assert w.controller.project.samples is before and w.controller.project.cache_generation==generation
  assert commands and all(c in (None,'cpu-keyframes') for c in commands) and w._sample_preparation is task
  w.delete_selected_pages();w.undo_edit()
  if not w.controller.project.pages:pytest.fail('No pages after undo')
  pdf=tmp_path/'keyframes.pdf';export_pdf_only(w.controller.project,pdf)
  assert len(PdfReader(pdf).pages)==len(w.controller.project.pages)
  w.back_to_preparation.click();spin(app,task.done.is_set)
  assert not directory.exists()
 finally:
  release.set();w.close();spin(app,lambda:not w.isVisible())

def test_keyframe_preparation_profile_reports_sampling_method(tmp_path):
 from gui.sample_preparation import BackgroundSamples
 import json
 source=video(tmp_path/'source.mkv');path=tmp_path/'profile.json'
 task=BackgroundSamples(source,tmp_path/'cache',profile_path=path)
 try:
  task.wait(CancelToken())
  report=json.loads(path.read_text())
  assert report['sampling_algorithm']=='decoder-keyframes-v1' and 'sample_fps' not in report
 finally:task.close();assert task.done.wait(3)

def test_keyframe_analysis_dialog_has_no_fps_control(tmp_path,monkeypatch):
 from PySide6.QtWidgets import QApplication,QDialog,QComboBox
 from gui.window import Window
 app=QApplication.instance() or QApplication([]);w=Window(settings=settings());w.show()
 before=w.settings
 def inspect(dialog):
  assert not dialog.findChildren(QComboBox)
  return QDialog.DialogCode.Accepted
 monkeypatch.setattr(QDialog,'exec',inspect)
 try:w.open_advanced();assert w.settings==before
 finally:w.close();spin(app,lambda:not w.isVisible())

def test_keyframe_save_options_offer_v4_json(tmp_path,monkeypatch):
 from PySide6.QtWidgets import QApplication,QDialog,QCheckBox
 from gui.window import Window
 from gui.state import State
 app=QApplication.instance() or QApplication([]);w=Window(settings=settings());w.show()
 source=video(tmp_path/'source.mkv');p,_=analyze_project(source,settings(),tmp_path/'cache')
 w.controller.project=p;w.controller.source=source;w.controller.state=State.REVIEW_READY;w._set_stage('review')
 def inspect(dialog):
  boxes=dialog.findChildren(QCheckBox)
  assert len(boxes)==1 and not boxes[0].isChecked()
  return QDialog.DialogCode.Accepted
 monkeypatch.setattr(QDialog,'exec',inspect)
 try:w.open_save_options();assert not w.json_enabled
 finally:
  p._cache_pin.close();w.close();spin(app,lambda:not w.isVisible())

def test_failed_reanalysis_preserves_previous_keyframe_cache(tmp_path,monkeypatch):
 from slide_core import analysis
 source=video(tmp_path/'source.mkv')
 p,_=analyze_project(source,AnalysisSettings(roi_mode='full'),tmp_path/'cache')
 paths={Path(s.cache_path) for s in p.samples}
 def fail(*a,**kw):raise RuntimeError('injected ROI error')
 monkeypatch.setattr(analysis,'_resolve_roi',fail)
 try:
  with pytest.raises(RuntimeError,match='ROI error'):analyze_project(source,settings(),tmp_path/'cache',previous=p)
  assert set((tmp_path/'cache').rglob('*.jpg'))==paths
 finally:p._cache_pin.close()

@pytest.mark.parametrize('rotation',[0,90])
def test_keyframe_preparation_preserves_rotation_and_non_square_sar(tmp_path,rotation):
 import subprocess
 from PIL import Image
 from slide_core.media import probe_source
 from slide_core.pts import extract_selected
 base=tmp_path/'base.mp4';path=tmp_path/'rotated.mp4'
 subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y','-f','lavfi','-i','testsrc2=size=96x64:rate=4:duration=2','-vf','setsar=4/3','-c:v','mpeg4','-g','4',str(base)],check=True,timeout=20)
 subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y','-display_rotation',str(rotation),'-i',str(base),'-c','copy',str(path)],check=True,timeout=20)
 source=probe_source(path);assert source.transform.rotation==rotation
 prepared=prepare_samples(source,tmp_path/'cache')
 try:
  assert (prepared.samples[0].width,prepared.samples[0].height)==((128,64) if rotation==0 else (64,128))
  full=extract_selected(source,prepared.samples,tmp_path/'full')
  assert all(Image.open(p).size==(s.width,s.height) for p,s in zip(full,prepared.samples))
 finally:prepared.discard()

def test_keyframe_dynamic_color_rejected_with_partial_cache_cleanup(tmp_path,monkeypatch):
 from tests.decoder_fixtures import decoder,sampling_source
 from tests.test_keyframe_sampling import emit
 from slide_core import pts
 from slide_core.media import MediaError
 body="sys.stderr.write('[showinfo@audit] color_range:tv color_space:bt709\\n');sys.stderr.flush()\n"+emit(0,0)+"sys.stderr.write('[showinfo@audit] color_range:pc color_space:bt709\\n');sys.stderr.flush()\n"+emit(1,1)
 source=sampling_source(monkeypatch,decoder(monkeypatch,tmp_path,body))
 with pytest.raises(MediaError) as err:pts.keyframe_stream(source,tmp_path/'cache')
 assert err.value.code=='UnsupportedDisplayTransform'
 assert not list((tmp_path/'cache').rglob('*.jpg'))


def test_keyframe_profile_records_actual_auto_thread_setting(tmp_path):
 from slide_core.profiling import AnalysisProfile
 source=video(tmp_path/'source.mkv');profile=AnalysisProfile()
 p,_=analyze_project(source,settings(),tmp_path/'cache',profile=profile)
 try:
  assert profile.metadata['decoder_backend']=='cpu-keyframes'
  assert profile.metadata['decoder_threads']==0
 finally:p._cache_pin.close()
