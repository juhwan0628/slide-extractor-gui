import importlib.util,json,subprocess
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[1]

def module():
 spec=importlib.util.spec_from_file_location('exporter',ROOT/'scripts/export_cli_release.py')
 mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);return mod

@pytest.fixture
def repo(tmp_path):
 p=tmp_path/'repo';p.mkdir()
 files={'slide_core/version.py':'VERSION = "0.5.0b2"\n','slide_core/__init__.py':'','slide_cli/__init__.py':'','slide_cli/cli.py':'# cli\n','LICENSE':'MIT\n','THIRD_PARTY_NOTICES.md':'Notices\n','docs/cli.md':'# Usage\n','gui/window.py':'PRIVATE GUI','secret.env':'secret','pyproject.toml':'not exported'}
 for name in ['pyproject.toml','README.md','cli.md','requirements-test.lock','ci.yml','verify_snapshot.py','test_install.py','CHANGELOG.md']:
  files['packaging/cli_release/'+name]=(ROOT/'packaging/cli_release'/name).read_text()
 for name in ['__init__.py','cli_fixtures.py','test_cli.py','test_cli_batch.py','test_cli_pipeline.py']:
  files['tests/'+name]=(ROOT/'tests'/name).read_text()
 for name,data in files.items():
  target=p/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_text(data)
 subprocess.run(['git','init',str(p)],check=True,capture_output=True)
 subprocess.run(['git','-C',str(p),'add','.'],check=True)
 subprocess.run(['git','-C',str(p),'-c','user.name=Test','-c','user.email=test@example.test','commit','-m','fixture'],check=True,capture_output=True)
 return p,subprocess.check_output(['git','-C',str(p),'rev-parse','HEAD'],text=True).strip()

def test_repeatable_allowlist_and_hashes(repo,tmp_path):
 import hashlib
 p,sha=repo
 module().export_release(p,sha,tmp_path/'a')
 module().export_release(p,sha,tmp_path/'b')
 a={str(f.relative_to(tmp_path/'a')):f.read_bytes() for f in (tmp_path/'a').rglob('*') if f.is_file()}
 b={str(f.relative_to(tmp_path/'b')):f.read_bytes() for f in (tmp_path/'b').rglob('*') if f.is_file()}
 assert a==b and 'gui/window.py' not in a and 'secret.env' not in a
 manifest=json.loads(a['source-manifest.json'])
 assert manifest['source_commit']==sha
 for name,h in manifest['tracked_file_sha256'].items():assert hashlib.sha256(a[name]).hexdigest()==h
 assert a['slide_cli/cli.py']==(p/'slide_cli/cli.py').read_bytes()
 assert 'gui' not in a['pyproject.toml'].decode()
 assert '0.5.0b2' in a['pyproject.toml'].decode()

def test_dirty_source_and_symbolic_ref_rejected(repo,tmp_path):
 p,sha=repo
 with pytest.raises(ValueError):module().export_release(p,'HEAD',tmp_path/'out')
 (p/'slide_cli/cli.py').write_text('changed')
 with pytest.raises(ValueError):module().export_release(p,sha,tmp_path/'out')
 assert not (tmp_path/'out').exists()

def test_existing_output_preserved(repo,tmp_path):
 p,sha=repo;out=tmp_path/'out';out.mkdir();(out/'keep').write_text('keep')
 with pytest.raises(FileExistsError):module().export_release(p,sha,out)
 assert (out/'keep').read_text()=='keep'

def test_snapshot_contains_independent_tests_ci_and_validator(repo,tmp_path):
 import sys
 p,sha=repo;out=tmp_path/'snapshot'
 module().export_release(p,sha,out)
 required=['tests/cli_fixtures.py','tests/test_cli.py','tests/test_cli_batch.py',
           'tests/test_cli_pipeline.py','tests/test_install.py','scripts/verify_snapshot.py',
           '.github/workflows/ci.yml','requirements-test.lock','CHANGELOG.md']
 assert all((out/name).is_file() for name in required)
 check=subprocess.run([sys.executable,str(out/'scripts/verify_snapshot.py')],capture_output=True,text=True)
 assert check.returncode==0,check.stderr
 (out/'slide_cli/cli.py').write_text('tampered')
 assert subprocess.run([sys.executable,str(out/'scripts/verify_snapshot.py')],capture_output=True).returncode!=0

@pytest.mark.parametrize('damage',['missing','extra','symlink'])
def test_validator_rejects_incomplete_or_unexpected_snapshot(repo,tmp_path,damage):
 import sys
 p,sha=repo;out=tmp_path/'snapshot'
 module().export_release(p,sha,out)
 target=out/'slide_cli/cli.py'
 if damage=='missing':target.unlink()
 elif damage=='extra':(out/'private.env').write_text('not allowed')
 else:
  target.unlink()
  try:target.symlink_to(p/'slide_cli/cli.py')
  except OSError:pytest.skip('Symlink privilege unavailable')
 result=subprocess.run([sys.executable,str(out/'scripts/verify_snapshot.py')],capture_output=True,text=True)
 assert result.returncode!=0
