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
