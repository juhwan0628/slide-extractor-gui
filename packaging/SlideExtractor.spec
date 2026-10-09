# Shared onedir recipe. Public builds require separately audited vendor inputs.
import os, sys, runpy
from pathlib import Path

root = Path(SPECPATH).resolve().parent
version = runpy.run_path(str(root/'slide_core/version.py'))
mode = os.environ.get('SLIDE_BUILD_MODE', 'approved')
if mode not in ('approved', 'personal'):
    raise RuntimeError('Unknown native build mode')
if sys.platform not in ('win32', 'darwin'):
    raise RuntimeError('Native release builds require Windows x64 or macOS arm64')
vendor = Path(os.environ.get('PERSONAL_FFMPEG_DIR' if mode=='personal' else 'APPROVED_FFMPEG_DIR',
                             str(root/'vendor/approved'))).resolve()
extension = '.exe' if sys.platform=='win32' else ''
binaries = [(str(vendor/(name+extension)), 'tools') for name in ('ffmpeg', 'ffprobe')]
if not all(Path(path).is_file() for path, _ in binaries):
    raise RuntimeError(f'Missing {mode} FFmpeg inputs: {vendor}')
datas = [(str(root/name), '.') for name in ('THIRD_PARTY_NOTICES.md', 'LICENSE_AUDIT.md')]
# Required approved distribution materials; personal builds have a different contract.
for name in ('licenses', 'SBOM.json', 'SOURCE_AND_REPLACEMENT.md'):
    item=vendor/name
    if mode=='approved' and not item.exists():
        raise RuntimeError(f'Missing approved distribution material: {name}')
    if item.exists():
        datas.append((str(item), name if item.is_dir() else '.'))
build_manifest=Path(os.environ.get('SLIDE_BUILD_MANIFEST',
                                  str(root/'build'/('personal' if mode=='personal' else '')/'build-manifest.json')))
if mode=='approved' and not build_manifest.is_file():
    raise RuntimeError('Missing observed build manifest')
if build_manifest.is_file():
    datas.append((str(build_manifest), '.'))
a = Analysis([str(root/'packaging/desktop_entry.py')], pathex=[str(root)],
             binaries=binaries, datas=datas, hiddenimports=[], hookspath=[],
             runtime_hooks=[], excludes=['fitz','pymupdf','pytest','scipy','skimage'],
             noarchive=False)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name='SlideExtractor',
          debug=False, strip=False, upx=False, console=False, argv_emulation=False,
          target_arch='arm64' if sys.platform=='darwin' else None,
          codesign_identity=os.environ.get('SLIDE_CODESIGN_IDENTITY'), entitlements_file=None)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name='SlideExtractor')
if sys.platform=='darwin':
    app = BUNDLE(coll, name='SlideExtractor.app', bundle_identifier='ing.juhwan.slideextractor',
                 version=version['BUNDLE_VERSION'],
                 info_plist={'NSHighResolutionCapable':True,
                             'CFBundleShortVersionString':version['BUNDLE_VERSION'],
                             'CFBundleVersion':version['BUNDLE_VERSION'],
                             'NSPrincipalClass':'NSApplication'})
