"""Run the frozen FPS baseline in a separate interpreter and source tree."""
import argparse,json,os,subprocess,sys,tarfile,tempfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
def run(args):
 lock=json.loads((Path(__file__).with_name('baseline.json')).read_text())
 commit=lock['commit']
 if len(commit)!=40 or any(c not in '0123456789abcdef' for c in commit):raise ValueError('Invalid baseline commit')
 subprocess.run(['git','cat-file','-e',commit+'^{commit}'],cwd=ROOT,check=True)
 with tempfile.TemporaryDirectory(prefix='slide-fps-baseline-') as name:
  work=Path(name);archive=work/'baseline.tar'
  with archive.open('wb') as stream:
   subprocess.run(['git','archive','--format=tar',commit],cwd=ROOT,stdout=stream,check=True)
  source=work/'source';source.mkdir()
  with tarfile.open(archive) as tar:tar.extractall(source,filter='data')
  env={**os.environ,'PYTHONPATH':str(source),'QT_QPA_PLATFORM':'offscreen'}
  print('Isolated FPS baseline commit:',commit,flush=True)
  return subprocess.run([sys.executable,'-m','pytest',*(args or ['-q'])],cwd=source,env=env).returncode

if __name__=='__main__':raise SystemExit(run(sys.argv[1:]))
