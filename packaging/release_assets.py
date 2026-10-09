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
        audit=approval.get('audits',{}).get(platform,{})
        for field,value in {'status':'PASSED','errors':[],'version':version,'commit':commit,'run_id':str(run_id),'installer_sha256':digest}.items():
            if audit.get(field)!=value:raise ValueError('Reviewed audit missing/mismatch: '+platform+'/'+field)
        if not audit.get('manifest_sha256'):raise ValueError('Reviewed audit manifest hash missing')
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

def stage_sources(root,output,sources):
    root,output=Path(root).resolve(),Path(output)
    checked=[]
    for name,item in sorted(sources.items()):
        filename=item['url'].rsplit('/',1)[-1]
        if not filename or Path(filename).name!=filename:raise ValueError('Unsafe source filename')
        path=root/filename
        if path.is_symlink() or not path.is_file() or not path.resolve().is_relative_to(root):raise ValueError('Corresponding source missing')
        if hashlib.sha256(path.read_bytes()).hexdigest()!=item['sha256']:raise ValueError('Corresponding source hash mismatch')
        if (output/filename).exists():raise ValueError('Duplicate source asset')
        checked.append((path,item['sha256']))
    for path,digest in checked:
        shutil.copy2(path,output/path.name)
        if hashlib.sha256((output/path.name).read_bytes()).hexdigest()!=digest:raise ValueError('Corresponding source hash changed during staging')
    with (output/'SHA256SUMS.txt').open('a',encoding='utf-8') as stream:
        stream.writelines(f'{digest}  {path.name}\n' for path,digest in checked)
    return [output/path.name for path,_ in checked]

if __name__=='__main__':
    p=argparse.ArgumentParser()
    for name in ('root','approval','output','version','commit','run-id','sources'):p.add_argument('--'+name,required=True)
    a=p.parse_args()
    stage(a.root,json.loads(Path(a.approval).read_text()),a.output,version=a.version,commit=a.commit,run_id=a.run_id)

    stage_sources(a.sources,a.output,json.loads((Path(__file__).parent/'native-sources.lock.json').read_text()))
