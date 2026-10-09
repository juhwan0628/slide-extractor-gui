from slide_core.version import VERSION
import hashlib
import json
import os
from pathlib import Path
import runpy
import zipfile
import pytest

ROOT=Path(__file__).resolve().parents[1]

def builder():return runpy.run_path(str(ROOT/'packaging/build_windows_personal.py'))

def test_tools_can_use_local_folder_with_spaces_and_dlls(tmp_path):
    folder=tmp_path/'한글 tool folder';folder.mkdir()
    for name in ('ffmpeg.exe','ffprobe.exe','avcodec-62.dll'):(folder/name).write_bytes(name.encode())
    module=builder();tools=module['find_tools'](folder)
    stage=tmp_path/'staged';module['stage_tools'](tools,stage)
    assert (stage/'ffmpeg.exe').read_bytes()==b'ffmpeg.exe'
    assert (stage/'avcodec-62.dll').read_bytes()==b'avcodec-62.dll'

def test_explicit_tool_folder_does_not_silently_use_other_path(tmp_path,monkeypatch):
    (tmp_path/'ffmpeg.exe').write_bytes(b'tool')
    monkeypatch.setenv('PATH','/usr/bin')
    with pytest.raises(FileNotFoundError,match='ffprobe'):builder()['find_tools'](tmp_path)

def fake_app(tmp_path,result=None):
    exe=tmp_path/'fake app.exe'
    script='#!/bin/sh\n'
    if result is not None:
        script+='printf \'%s\' \''+json.dumps(result)+'\' > "$2"\n'
    exe.write_text(script+'exit 0\n');exe.chmod(0o755)
    return exe

@pytest.mark.skipif(os.name!='posix',reason='POSIX process fixture; native Windows smoke is separate device validation')
def test_smoke_rejects_stale_success_report(tmp_path):
    report=tmp_path/'smoke.json';report.write_text(json.dumps({'status':'success','frozen':True,'bundled_tools_checked':True,'version':VERSION}))
    with pytest.raises(ValueError,match='report'):builder()['run_smoke'](fake_app(tmp_path),report)

@pytest.mark.skipif(os.name!='posix',reason='POSIX process fixture; native Windows smoke is separate device validation')
def test_smoke_requires_bundled_frozen_result(tmp_path):
    result={'status':'success','frozen':False,'bundled_tools_checked':False,'version':VERSION}
    with pytest.raises(ValueError,match='Bundled'):builder()['run_smoke'](fake_app(tmp_path,result),tmp_path/'report.json')

@pytest.mark.skipif(os.name!='posix',reason='POSIX process fixture; native Windows smoke is separate device validation')
def test_smoke_accepts_actual_report_from_launched_process(tmp_path):
    result={'status':'success','frozen':True,'bundled_tools_checked':True,'version':VERSION}
    actual=builder()['run_smoke'](fake_app(tmp_path,result),tmp_path/'report.json')
    assert actual==result

def test_portable_zip_has_app_validation_guide_and_hash(tmp_path):
    bundle=tmp_path/'SlideExtractor';(bundle/'_internal/tools').mkdir(parents=True)
    (bundle/'SlideExtractor.exe').write_bytes(b'native exe fixture')
    (bundle/'_internal/tools/ffmpeg.exe').write_bytes(b'tool fixture')
    output=tmp_path/'out';output.mkdir()
    archive=builder()['portable_zip'](bundle,output)
    with zipfile.ZipFile(archive) as z:
        assert z.read('SlideExtractor/SlideExtractor.exe')==b'native exe fixture'
        assert 'SlideExtractor/VALIDATE-WINDOWS.bat' in z.namelist()
        assert 'SlideExtractor/INSTALL-WINDOWS.md' in z.namelist()
    assert hashlib.sha256(archive.read_bytes()).hexdigest() in archive.with_suffix('.zip.sha256').read_text()

def test_source_zip_contains_windows_build_and_validation_entrypoints(tmp_path):
    archive=tmp_path/'source.zip'
    runpy.run_path(str(ROOT/'packaging/build_source_zip.py'))['build'](archive)
    with zipfile.ZipFile(archive) as z:
        for name in ('BUILD-WINDOWS.bat','INSTALL-WINDOWS.md','packaging/build_windows_personal.py','scripts/validate-windows-portable.bat'):
            assert 'SlideExtractor/'+name in z.namelist()
