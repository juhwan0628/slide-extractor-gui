"""Stage the exact reviewed two-platform installers, without publishing them."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil


def stage(root, approval, output, *, version, commit, run_id):
    root, output = Path(root).resolve(), Path(output)
    for field,expected in {'status':'APPROVED','version':version,'commit':commit,'run_id':str(run_id)}.items():
        if approval.get(field)!=expected:raise ValueError('Release approval mismatch: '+field)
    assets=approval.get('assets',{})
    if set(assets)!={'macos-arm64','windows-x64'}:raise ValueError('Both platform installers must be reviewed')
    expected={'macos-arm64':f'SlideExtractor-v{version}-macOS-arm64-approved.dmg',
              'windows-x64':f'SlideExtractor-v{version}-Setup-Windows-x64.exe'}
    checked=[]
    for platform,item in sorted(assets.items()):
        rel=Path(item['path'])
        if rel.is_absolute() or '..' in rel.parts or '\\' in str(rel) or ':' in str(rel):raise ValueError('Unsafe asset path')
        path=root/rel
        if path.is_symlink() or not path.is_file() or not path.resolve().is_relative_to(root):raise ValueError('Missing/unsafe asset')
        if path.name!=expected[platform]:raise ValueError('Unexpected installer filename')
        digest=hashlib.sha256(path.read_bytes()).hexdigest()
        if digest!=item.get('sha256'):raise ValueError('Reviewed installer hash mismatch')
        checked.append((path,digest))
    if output.exists() and any(output.iterdir()):raise ValueError('Release staging folder must be empty')
    output.mkdir(parents=True,exist_ok=True)
    for path,digest in checked:
        destination=output/path.name
        shutil.copy2(path,destination)
        if hashlib.sha256(destination.read_bytes()).hexdigest()!=digest:
            raise ValueError('Installer changed during staging')
    (output/'SHA256SUMS.txt').write_text(''.join(f'{digest}  {path.name}\n' for path,digest in checked),encoding='utf-8')
    return [output/path.name for path,_ in checked]

if __name__=='__main__':
    p=argparse.ArgumentParser()
    for name in ('root','approval','output','version','commit','run-id'):p.add_argument('--'+name,required=True)
    a=p.parse_args()
    stage(a.root,json.loads(Path(a.approval).read_text()),a.output,version=a.version,commit=a.commit,run_id=a.run_id)
