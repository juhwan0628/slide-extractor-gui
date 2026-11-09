"""Export a committed CLI snapshot without GUI or working-tree data."""
import argparse
import ast
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

TOOL_VERSION = 2
SOURCE_REPOSITORY = "https://github.com/juhwan0628/slide-extractor-gui"

def _git(repo,*args):
 return subprocess.check_output(['git','-C',str(repo),*args])

def export_release(repo,commit,destination):
 repo=Path(repo);destination=Path(destination)
 if not re.fullmatch(r'[0-9a-f]{40}',commit):raise ValueError('Full immutable commit SHA required')
 if _git(repo,'status','--porcelain').strip():raise ValueError('Source working tree must be clean')
 if _git(repo,'rev-parse',commit+'^{commit}').decode().strip()!=commit:raise ValueError('Invalid commit')
 if destination.exists() or destination.is_symlink():raise FileExistsError(destination)
 entries={}
 for row in _git(repo,'ls-tree','-rz',commit).split(b'\0'):
  if not row:continue
  meta,path=row.split(b'\t',1);mode,kind,blob=meta.split()
  entries[path.decode()]=(mode,kind,blob.decode())
 def read(name):
  if name not in entries:raise ValueError('Required source missing: '+name)
  mode,kind,blob=entries[name]
  if mode!=b'100644' or kind!=b'blob':raise ValueError('Unsafe source mode: '+name)
  return _git(repo,'cat-file','blob',blob)
 selected=sorted(n for n in entries if (n.startswith(('slide_core/','slide_cli/')) and n.endswith('.py')))
 if 'slide_core/version.py' not in selected or 'slide_cli/cli.py' not in selected:raise ValueError('Incomplete CLI/core')
 files={n:read(n) for n in selected}
 for name in ('LICENSE','THIRD_PARTY_NOTICES.md'):files[name]=read(name)
 tree=ast.parse(files['slide_core/version.py'])
 versions=[ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(x,ast.Name) and x.id=='VERSION' for x in n.targets)]
 if len(versions)!=1 or not isinstance(versions[0],str):raise ValueError('Unambiguous VERSION required')
 version=versions[0]
 if not re.fullmatch(r'[0-9A-Za-z.+!-]+',version):raise ValueError('Invalid version')
 for name in ('tests/__init__.py','tests/cli_fixtures.py','tests/test_cli.py','tests/test_cli_batch.py','tests/test_cli_pipeline.py'):
  files[name]=read(name)
 templates={'build_release.py':'scripts/build_release.py','publish-cli.yml':'.github/workflows/publish-cli.yml','MANIFEST.in':'MANIFEST.in','gitattributes':'.gitattributes','README.md':'README.md','CHANGELOG.md':'CHANGELOG.md','pyproject.toml':'pyproject.toml','cli.md':'docs/cli.md',
            'requirements-test.lock':'requirements-test.lock','ci.yml':'.github/workflows/ci.yml',
            'verify_snapshot.py':'scripts/verify_snapshot.py','test_install.py':'tests/test_install.py'}
 for name,target in templates.items():
  files[target]=read('packaging/cli_release/'+name).replace(b'@VERSION@',version.encode())
 files['source-manifest.json']=(json.dumps(dict(schema_version=1,source_repository=SOURCE_REPOSITORY,
  source_commit=commit,package_version=version,export_tool_version=TOOL_VERSION,
  tracked_file_sha256={n:hashlib.sha256(data).hexdigest() for n,data in sorted(files.items())},
  source_file_sha256={n:hashlib.sha256(files[n]).hexdigest() for n in selected}),sort_keys=True,indent=2)+'\n').encode()
 destination.parent.mkdir(parents=True,exist_ok=True)
 stage=Path(tempfile.mkdtemp(prefix='.cli-export-',dir=destination.parent))
 try:
  for name,data in files.items():
   path=stage/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)
  if destination.exists() or destination.is_symlink():raise FileExistsError(destination)
  # Reserve the final name exclusively; never replace an existing directory.
  destination.mkdir()
  try:
   for path in stage.iterdir():shutil.move(str(path),str(destination/path.name))
  except BaseException:
   shutil.rmtree(destination);raise
 finally:shutil.rmtree(stage)
 return destination

def main():
 p=argparse.ArgumentParser(description=__doc__)
 p.add_argument('--repo',type=Path,default=Path(__file__).resolve().parents[1])
 p.add_argument('--commit',required=True);p.add_argument('--output',type=Path,required=True)
 a=p.parse_args();print(export_release(a.repo,a.commit,a.output))

if __name__=='__main__':main()
