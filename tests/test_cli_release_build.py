"""Release validation must reject stale contexts and altered source artifacts."""
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import tarfile
import pytest
ROOT=Path(__file__).resolve().parents[1]

def builder(monkeypatch):
 monkeypatch.syspath_prepend(str(ROOT/'packaging/cli_release'))
 spec=importlib.util.spec_from_file_location('release_builder',ROOT/'packaging/cli_release/build_release.py')
 mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);return mod

def test_sdist_hash_validation(monkeypatch,tmp_path):
 mod=builder(monkeypatch)
 root=tmp_path/'source';root.mkdir()
 data=b'print("source")\n'
 manifest={'tracked_file_sha256':{'slide_cli/cli.py':hashlib.sha256(data).hexdigest()}}
 (root/'source-manifest.json').write_text(json.dumps(manifest))
 def archive(name,payload):
  out=tmp_path/name
  with tarfile.open(out,'w:gz') as t:
   for p,b in {'slide_cli/cli.py':payload,'source-manifest.json':(root/'source-manifest.json').read_bytes()}.items():
    m=tarfile.TarInfo('package/'+p);m.size=len(b);t.addfile(m,io.BytesIO(b))
  return out
 mod.validate_sdist(archive('good.tar.gz',data),root)
 with pytest.raises(ValueError):mod.validate_sdist(archive('bad.tar.gz',b'changed'),root)

def test_publication_requires_exact_repo_branch_and_main(monkeypatch,tmp_path):
 mod=builder(monkeypatch)
 monkeypatch.setenv('GITHUB_REPOSITORY','other/repo')
 with pytest.raises(ValueError):mod.publication_context(tmp_path,'0.5.0b2')
 monkeypatch.setenv('GITHUB_REPOSITORY','juhwan0628/slide-extractor')
 monkeypatch.setenv('GITHUB_REF_NAME','main')
 with pytest.raises(ValueError):mod.publication_context(tmp_path,'0.5.0b2')
