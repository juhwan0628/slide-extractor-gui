"""Produce a small user-run source evaluation ZIP, never a native installer."""
from __future__ import annotations
import hashlib,zipfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
BASE=('app.py','requirements.txt','README.md',
      'BUILD-WINDOWS.bat','INSTALL-WINDOWS.md','packaging/build_windows_personal.py','packaging/windows_media.py','packaging/build_windows_kit.py',
      'scripts/validate-windows-portable.bat',
      'LICENSE_AUDIT.md','THIRD_PARTY_NOTICES.md',
      'packaging/BUILD_AND_TEST.md','packaging/QA_STATUS.md',
      'scripts/run-macos.command','scripts/run-windows.bat',
      'scripts/build-macos-personal.command','packaging/SlideExtractor-personal.spec',
      'packaging/desktop_entry.py','INSTALL-MAC.md',
      'packaging/SlideExtractor.spec','packaging/audit_release.py',
      'packaging/binary-manifest.example.json','packaging/build-macos-dmg.sh','packaging/windows.iss',
      'packaging/build_manifest.py','packaging/prepare_vendor.py','packaging/build_source_zip.py',
      'packaging/requirements-macos-arm64.lock','packaging/requirements-windows-x64.lock',
      'packaging/requirements-linux-aarch64-validation.lock')

def build(output:Path, *, include_tests=False):
    files=[ROOT/name for name in BASE]
    for folder in ('gui','slide_core'):
        files.extend(sorted((ROOT/folder).glob('*.py')))
    for path in files:
        if not path.is_file() or path.is_symlink():
            raise ValueError(f'Unsafe or missing evaluated source: {path}')
    if include_tests:
        files.extend(sorted((ROOT/'tests').glob('*.py')))
        files.extend(ROOT/name for name in ('requirements-dev.txt','.github/workflows/native-build-template.yml','scripts/benchmark-analysis.py','scripts/run-macos-benchmark.command'))
    output=Path(output);output.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(output,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for path in files:
            rel=path.relative_to(ROOT).as_posix()
            dest='SlideExtractor/'+rel
            metadata=zipfile.ZipInfo(dest,date_time=(2026,10,9,0,0,0))
            metadata.compress_type=zipfile.ZIP_DEFLATED
            metadata.external_attr=(0o755 if rel.endswith(('.command','.sh')) else 0o644)<<16
            z.writestr(metadata,path.read_bytes(),compress_type=zipfile.ZIP_DEFLATED,compresslevel=9)
    with zipfile.ZipFile(output) as z:
        for info in z.infolist():
            if info.filename.startswith('/') or '..' in Path(info.filename).parts:
                raise ValueError('Archive path traversal')
            if not z.testzip() is None:raise ValueError('Corrupt ZIP')
    digest=hashlib.sha256(output.read_bytes()).hexdigest()
    print(f'{output}: {len(files)} files, {output.stat().st_size} bytes, SHA256={digest}')
    return digest

if __name__=='__main__':
    import sys
    build(Path(sys.argv[1]),include_tests='--include-tests' in sys.argv[2:])
