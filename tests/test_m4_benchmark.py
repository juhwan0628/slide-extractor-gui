"""External harness must measure actual workers and fail closed."""
import json, os, subprocess, sys
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[1]
HARNESS=ROOT/'legacy_fps'/'benchmark_m4.py'
pytestmark=pytest.mark.skipif(sys.platform!='linux' or not HARNESS.is_file(),reason='External Linux benchmark tooling; not shipped with product')

def run_worker(video,output,*extra):
 return subprocess.run([sys.executable,str(HARNESS),'--worker','--source',str(ROOT),'--video',str(video),'--output',str(output),'--mode','keyframes',*extra],cwd=ROOT,env={**os.environ,'PYTHONPATH':str(ROOT),'QT_QPA_PLATFORM':'offscreen'},capture_output=True,text=True,timeout=60)

def test_real_worker_prepared_analysis_and_paired_export(tmp_path):
 from tests.test_keyframe_sampling import video
 source=video(tmp_path/'source.mkv')
 output=tmp_path/'out'
 result=run_worker(source.path,output)
 assert result.returncode==0,result.stderr
 report=json.loads((output/'report.json').read_text())
 assert report['status']=='success'
 assert report['sample_pts'] and report['representative_pts']
 assert report['sampling_algorithm']=='decoder-keyframes-v1'
 assert report['cache_bytes']>0 and report['pdf_bytes']>0
 assert report['seconds']['preparation']>0 and report['seconds']['ready_analysis']>0
 assert report['preparation_profile']['seconds']['decode_wait']>=0
 assert report['analysis_profile']['cache_reused'] is True
 assert report['json_schema']==4
 assert report['decoder_invocations_before_export']==1
 assert report['decoder_modes_before_export']==['keyframes']
 assert report['export_decoder_invocations']==report['pages']
 assert sum(report['export_phases'].values())==pytest.approx(report['seconds']['export'])
 assert report['worker_source']==str(ROOT)
 assert report['cpu_seconds']['parent']>=0 and report['cpu_seconds']['children']>=0

def test_worker_failure_is_nonzero_and_reported(tmp_path):
 result=run_worker(tmp_path/'missing.mp4',tmp_path/'out')
 assert result.returncode!=0
 report=json.loads((tmp_path/'out'/'report.json').read_text())
 assert report['status']=='failed' and report['error_type']

@pytest.mark.parametrize('click',['early','ready'])
def test_worker_background_single_producer_click_paths(tmp_path,click):
 from tests.test_keyframe_sampling import video
 source=video(tmp_path/'source.mkv')
 result=run_worker(source.path,tmp_path/'out','--click',click)
 assert result.returncode==0,result.stderr
 report=json.loads((tmp_path/'out'/'report.json').read_text())
 assert report['background_producers']==1
 assert report['decoder_invocations_before_export']==1
 assert report['analysis_profile']['cache_reused'] is True
 assert report['seconds']['click_to_result']>=report['seconds']['ready_analysis']
 assert report['background_done'] is True

def test_worker_cleanup_failure_still_writes_failed_report(tmp_path,monkeypatch):
 from argparse import Namespace
 import importlib.util
 from tests.test_keyframe_sampling import video
 from slide_core.preparation import PreparedSamples
 spec=importlib.util.spec_from_file_location('m4worker',HARNESS);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
 source=video(tmp_path/'source.mkv')
 real=PreparedSamples.discard
 def fail(prepared):
  real(prepared)
  raise OSError('injected cleanup failure')
 monkeypatch.setattr(PreparedSamples,'discard',fail)
 args=Namespace(source=str(ROOT),output=str(tmp_path/'out'),video=str(source.path),mode='keyframes',click=None,sheets=False,no_export=True)
 assert module.worker(args)==1
 report=json.loads((tmp_path/'out'/'report.json').read_text())
 assert report['status']=='failed' and 'cleanup' in report['error'].lower()

def test_worker_rejects_missing_source_tree_instead_of_importing_product(tmp_path):
 from tests.test_keyframe_sampling import video
 source=video(tmp_path/'source.mkv')
 result=subprocess.run([sys.executable,str(HARNESS),'--worker','--source',str(tmp_path/'missing-tree'),'--video',str(source.path),'--output',str(tmp_path/'out'),'--mode','keyframes','--no-export'],cwd=ROOT,env={**os.environ,'PYTHONPATH':str(ROOT)},capture_output=True,text=True,timeout=30)
 assert result.returncode!=0
 report=json.loads((tmp_path/'out'/'report.json').read_text())
 assert report['status']=='failed'

def test_background_cleanup_deadline_is_failure(tmp_path,monkeypatch):
 from argparse import Namespace
 import importlib.util
 from tests.test_keyframe_sampling import video
 from gui import sample_preparation
 spec=importlib.util.spec_from_file_location('m4worker',HARNESS);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
 real=sample_preparation.BackgroundSamples
 class Done:
  def __init__(self,event):self.event=event
  def set(self):self.event.set()
  def wait(self,timeout):self.event.wait(timeout);return False
 def task(*args,**kw):
  result=real(*args,**kw);result.done=Done(result.done);return result
 monkeypatch.setattr(sample_preparation,'BackgroundSamples',task)
 source=video(tmp_path/'source.mkv')
 args=Namespace(source=str(ROOT),output=str(tmp_path/'out'),video=str(source.path),mode='keyframes',click='ready',sheets=False,no_export=True)
 assert module.worker(args)==1
 report=json.loads((tmp_path/'out'/'report.json').read_text())
 assert report['status']=='failed' and report['background_done'] is False
