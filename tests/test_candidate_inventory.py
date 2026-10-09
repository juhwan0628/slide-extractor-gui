import hashlib
import runpy
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def test_inventory_does_not_hash_license_directory_named_ffmpeg(tmp_path,monkeypatch):
    (tmp_path/'licenses'/'ffmpeg').mkdir(parents=True)
    (tmp_path/'tools').mkdir()
    for name in ('ffmpeg','ffprobe'):(tmp_path/'tools'/name).write_bytes(name.encode())
    (tmp_path/'build-manifest.json').write_text('{}')
    original=Path.rglob
    monkeypatch.setattr(Path,'rglob',lambda self,pattern:iter(sorted(original(self,pattern),key=lambda p:(p.is_file(),str(p)))))
    module=runpy.run_path(str(ROOT/'packaging/candidate_inventory.py'))
    result=module['inventory'](tmp_path,'test-version','')
    assert result['tools']['ffmpeg']['bundle_sha256']==hashlib.sha256(b'ffmpeg').hexdigest()
    assert result['candidate_version']=='test-version'
