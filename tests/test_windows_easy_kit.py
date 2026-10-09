from pathlib import Path
import hashlib,runpy,zipfile
import pytest
ROOT=Path(__file__).resolve().parents[1]
def media():return runpy.run_path(str(ROOT/'packaging/windows_media.py'))
def fixture(tmp_path,extra=None):
    p=tmp_path/'fixture.zip'
    with zipfile.ZipFile(p,'w') as z:
        for name in ('ffmpeg.exe','ffprobe.exe'):z.writestr('ffmpeg-fixture/bin/'+name,b'MZ fixture '+name.encode())
        z.writestr('ffmpeg-fixture/LICENSE','license fixture')
        if extra:z.writestr(extra,b'unsafe')
    return p,hashlib.sha256(p.read_bytes()).hexdigest()
def test_download_creates_tools_without_user_folders_and_reuses_verified_cache(tmp_path):
    p,sha=fixture(tmp_path);target=tmp_path/'new vendor'
    tools=media()['prepare'](target,url=p.as_uri(),expected_sha256=sha)
    assert tools['ffmpeg'].read_bytes().startswith(b'MZ')
    assert (target/'LICENSE').read_text()=='license fixture'
    p.unlink()
    assert media()['prepare'](target,url=p.as_uri(),expected_sha256=sha)['ffprobe'].is_file()
def test_download_rejects_wrong_hash_before_extracting(tmp_path):
    p,_=fixture(tmp_path);target=tmp_path/'new vendor'
    with pytest.raises(ValueError,match='SHA'):media()['prepare'](target,url=p.as_uri(),expected_sha256='0'*64)
    assert not (target/'ffmpeg.exe').exists()
def test_download_rejects_archive_path_escape(tmp_path):
    p,sha=fixture(tmp_path,'../escaped.exe')
    with pytest.raises(ValueError,match='Unsafe'):media()['prepare'](tmp_path/'vendor',url=p.as_uri(),expected_sha256=sha)
    assert not (tmp_path/'escaped.exe').exists()
def test_easy_kit_has_only_launcher_guide_and_internal_source(tmp_path):
    output=tmp_path/'kit.zip';runpy.run_path(str(ROOT/'packaging/build_windows_kit.py'))['build'](output)
    with zipfile.ZipFile(output) as z:
        names=z.namelist();prefix='SlideExtractor-Windows/'
        top={n[len(prefix):].split('/')[0] for n in names}
        assert top=={'BUILD-WINDOWS.bat','사용안내.txt','_app'}
        assert prefix+'_app/packaging/windows_media.py' in names
        assert not any('macos' in n.lower() or 'INSTALL-MAC' in n for n in names)
        assert 'windows_media' not in z.read(prefix+'BUILD-WINDOWS.bat').decode('ascii')
