"""Real and failure-injected keyframe PDF/JSON publication."""
from pathlib import Path
from dataclasses import replace
import hashlib,json
from uuid import uuid4
import pytest
from pypdf import PdfReader
from slide_core.analysis import analyze_project
from slide_core.config import AnalysisSettings
from slide_core.models import CancelToken
from tests.test_keyframe_sampling import video,keyframes
from tests.export_fixtures import make_project,extract_stub

@pytest.mark.parametrize('format',['detailed','simple'])
@pytest.mark.parametrize('vfr,offset',[(True,0),(False,8)])
def test_real_keyframes_export_with_matching_pdf_and_json(tmp_path,format,vfr,offset):
 from slide_core.keyframe_export import export_project
 from slide_core.keyframe_json import loads
 from slide_core.simple_json import simple_timeline
 source=video(tmp_path/'source.mkv',vfr=vfr,offset=offset)
 p,_=analyze_project(source,AnalysisSettings(roi_mode='full'),tmp_path/'cache')
 try:
  pdf,side=export_project(p,tmp_path/'out.pdf',sidecar_format=format)
  assert len(PdfReader(pdf).pages)==len(p.pages)
  if format=='detailed':
   data=loads(side.read_bytes(),pdf_bytes=pdf.read_bytes(),pdf_page_count=len(p.pages))
   assert [s['source_pts'] for s in data['samples']]==keyframes(source)
   assert PdfReader(pdf).metadata.subject.endswith(data['artifact']['export_id'])
  else:assert json.loads(side.read_bytes())==simple_timeline(p)
  assert not list(tmp_path.glob('*.lock')) and not list(tmp_path.glob('.slide-export-*'))
 finally:p._cache_pin.close()

@pytest.mark.parametrize('format',['detailed','simple'])
@pytest.mark.parametrize('mutation',['pages','settings'])
def test_project_mutated_during_render_never_publishes_pair(tmp_path,monkeypatch,format,mutation):
 from slide_core import keyframe_export as engine
 p=make_project(tmp_path);stub=extract_stub(p)
 def mutate(*a,**kw):
  paths=stub(*a,**kw)
  if mutation=='pages':p.pages=[]
  else:p.settings=replace(p.settings,settings_revision=1)
  return paths
 monkeypatch.setattr(engine,'extract_selected',mutate)
 with pytest.raises(RuntimeError,match='Project changed'):
  engine.export_project(p,tmp_path/'out.pdf',sidecar_format=format)
 assert not (tmp_path/'out.pdf').exists() and not (tmp_path/'out.json').exists()
 assert not list(tmp_path.glob('.slide-export-*'))

def test_cancel_before_publish_preserves_previous_pair(tmp_path,monkeypatch):
 from slide_core import keyframe_export as engine
 p=make_project(tmp_path);stub=extract_stub(p);token=CancelToken()
 pdf=tmp_path/'out.pdf';pdf.write_bytes(b'old pdf');side=pdf.with_suffix('.json');side.write_bytes(b'old json')
 def cancel(*a,**kw):paths=stub(*a,**kw);token.cancel();return paths
 monkeypatch.setattr(engine,'extract_selected',cancel)
 with pytest.raises(Exception):engine.export_project(p,pdf,overwrite=True,cancel_token=token)
 assert pdf.read_bytes()==b'old pdf' and side.read_bytes()==b'old json' and not token.committed

@pytest.mark.parametrize('format',['detailed','simple'])
def test_cancel_after_publication_is_recorded_as_saved(tmp_path,monkeypatch,format):
 from slide_core import keyframe_export as engine
 p=make_project(tmp_path);monkeypatch.setattr(engine,'extract_selected',extract_stub(p))
 token=CancelToken();real=engine._recover_one
 def cancel(*a,**kw):token.cancel();return real(*a,**kw)
 monkeypatch.setattr(engine,'_recover_one',cancel)
 pdf,side=engine.export_project(p,tmp_path/'out.pdf',sidecar_format=format,cancel_token=token)
 assert token.committed and token.cancelled and pdf.is_file() and side.is_file()

def test_forged_nonkeyframe_pts_are_not_substituted(tmp_path):
 from slide_core.keyframe_export import export_project
 source=video(tmp_path/'source.mkv');p,_=analyze_project(source,AnalysisSettings(roi_mode='full'),tmp_path/'cache')
 try:
  # Change a selected sample to a real P/B PTS with same cache; extraction must fail.
  import subprocess
  data=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_frames','-show_entries','frame=key_frame,pts','-of','json',str(source.path)]))
  nonkey=next(int(x['pts']) for x in data['frames'] if x['key_frame']==0)
  from slide_core.editing import add_page
  add_page(p,p.samples[0].actual_time)
  p.pages=[x for x in p.pages if x.representative_sample_id==p.samples[0].sample_id]
  p.samples=(replace(p.samples[0],source_pts=nonkey),)+p.samples[1:]
  # Project records still reference first observation time, so validation may fail earlier.
  with pytest.raises(Exception):export_project(p,tmp_path/'forged.pdf')
  assert not (tmp_path/'forged.pdf').exists()
 finally:p._cache_pin.close()


@pytest.mark.parametrize('format',['detailed','simple'])
@pytest.mark.parametrize('change',['project','cancel'])
@pytest.mark.parametrize('existing',[False,True])
def test_publication_guard_rechecks_after_output_lock_before_any_output_changes(tmp_path,monkeypatch,format,change,existing):
 from contextlib import contextmanager
 from slide_core import keyframe_export as engine,export as core
 from slide_core.models import CancelledError
 p=make_project(tmp_path);monkeypatch.setattr(engine,'extract_selected',extract_stub(p))
 target=tmp_path/'out.pdf';side=target.with_suffix('.json');token=CancelToken()
 if existing:target.write_bytes(b'old pdf');side.write_bytes(b'old json')
 real=core.export_file_lease;fired=[]
 @contextmanager
 def delayed(path):
  with real(path) as handle:
   if Path(path)==core.output_lock_path(target) and not fired:
    fired.append(True)
    if change=='project':p.pages=[];p.revision+=1
    else:token.cancel()
   yield handle
 monkeypatch.setattr(core,'export_file_lease',delayed)
 error=RuntimeError if change=='project' else CancelledError
 with pytest.raises(error):
  engine.export_project(p,target,overwrite=existing,sidecar_format=format,cancel_token=token)
 assert fired and not token.committed
 if existing:assert target.read_bytes()==b'old pdf' and side.read_bytes()==b'old json'
 else:assert not target.exists() and not side.exists()
 assert not list(tmp_path.glob('.slide-export-*')) and not list(tmp_path.glob('*.lock'))
