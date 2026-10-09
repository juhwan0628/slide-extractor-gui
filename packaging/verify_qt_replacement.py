"""Modify QtCore's runtime version marker in an installed test copy only."""
import argparse,hashlib,json,sys
from pathlib import Path

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('root',type=Path);p.add_argument('report',type=Path);a=p.parse_args()
    source=json.loads((Path(__file__).parent/'native-sources.lock.json').read_text())['qt']['version']
    replacement=source.rsplit('.',1)[0]+'.9'
    if replacement==source:raise ValueError('Test marker must differ from supplied Qt version')
    needle=source.encode()+b'\0';marker=replacement.encode()+b'\0'
    assert len(needle)==len(marker)
    core=next(x for x in a.root.rglob('Qt6Core.dll' if sys.platform=='win32' else 'QtCore') if x.is_file() and not x.is_symlink())
    data=core.read_bytes();assert data.count(needle)==1,'QtCore version marker must be unique'
    changed=data.replace(needle,marker)
    core.chmod(core.stat().st_mode|0o200);core.write_bytes(changed)
    record={'method':'QtCore runtime version string mutation in installed test copy; not a rebuilt Qt library',
            'path':str(core.relative_to(a.root)),'original_sha256':hashlib.sha256(data).hexdigest(),
            'modified_sha256':hashlib.sha256(changed).hexdigest(),'expected_runtime_version':replacement}
    a.report.write_text(json.dumps(record,indent=2)+'\n')
    print(json.dumps(record))
