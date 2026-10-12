"""Contract for the keyframe-only application and isolated FPS baseline."""
from dataclasses import fields,replace
from pathlib import Path
import inspect,json,subprocess,runpy,zipfile
import pytest
from PySide6.QtWidgets import QApplication,QComboBox,QDialog,QCheckBox
from slide_core.config import AnalysisSettings
from slide_core import pts,preparation
from slide_core.preparation import prepare_samples
from slide_core.analysis import analyze_project
from gui.sample_preparation import BackgroundSamples
from gui.window import Window
from tests.test_keyframe_sampling import video,keyframes
from tests.qt_fixtures import spin
from slide_core.models import CancelToken
ROOT=Path(__file__).resolve().parents[1]

def test_settings_and_preparation_have_no_fps_or_mode():
 assert not {'fps','sampling_mode'} & {f.name for f in fields(AnalysisSettings)}
 assert 'fps' not in inspect.signature(prepare_samples).parameters
 assert 'sampling_mode' not in inspect.signature(BackgroundSamples).parameters
 assert not hasattr(pts,'sample_stream') and not hasattr(preparation,'compact_samples')

@pytest.mark.parametrize('bad',[{'fps':.5},{'sampling_mode':'fps'}])
def test_legacy_parameters_are_rejected(bad):
 with pytest.raises(TypeError):AnalysisSettings(**bad)

def test_default_preparation_is_keyframes_and_ready_cache_is_reused(tmp_path,monkeypatch):
 from slide_core import analysis
 source=video(tmp_path/'source.mkv',vfr=True);prepared=prepare_samples(source,tmp_path/'cache')
 try:
  assert [s.source_pts for s in prepared.samples]==keyframes(source)
  assert prepared.sampling_algorithm=='decoder-keyframes-v1'
  def forbidden(*a,**kw):raise AssertionError('second decode')
  monkeypatch.setattr(analysis,'keyframe_stream',forbidden)
  p,_=analyze_project(source,AnalysisSettings(roi_mode='full'),tmp_path/'cache',prepared=prepared)
  q,_=analyze_project(source,replace(p.settings,roi_mode='manual'),tmp_path/'cache',previous=p)
  assert q.samples is p.samples and q.cache_generation==prepared.cache_generation
  with pytest.raises(ValueError,match='algorithm'):
   analyze_project(source,AnalysisSettings(),tmp_path/'cache',prepared=replace(prepared,sampling_algorithm='bucket-first-v1'))
 finally:prepared.discard()

def test_default_window_uses_keyframes_without_sampling_controls(tmp_path,monkeypatch):
 app=QApplication.instance() or QApplication([]);w=Window();w.show()
 assert not hasattr(w,'fps') and not hasattr(w,'_fps_changed')
 def inspect_dialog(dialog):
  assert not dialog.findChildren(QComboBox)
  return QDialog.DialogCode.Accepted
 monkeypatch.setattr(QDialog,'exec',inspect_dialog)
 try:w.open_advanced()
 finally:w.close();spin(app,lambda:not w.isVisible())

def test_exact_export_rejects_nonkeyframe_and_uses_keyframe_decoder(tmp_path,monkeypatch):
 source=video(tmp_path/'source.mkv');samples,_=pts.keyframe_stream(source,tmp_path/'cache')
 commands=[];real=pts._ffmpeg
 def observed(*a,**kw):
  cmd=real(*a,**kw);commands.append(cmd);return cmd
 monkeypatch.setattr(pts,'_ffmpeg',observed)
 pts.extract_selected(source,samples,tmp_path/'full')
 assert commands and all('-skip_frame' in c and c[c.index('-skip_frame')+1]=='nokey' for c in commands)
 probe=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_frames','-show_entries','frame=key_frame,pts','-of','json',str(source.path)]))
 nonkey=next(int(f['pts']) for f in probe['frames'] if f['key_frame']==0)
 with pytest.raises(Exception,match='PTS missing'):pts.extract_selected(source,[nonkey],tmp_path/'invalid')
 assert not list((tmp_path/'invalid').glob('*.png'))

def test_first_roi_preview_uses_audited_keyframes(tmp_path,monkeypatch):
 from gui.preparation import prepare_first_frame
 source=video(tmp_path/'source.mkv');seen=[];real=pts._ffmpeg
 def observed(*a,**kw):
  cmd=real(*a,**kw);seen.append(cmd);return cmd
 monkeypatch.setattr(pts,'_ffmpeg',observed)
 rgb,w,h,roi,warning=prepare_first_frame(source)
 assert len(rgb)==w*h*3 and seen
 assert all('-skip_frame' in c for c in seen)

def test_packaged_source_excludes_fps_runtime_and_legacy_runner(tmp_path):
 module=runpy.run_path(str(ROOT/'packaging/build_source_zip.py'))
 path=tmp_path/'source.zip';module['build'](path,include_tests=False)
 with zipfile.ZipFile(path) as z:
  names=z.namelist()
  assert not any('/legacy_fps/' in n or n.endswith('export_v3.py') or n.endswith('timeline_json.py') for n in names)
  text=z.read('SlideExtractor/slide_core/pts.py').decode()
  assert 'def sample_stream' not in text

def test_product_imports_never_load_legacy_modules():
 result=subprocess.check_output([__import__('sys').executable,'-c',"import app,slide_core.analysis,slide_core.preparation;import sys;print([x for x in sys.modules if x.startswith('legacy_fps')])"],cwd=ROOT,text=True)
 assert result.strip()=='[]'

def test_product_has_no_sampler_or_decoder_override(tmp_path):
 assert 'sampler' not in inspect.signature(analyze_project).parameters
 assert 'decode_options' not in inspect.signature(analyze_project).parameters
 source=video(tmp_path/'source.mkv')
 with pytest.raises(ValueError,match='keyframes'):
  pts._ffmpeg(source,'null',decode_options={'backend':'cpu-metadata'})

def test_developer_source_zip_and_benchmarks_use_current_product(tmp_path,monkeypatch):
 module=runpy.run_path(str(ROOT/'packaging/build_source_zip.py'))
 path=tmp_path/'developer.zip';module['build'](path,include_tests=True)
 with zipfile.ZipFile(path) as z:
  for name in z.namelist():
   if name.endswith('.py') and '/tests/' not in name:
    text=z.read(name).decode()
    assert 'from slide_core.export_v3 import' not in text
    assert 'AnalysisSettings(fps=' not in text
 core=runpy.run_path(str(ROOT/'scripts/benchmark_core.py'))
 source=video(tmp_path/'source.mkv')
 report=core['run'](source.path,tmp_path/'core',rounds=1)
 assert report['runs'][0]['pdf_bytes']>0
 assert report['runs'][0]['sampling_algorithm']=='decoder-keyframes-v1'
 bench=runpy.run_path(str(ROOT/'scripts/benchmark-analysis.py'))
 bench['main'].__globals__['ROOT']=tmp_path
 monkeypatch.setattr(__import__('sys'),'argv',['benchmark',str(source.path),'--rounds','1'])
 assert bench['main']()==0
 report=json.loads(next((tmp_path/'profiles').glob('benchmark-*.json')).read_text())
 assert report['runs'][0]['profile']['sampling_algorithm']=='decoder-keyframes-v1'

def test_core_benchmark_runs_without_posix_resource(tmp_path,monkeypatch):
 import sys
 source=video(tmp_path/'source.mkv')
 monkeypatch.setitem(sys.modules,'resource',None)
 core=runpy.run_path(str(ROOT/'scripts/benchmark_core.py'))
 report=core['run'](source.path,tmp_path/'core',rounds=1)
 assert report['runs'][0]['pdf_bytes']>0
 assert report['runs'][0]['parent_maxrss_kib'] is None
 assert report['runs'][0]['child_maxrss_kib'] is None
