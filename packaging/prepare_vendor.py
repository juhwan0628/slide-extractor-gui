"""Verify immutable supplier inputs before restoring artifact execute bits."""
import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

def prepare(root, *, candidate=False):
    root=Path(root)
    data=json.loads((root/'binary-manifest.json').read_text())
    if data.get('status') not in ({'APPROVED','VERIFIED_INPUTS'} if candidate else {'APPROVED'}):
        raise ValueError('Supplier input manifest not approved')
    extension='.exe' if sys.platform=='win32' else ''
    tools=[]
    for name in ('ffmpeg','ffprobe'):
        tool=root/(name+extension)
        if tool.is_symlink() or not tool.is_file():
            raise ValueError(f'Missing regular supplier {name}')
        digest=hashlib.sha256(tool.read_bytes()).hexdigest()
        if digest != data.get(name,{}).get('sha256'):
            raise ValueError(f'{name} supplier hash mismatch')
        tools.append(tool)
    if os.name!='nt':
        for tool in tools:tool.chmod(tool.stat().st_mode | 0o111)
    return tools

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('root',type=Path)
    parser.add_argument('--candidate',action='store_true')
    args=parser.parse_args()
    prepare(args.root,candidate=args.candidate)
