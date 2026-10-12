"""The native release gate must reject incomplete or legacy candidates."""
import runpy
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[1]
def contract():
 return runpy.run_path(str(ROOT/'packaging/keyframe_release_contract.py'))
def valid():
 return dict(version='0.5.0b1',status='success',frozen=True,decoder_backend='cpu-keyframes',
  **{k:True for k in ('bundled_tools_checked','pdf_only_checked','output_lock_cleanup_checked',
  'background_preparation_checked','save_options_checked','start_over_cache_cleanup_checked',
  'manual_editing_checked','keyboard_editing_checked','edited_export_checked',
  'keyframe_json_v4_checked','simple_json_checked','keyframe_only_checked','legacy_modules_absent_checked')})
@pytest.mark.parametrize('field',list(valid()))
def test_native_contract_rejects_missing_evidence(field):
 report=valid();del report[field]
 with pytest.raises(ValueError):contract()['validate_smoke'](report,'0.5.0b1')
@pytest.mark.parametrize('field',[k for k,v in valid().items() if v is True])
def test_native_contract_rejects_false_or_truthy_evidence(field):
 for bad in (False,1,'true'):
  report=valid();report[field]=bad
  with pytest.raises(ValueError):contract()['validate_smoke'](report,'0.5.0b1')
def test_native_contract_accepts_observed_current_smoke():
 contract()['validate_smoke'](valid(),'0.5.0b1')
@pytest.mark.parametrize('name',['legacy_fps','legacy_fps.benchmark_m4','slide_core.export_v3','slide_core.timeline_json'])
def test_native_contract_rejects_legacy_module(name):
 with pytest.raises(ValueError):contract()['verify_modules'](['app','slide_core.analysis',name])
def test_native_contract_rejects_other_version_or_decoder():
 for key,bad in [('version','0.4.12rc1'),('decoder_backend','cpu-metadata'),('status','failed')]:
  report=valid();report[key]=bad
  with pytest.raises(ValueError):contract()['validate_smoke'](report,'0.5.0b1')
def test_native_contract_allows_source_smoke_only_when_explicit():
 report=valid();report['frozen']=False;report['bundled_tools_checked']=False
 contract()['validate_smoke'](report,'0.5.0b1',require_frozen=False)
 with pytest.raises(ValueError):contract()['validate_smoke'](report,'0.5.0b1')

def test_installed_smoke_records_current_keyframe_contract(tmp_path):
 import json
 from slide_core.version import VERSION
 entry=runpy.run_path(str(ROOT/'packaging/desktop_entry.py'))
 target=tmp_path/'smoke.json';entry['smoke'](target)
 contract()['validate_smoke'](json.loads(target.read_text()),VERSION,require_frozen=False)

def test_spec_rejects_legacy_module_in_actual_analysis_toc(tmp_path,monkeypatch):
 import sys
 monkeypatch.setattr(sys,'platform','darwin')
 monkeypatch.setenv('APPROVED_FFMPEG_DIR',str(tmp_path))
 for name in ('ffmpeg','ffprobe','SBOM.json','SOURCE_AND_REPLACEMENT.md'):
  (tmp_path/name).write_text('fixture')
 (tmp_path/'licenses').mkdir()
 manifest=tmp_path/'build-manifest.json';manifest.write_text('{}')
 monkeypatch.setenv('SLIDE_BUILD_MANIFEST',str(manifest))
 class Analysis:
  def __init__(self,*args,**kwargs):
   self.pure=[('legacy_fps.benchmark_m4','fixture.py','PYMODULE')]
   self.scripts=self.binaries=self.datas=[]
 with pytest.raises(ValueError,match='Legacy modules'):
  runpy.run_path(str(ROOT/'packaging/SlideExtractor.spec'),init_globals={
   'SPECPATH':str(ROOT/'packaging'),'Analysis':Analysis,'PYZ':lambda *a,**kw:None,
   'EXE':lambda *a,**kw:None,'COLLECT':lambda *a,**kw:None,'BUNDLE':lambda *a,**kw:None})
