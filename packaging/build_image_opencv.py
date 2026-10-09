"""Build only the image functions the app uses, from exact upstream sources."""
import difflib,hashlib,json,os,shutil,subprocess,sys,tarfile,urllib.request
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def patch_image_only_source(source_root):
    """Patch only upstream packaging/type metadata for excluded modules."""
    changes = [
        ("setup.py", 'if os.name == "nt"\n            else []', 'if False  # image-only build has no videoio helper\n            else []'),
        ("opencv/modules/python/src2/typing_stubs_generation/api_refinement.py",
         "for_each_function_overload)",
         "for_each_function_overload, ScopeNotFoundError, SymbolNotFoundError)"),
        ("opencv/modules/python/src2/typing_stubs_generation/api_refinement.py",
         "    for symbol_name, refine_symbol in NODES_TO_REFINE.items():\n        refine_symbol(root, symbol_name)",
         "    for symbol_name, refine_symbol in NODES_TO_REFINE.items():\n"
         "        try:\n            find_function_node(root, symbol_name)\n"
         "        except (ScopeNotFoundError, SymbolNotFoundError):\n"
         "            continue  # API excluded from this partial module build\n"
         "        refine_symbol(root, symbol_name)"),
    ]
    originals = {}
    modified = {}
    for relative, old, new in changes:
        path = source_root / relative
        if relative not in originals:
            originals[relative] = path.read_text(encoding="utf-8")
            modified[relative] = originals[relative]
        if modified[relative].count(old) != 1:
            raise ValueError(f"Unexpected pinned OpenCV source: {relative}")
        modified[relative] = modified[relative].replace(old, new)
    patch = ""
    for relative, updated in modified.items():
        compile(updated, relative, "exec")
        patch += "".join(difflib.unified_diff(originals[relative].splitlines(True),
                         updated.splitlines(True), fromfile="a/"+relative, tofile="b/"+relative))
        (source_root / relative).write_text(updated, encoding="utf-8")
    return patch

if __name__=='__main__':
    config=json.loads((ROOT/'packaging/opencv-image-only.json').read_text())
    source=config['source'];archive=ROOT/'vendor/approved/sources'/source['url'].rsplit('/',1)[-1]
    archive.parent.mkdir(parents=True,exist_ok=True)
    if not archive.is_file() or hashlib.sha256(archive.read_bytes()).hexdigest()!=source['sha256']:
        urllib.request.urlretrieve(source['url'],archive)
    assert hashlib.sha256(archive.read_bytes()).hexdigest()==source['sha256'],'OpenCV source hash mismatch'
    source_dir=ROOT/'build/opencv-source'
    if source_dir.exists():shutil.rmtree(source_dir)
    source_dir.mkdir(parents=True)
    with tarfile.open(archive) as upstream:upstream.extractall(source_dir,filter='data')
    source_root=next(source_dir.iterdir())
    patch_path=archive.parent/'opencv-image-only.patch'
    patch_path.write_text(patch_image_only_source(source_root),encoding='utf-8')
    wheel_dir=ROOT/'build/opencv-wheel';wheel_dir.mkdir(parents=True,exist_ok=True)
    env={**os.environ,'ENABLE_HEADLESS':'1','CMAKE_ARGS':' '.join(config['cmake_args']),
         'CMAKE_BUILD_PARALLEL_LEVEL':str(os.cpu_count() or 2)}
    subprocess.run([sys.executable,'-m','pip','wheel','--no-deps','--wheel-dir',str(wheel_dir),str(source_root)],check=True,env=env)
    wheel=next(wheel_dir.glob('opencv_python_headless-*.whl'))
    subprocess.run([sys.executable,'-m','pip','install','--force-reinstall','--no-deps',str(wheel)],check=True)
    import cv2,runpy
    build=cv2.getBuildInformation()
    policy=runpy.run_path(str(ROOT/'packaging/native_codec_policy.py'))['validate_image_only_opencv']
    policy(Path(cv2.__file__).parent,build,has_video_capture=hasattr(cv2,'VideoCapture'))
    libs=Path(cv2.__file__).parent.parent/'opencv_python_headless.libs'
    if libs.exists():policy(libs,build,has_video_capture=False)
    assert all(hasattr(cv2,name) for name in ('cvtColor','resize','absdiff','integral','imread','imwrite'))
    print(build)
    (ROOT/'build/opencv-build.json').write_text(json.dumps({**config,'source_patch':'opencv-image-only.patch','source_patch_sha256':hashlib.sha256(patch_path.read_bytes()).hexdigest(),'wheel':wheel.name,'wheel_sha256':hashlib.sha256(wheel.read_bytes()).hexdigest(),'build_information':build,'image_only_verified':True},indent=2)+'\n')
