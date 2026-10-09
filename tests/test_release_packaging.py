import json
import os
import runpy
from pathlib import Path
import zipfile

ROOT=Path(__file__).resolve().parents[1]

def test_shared_spec_uses_entrypoint_data_and_version(tmp_path,monkeypatch):
    import sys
    monkeypatch.setattr(sys,'platform','darwin')
    monkeypatch.setenv('APPROVED_FFMPEG_DIR',str(tmp_path))
    for name in ('ffmpeg','ffprobe'):(tmp_path/name).write_bytes(b'tool')
    (tmp_path/'licenses').mkdir()
    (tmp_path/'licenses/COPYING').write_text('license')
    (tmp_path/'SBOM.json').write_text('{}')
    (tmp_path/'SOURCE_AND_REPLACEMENT.md').write_text('instructions')
    build_input=tmp_path/'build-manifest.json';build_input.write_text('{}')
    monkeypatch.setenv('SLIDE_BUILD_MANIFEST',str(build_input))
    calls={}
    def analysis(scripts,**kwargs):
        calls.update(scripts=scripts,**kwargs)
        return type('A',(),dict(pure=[],scripts=[],binaries=[],datas=[]))()
    def bundle(*args,**kwargs):calls['bundle']=kwargs
    runpy.run_path(str(ROOT/'packaging/SlideExtractor.spec'),init_globals={
        'SPECPATH':str(ROOT/'packaging'),'Analysis':analysis,'PYZ':lambda *a,**kw:None,
        'EXE':lambda *a,**kw:None,'COLLECT':lambda *a,**kw:None,'BUNDLE':bundle})
    from slide_core.version import VERSION,BUNDLE_VERSION
    assert calls['scripts']==[str(ROOT/'packaging/desktop_entry.py')]
    assert all(Path(p).name in ('ffmpeg','ffprobe') for p,_ in calls['binaries'])
    assert {Path(p).name for p,_ in calls['datas']} >= {'THIRD_PARTY_NOTICES.md','LICENSE_AUDIT.md'}
    assert calls['bundle']['version']==BUNDLE_VERSION
    assert VERSION.startswith('0.4.9')

def test_archive_contains_complete_build_inputs(tmp_path):
    module=runpy.run_path(str(ROOT/'packaging/build_source_zip.py'))
    dest=tmp_path/'source.zip'
    module['build'](dest,include_tests=True)
    with zipfile.ZipFile(dest) as archive:
        names=set(archive.namelist())
    for name in ('requirements-dev.txt','packaging/requirements-macos-arm64.lock','packaging/build_manifest.py','slide_core/version.py'):
        assert 'SlideExtractor/'+name in names
    assert 'SlideExtractor/engine.py' not in names
    assert 'SlideExtractor/tests/export_fixtures.py' in names

def test_manifest_records_exact_tools_and_packages(tmp_path):
    module=runpy.run_path(str(ROOT/'packaging/build_manifest.py'))
    for name in ('ffmpeg','ffprobe'):
        tool=tmp_path/name
        tool.write_text('#!/bin/sh\nprintf "fake version\\nconfiguration: --disable-gpl\\n"\n')
        tool.chmod(0o755)
    result=module['manifest'](tmp_path,'personal')
    assert result['public_release_approved'] is False
    assert result['tools']['ffmpeg']['sha256']
    assert '--disable-gpl' in result['tools']['ffmpeg']['version_output']
    assert result['packages']['numpy']
    assert result['version'].startswith('0.4.9')
