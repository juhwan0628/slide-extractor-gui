import hashlib
import json
import runpy
from pathlib import Path
import pytest

ROOT=Path(__file__).resolve().parents[1]

def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def fixture(tmp_path):
    root=tmp_path/'bundle';root.mkdir()
    (root/'SlideExtractor').write_bytes(b'app')
    (root/'THIRD_PARTY_NOTICES.md').write_text('notices')
    (root/'licenses').mkdir();(root/'licenses/COPYING.txt').write_text('license copy')
    (root/'SBOM.json').write_text(json.dumps({'components':[{'name':'Qt','version':'6.12.0'},{'name':'FFmpeg'},{'name':'Python'}]}))
    (root/'SOURCE_AND_REPLACEMENT.md').write_text('Source archive locations and replacement instructions')
    tool=root/'ffmpeg';tool.write_text('#!/bin/sh\nprintf "fake version\\nconfiguration: --disable-gpl\\n"\n');tool.chmod(0o755)
    probe=root/'ffprobe';probe.write_bytes(tool.read_bytes());probe.chmod(0o755)
    source=tmp_path/'source.tar';source.write_bytes(b'exact source archive fixture')
    component={'version':'fixture','corresponding_source_url':'https://example.test/source','source_sha256':digest(source),'source_archive_local':str(source)}
    payload={'status':'APPROVED','ffmpeg':dict(component,supplier='test',configure='--disable-gpl',sha256=digest(tool),bundle_sha256=digest(tool)),
             'ffprobe':{'sha256':digest(probe),'bundle_sha256':digest(probe)},
             'qt':dict(component,modules=['QtCore','QtWidgets'],replacement_verified=True),
             'bundle':{key:True for key in ('third_party_notices_included','license_copies_included','sbom_included','pymupdf_absent','clean_machine_smoke_verified','native_installer_verified','signed_or_notarization_state_recorded')}}
    build=root/'build-manifest.json'
    build.write_text(json.dumps({'version':'0.4.9rc1','tools':{name:{'sha256':payload[name]['sha256']} for name in ('ffmpeg','ffprobe')}}))
    payload['bundle'].update(candidate_version='0.4.9rc1',build_manifest_sha256=digest(build))
    manifest=tmp_path/'manifest.json';manifest.write_text(json.dumps(payload))
    return root,tool,manifest,payload

@pytest.mark.parametrize('missing',['licenses','SBOM.json','SOURCE_AND_REPLACEMENT.md'])
def test_gate_checks_actual_materials_not_declared_flags(tmp_path,missing):
    import shutil
    root,tool,manifest,_=fixture(tmp_path)
    target=root/missing
    shutil.rmtree(target) if target.is_dir() else target.unlink()
    errors=runpy.run_path(str(ROOT/'packaging/audit_release.py'))['audit'](root,tool,manifest)
    assert errors, 'True manifest flags must not substitute for actual bundle contents'

def test_gate_distinguishes_supplier_and_reviewed_bundle_bytes(tmp_path):
    root,tool,manifest,payload=fixture(tmp_path)
    payload['ffmpeg']['sha256']=hashlib.sha256(b'unmodified supplier Mach-O').hexdigest()
    payload['ffprobe']['sha256']=hashlib.sha256(b'supplier probe').hexdigest()
    build=root/'build-manifest.json'
    build.write_text(json.dumps({'version':'0.4.9rc1','tools':{name:{'sha256':payload[name]['sha256']} for name in ('ffmpeg','ffprobe')}}))
    payload['bundle']['build_manifest_sha256']=digest(build)
    manifest.write_text(json.dumps(payload))
    audit=runpy.run_path(str(ROOT/'packaging/audit_release.py'))['audit']
    assert audit(root,tool,manifest)==[]
    tool.write_text(tool.read_text()+'# bytes changed after review\n')
    assert any('hash mismatch' in error for error in audit(root,tool,manifest))

def test_gate_requires_reviewed_bundle_hash(tmp_path):
    root,tool,manifest,payload=fixture(tmp_path)
    del payload['ffmpeg']['bundle_sha256']
    manifest.write_text(json.dumps(payload))
    errors=runpy.run_path(str(ROOT/'packaging/audit_release.py'))['audit'](root,tool,manifest)
    assert any('bundle hash' in error for error in errors)

def test_prepare_vendor_checks_hash_before_restoring_executable_bits(tmp_path):
    module=runpy.run_path(str(ROOT/'packaging/prepare_vendor.py'))
    for name in ('ffmpeg','ffprobe'):(tmp_path/name).write_text('#!/bin/sh\nprintf \"approved version\\nconfiguration: --disable-gpl\\n\"\n');(tmp_path/name).chmod(0o644)
    manifest=tmp_path/'binary-manifest.json'
    payload={'status':'APPROVED',**{name:{'sha256':digest(tmp_path/name)} for name in ('ffmpeg','ffprobe')}}
    manifest.write_text(json.dumps(payload))
    module['prepare'](tmp_path)
    assert (tmp_path/'ffmpeg').stat().st_mode & 0o100
    observed=runpy.run_path(str(ROOT/'packaging/build_manifest.py'))['manifest'](tmp_path,'approved')
    assert 'approved version' in observed['tools']['ffmpeg']['version_output']
    (tmp_path/'ffprobe').write_bytes(b'tampered');(tmp_path/'ffmpeg').chmod(0o644)
    with pytest.raises(ValueError,match='hash mismatch'):module['prepare'](tmp_path)
    assert not (tmp_path/'ffmpeg').stat().st_mode & 0o100
