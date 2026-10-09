"""Record observed build inputs; this file never approves a public release."""
import argparse
import hashlib
import importlib.metadata
import json
import os
import platform
import runpy
import subprocess
import sys
from pathlib import Path

def manifest(tools, mode):
    version=runpy.run_path(str(Path(__file__).resolve().parents[1]/'slide_core/version.py'))['VERSION']
    result={'version':version,'mode':mode,'public_release_approved':False,
            'python':sys.version,'platform':platform.platform(),'architecture':platform.machine(),
            'packages':dict(sorted((d.metadata['Name'],d.version) for d in importlib.metadata.distributions())),
            'tools':{},'provenance':{key:os.environ[key] for key in ('GITHUB_RUN_ID','GITHUB_RUN_ATTEMPT','GITHUB_SHA') if key in os.environ}}
    extension='.exe' if sys.platform=='win32' else ''
    for name in ('ffmpeg','ffprobe'):
        path=(Path(tools)/(name+extension)).resolve()
        result['tools'][name]={'path':str(path),
            'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
            'version_output':subprocess.run([str(path),'-version'],capture_output=True,text=True,
                                           check=True,timeout=20).stdout}
    return result

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--tools',type=Path,required=True)
    parser.add_argument('--mode',choices=('personal','approved'),required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(manifest(args.tools,args.mode),indent=2)+'\n')
