import runpy
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[1]

def test_approved_tools_require_native_helper_and_evidence(tmp_path):
 f=runpy.run_path(str(ROOT/'packaging/native_helper_contract.py'))['bundle_tools']
 for name in ('ffmpeg','ffprobe'):(tmp_path/name).write_bytes(b'fixture')
 with pytest.raises(ValueError,match='helper'):f(tmp_path,'',approved=True)
 (tmp_path/'slide-keyframe-decode').write_bytes(b'helper')
 with pytest.raises(ValueError,match='evidence'):f(tmp_path,'',approved=True)

def test_helper_hash_is_verified(tmp_path):
 import hashlib,json
 f=runpy.run_path(str(ROOT/'packaging/native_helper_contract.py'))['bundle_tools']
 for name in ('ffmpeg','ffprobe','slide-keyframe-decode'):(tmp_path/name).write_bytes(b'fixture')
 p=tmp_path/'native-helper-build.json';p.write_text(json.dumps({'helper_sha256':'wrong'}))
 with pytest.raises(ValueError,match='schema'):f(tmp_path,'',approved=True)
 p.write_text(json.dumps({'helper_sha256':hashlib.sha256(b'fixture').hexdigest()}))
 with pytest.raises(ValueError,match='schema'):f(tmp_path,'',approved=True)

def test_personal_build_keeps_cpu_fallback(tmp_path):
 f=runpy.run_path(str(ROOT/'packaging/native_helper_contract.py'))['bundle_tools']
 for name in ('ffmpeg','ffprobe'):(tmp_path/name).write_bytes(b'fixture')
 assert len(f(tmp_path,'',approved=False))==2

def test_native_release_gate_requires_half_evidence():
    from tests.test_keyframe_release_contract import valid
    f=runpy.run_path(str(ROOT/'packaging/keyframe_release_contract.py'))['validate_smoke']
    with pytest.raises(ValueError,match='native'):
        f(valid(),'0.5.0b1',require_native=True)

def test_approved_contract_rejects_hash_only_evidence(tmp_path):
    import hashlib,json
    f=runpy.run_path(str(ROOT/'packaging/native_helper_contract.py'))['bundle_tools']
    for name in ('ffmpeg','ffprobe','slide-keyframe-decode'):(tmp_path/name).write_bytes(b'fixture')
    (tmp_path/'native-helper-build.json').write_text(json.dumps({'helper_sha256':hashlib.sha256(b'fixture').hexdigest()}))
    with pytest.raises(ValueError,match='schema'):f(tmp_path,'',approved=True)


def evidence_fixture(root):
    import hashlib,json
    kit=root/'helper-relink';(kit/'ffmpeg-libraries').mkdir(parents=True)
    for name in ('ffmpeg','ffprobe','slide-keyframe-decode'):(root/name).write_bytes(b'fixture')
    (kit/'keyframe_decode.cpp').write_bytes((ROOT/'native/keyframe_decode.cpp').read_bytes())
    (kit/'keyframe_decode.o').write_bytes(b'object')
    libraries={}
    for name in ('libavformat.a','libavcodec.a','libavfilter.a','libavutil.a'):
        (kit/'ffmpeg-libraries'/name).write_bytes(name.encode());libraries[name]=hashlib.sha256(name.encode()).hexdigest()
    command='c++ keyframe_decode.o '+' '.join(libraries)+' -o slide-keyframe-decode\n'
    (kit/'link-command.txt').write_text(command)
    data=dict(schema_version=1,helper_sha256=hashlib.sha256(b'fixture').hexdigest(),
        helper_source_sha256=hashlib.sha256((kit/'keyframe_decode.cpp').read_bytes()).hexdigest(),
        ffmpeg_source=json.loads((ROOT/'packaging/native-sources.lock.json').read_text())['ffmpeg'],
        ffmpeg_libraries=libraries,link_command=command,relink_object_sha256=hashlib.sha256(b'object').hexdigest(),public_release_approved=False)
    (root/'native-helper-build.json').write_text(json.dumps(data))
    return kit

def test_complete_evidence_rejects_missing_or_changed_relink_file(tmp_path):
    f=runpy.run_path(str(ROOT/'packaging/native_helper_contract.py'))['bundle_tools']
    kit=evidence_fixture(tmp_path)
    assert len(f(tmp_path,'',approved=True))==3
    (kit/'ffmpeg-libraries/libavcodec.a').write_bytes(b'changed')
    with pytest.raises(ValueError,match='hash'):f(tmp_path,'',approved=True)

def test_review_requires_installed_native_evidence(tmp_path):
    f=runpy.run_path(str(ROOT/'packaging/review_candidate.py'))['review_native_materials']
    with pytest.raises(ValueError,match='native'):
        f(tmp_path,tmp_path,{},'.exe')

def test_evidence_rejects_ambiguous_dynamic_link_flags(tmp_path):
    import json
    f=runpy.run_path(str(ROOT/'packaging/native_helper_contract.py'))['bundle_tools']
    kit=evidence_fixture(tmp_path)
    record=tmp_path/'native-helper-build.json';data=json.loads(record.read_text())
    data['link_command']='c++ keyframe_decode.o -lavformat -lavcodec -lavfilter -lavutil\n'
    (kit/'link-command.txt').write_text(data['link_command']);record.write_text(json.dumps(data))
    with pytest.raises(ValueError,match='static'):f(tmp_path,'',approved=True)

def test_helper_recipe_accepts_empty_platform_link_flags(tmp_path):
    import os,shutil,subprocess
    shell=os.environ.get('SLIDE_TEST_BASH','/bin/bash')
    if not Path(shell).is_file():pytest.skip('POSIX build shell unavailable')
    (tmp_path/'packaging').mkdir();(tmp_path/'native').mkdir()
    shutil.copyfile(ROOT/'packaging/build-native-helper.sh',tmp_path/'packaging/build-native-helper.sh')
    (tmp_path/'native/keyframe_decode.cpp').write_text('// fixture')
    sdk=tmp_path/'build/ffmpeg-sdk/lib';(sdk/'pkgconfig').mkdir(parents=True)
    for name in ('avformat','avcodec','avfilter','avutil'):(sdk/('lib'+name+'.a')).write_bytes(b'archive')
    tools=tmp_path/'tools';tools.mkdir()
    scripts={
        'uname':'#!/bin/sh\necho Darwin\n',
        'pkg-config':'#!/bin/sh\ncase "$*" in *--cflags*) exit 0;; esac\necho "-lavformat -lavcodec -lavfilter -lavutil"\n',
        'clang++':'#!/bin/sh\nwhile [ "$#" -gt 0 ]; do\nif [ "$1" = "-o" ]; then shift; : > "$1"; fi\nshift\ndone\n',
        'python':'#!/bin/sh\nexit 0\n'}
    for name,content in scripts.items():
        p=tools/name;p.write_text(content);p.chmod(0o755)
    result=subprocess.run([shell,str(tmp_path/'packaging/build-native-helper.sh')],env={**os.environ,'PATH':str(tools)+os.pathsep+os.environ['PATH']},capture_output=True,text=True)
    assert result.returncode==0,result.stderr
    assert (tmp_path/'vendor/approved/helper-relink/link-command.txt').is_file()

def test_real_native_smoke_uses_unicode_input(tmp_path,monkeypatch):
    import sys
    extension='.exe' if sys.platform=='win32' else ''
    helper=next((p for p in (ROOT/'vendor/approved'/('slide-keyframe-decode'+extension),ROOT/'build/native'/('slide-keyframe-decode'+extension)) if p.is_file()),None)
    if helper is None:pytest.skip('Native helper not built on this host')
    monkeypatch.setenv('SLIDE_NATIVE_KEYFRAME_HELPER',str(helper))
    from slide_core import preparation
    real=preparation.prepare_samples;seen=[]
    def spy(source,*a,**kw):
        seen.append(Path(source).name);return real(source,*a,**kw)
    monkeypatch.setattr(preparation,'prepare_samples',spy)
    entry=runpy.run_path(str(ROOT/'packaging/desktop_entry.py'))
    result=entry['verify_native_half'](tmp_path,frozen=False)
    assert result['native_half_checked'] is True
    assert seen==['H264 한글 경로 영상.mp4']
