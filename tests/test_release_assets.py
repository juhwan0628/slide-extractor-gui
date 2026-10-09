import hashlib,json,runpy
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[1]

def fixture(tmp_path):
    root=tmp_path/'inputs';root.mkdir()
    files={}
    for platform,name in [('macos-arm64','SlideExtractor-v0.4.9rc1-macOS-arm64-approved.dmg'),('windows-x64','SlideExtractor-v0.4.9rc1-Setup-Windows-x64.exe')]:
        p=root/name;p.write_bytes(platform.encode())
        files[platform]={'path':name,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
    approval={'status':'APPROVED','version':'0.4.9rc1','commit':'a'*40,'run_id':'123','assets':files}
    approval['audits']={platform:{'status':'PASSED','errors':[],'version':'0.4.9rc1','commit':'a'*40,'run_id':'123','installer_sha256':item['sha256'],'manifest_sha256':'c'*64} for platform,item in files.items()}
    return root,approval

def stage(root, approval, output):
    return runpy.run_path(str(ROOT/'packaging/release_assets.py'))['stage'](root,approval,output,version='0.4.9rc1',commit='a'*40,run_id='123')

def test_release_requires_both_reviewed_platforms(tmp_path):
    root,a=fixture(tmp_path);del a['assets']['windows-x64']
    with pytest.raises(ValueError):stage(root,a,tmp_path/'out')

def test_release_detects_changed_package(tmp_path):
    root,a=fixture(tmp_path);(root/a['assets']['windows-x64']['path']).write_bytes(b'changed')
    with pytest.raises(ValueError):stage(root,a,tmp_path/'out')

@pytest.mark.parametrize('field,value',[('status','NOT_APPROVED'),('version','0.4.8'),('commit','b'*40),('run_id','124')])
def test_release_rejects_wrong_identity(tmp_path,field,value):
    root,a=fixture(tmp_path);a[field]=value
    with pytest.raises(ValueError):stage(root,a,tmp_path/'out')

def test_release_rejects_path_escape(tmp_path):
    root,a=fixture(tmp_path);a['assets']['windows-x64']['path']='../external.exe'
    with pytest.raises(ValueError):stage(root,a,tmp_path/'out')

def test_reviewed_assets_get_shared_checksums(tmp_path):
    root,a=fixture(tmp_path);out=tmp_path/'out'
    result=stage(root,a,out)
    assert len(result)==2
    assert len((out/'SHA256SUMS.txt').read_text().splitlines())==2
    assert len(list(out.iterdir()))==3

def test_release_blocks_pending_audit_even_with_installer_approval(tmp_path):
    root,a=fixture(tmp_path)
    a['audits']={'macos-arm64':{'status':'BLOCKED','errors':['Qt replacement not verified']}}
    with pytest.raises(ValueError,match='audit'):stage(root,a,tmp_path/'out')

def test_release_requires_corresponding_source_hashes(tmp_path):
    mod=runpy.run_path(str(ROOT/'packaging/release_assets.py'))
    source=tmp_path/'source';source.mkdir();(source/'ffmpeg.tar.xz').write_bytes(b'changed')
    out=tmp_path/'out';out.mkdir()
    with pytest.raises(ValueError,match='source hash'):
        mod['stage_sources'](source,out,{'ffmpeg':{'url':'https://example.test/ffmpeg.tar.xz','sha256':'0'*64}})
