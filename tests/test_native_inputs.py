import hashlib
import io
import json
import runpy
import tarfile
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[1]

def module():return runpy.run_path(str(ROOT/'packaging/native_inputs.py'))

def test_download_rejects_changed_source_without_retaining_it(tmp_path):
    src=tmp_path/'upstream.tar.xz';src.write_bytes(b'changed')
    dest=tmp_path/'saved.tar.xz'
    with pytest.raises(ValueError,match='hash mismatch'):
        module()['download_verified'](src.as_uri(),'0'*64,dest)
    assert not dest.exists()

@pytest.mark.parametrize('configuration',['--enable-gpl','--enable-nonfree','--enable-version3','--enable-libx264'])
def test_supplier_rejects_restricted_or_external_configuration(configuration):
    with pytest.raises(ValueError):module()['validate_configuration']('configuration: --disable-autodetect '+configuration)

def test_supplier_requires_known_minimal_configuration():
    with pytest.raises(ValueError):module()['validate_configuration']('configuration: --enable-static')
    module()['validate_configuration']('configuration: --disable-autodetect --disable-gpl --disable-nonfree --disable-version3 --enable-static --disable-shared')

def test_license_extraction_preserves_original_and_ignores_escaping_members(tmp_path):
    archive=tmp_path/'source.tar.xz'
    with tarfile.open(archive,'w:xz') as stream:
        for name in ('source/LICENSES/LGPL-3.0-only.txt','../../COPYING'):
            info=tarfile.TarInfo(name);info.size=7;stream.addfile(info,io.BytesIO(b'license'))
    with pytest.raises(ValueError,match='unsafe'):
        module()['source_licenses'](archive,tmp_path/'licenses','Qt')
    assert not (tmp_path.parent/'COPYING').exists()

def test_input_manifest_never_claims_release_approval(tmp_path):
    for name in ('ffmpeg','ffprobe'):(tmp_path/name).write_bytes(name.encode())
    source=tmp_path/'ffmpeg.tar.xz';source.write_bytes(b'source')
    result=module()['input_manifest'](tmp_path,{'ffmpeg':{'version':'8.1.2','url':'https://ffmpeg.org/source','sha256':hashlib.sha256(b'source').hexdigest()}},'configuration: --disable-autodetect --disable-gpl --disable-nonfree --disable-version3 --enable-static --disable-shared',extension='')
    assert result['status']=='VERIFIED_INPUTS'
    assert result['public_release_approved'] is False
    assert 'bundle' not in result
    assert result['ffprobe']['sha256']==hashlib.sha256(b'ffprobe').hexdigest()

def test_verified_inputs_are_only_accepted_for_candidate_builds(tmp_path):
    prepare=runpy.run_path(str(ROOT/'packaging/prepare_vendor.py'))['prepare']
    for name in ('ffmpeg','ffprobe'):(tmp_path/name).write_bytes(name.encode())
    data={'status':'VERIFIED_INPUTS',**{name:{'sha256':hashlib.sha256(name.encode()).hexdigest()} for name in ('ffmpeg','ffprobe')}}
    (tmp_path/'binary-manifest.json').write_text(json.dumps(data))
    with pytest.raises(ValueError,match='not approved'):prepare(tmp_path)
    assert len(prepare(tmp_path,candidate=True))==2

def test_spdx_license_directory_copies_original_lgpl_text(tmp_path):
    archive=tmp_path/'qt-source.tar.xz'
    text=b'GNU LESSER GENERAL PUBLIC LICENSE Version 3'
    with tarfile.open(archive,'w:xz') as stream:
        info=tarfile.TarInfo('qtbase/LICENSES/LGPL-3.0-only.txt');info.size=len(text)
        stream.addfile(info,io.BytesIO(text))
    copied=module()['source_licenses'](archive,tmp_path/'licenses','qt')
    assert len(copied)==1
    assert copied[0].read_bytes()==text
