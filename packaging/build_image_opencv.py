"""Build only the image functions the app uses, from exact upstream sources."""
import hashlib,json,os,subprocess,sys,urllib.request
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
if __name__=='__main__':
    config=json.loads((ROOT/'packaging/opencv-image-only.json').read_text())
    source=config['source'];archive=ROOT/'vendor/approved/sources'/source['url'].rsplit('/',1)[-1]
    archive.parent.mkdir(parents=True,exist_ok=True)
    if not archive.is_file() or hashlib.sha256(archive.read_bytes()).hexdigest()!=source['sha256']:
        urllib.request.urlretrieve(source['url'],archive)
    assert hashlib.sha256(archive.read_bytes()).hexdigest()==source['sha256'],'OpenCV source hash mismatch'
    wheel_dir=ROOT/'build/opencv-wheel';wheel_dir.mkdir(parents=True,exist_ok=True)
    env={**os.environ,'ENABLE_HEADLESS':'1','CMAKE_ARGS':' '.join(config['cmake_args']),
         'CMAKE_BUILD_PARALLEL_LEVEL':str(os.cpu_count() or 2)}
    subprocess.run([sys.executable,'-m','pip','wheel','--no-deps','--wheel-dir',str(wheel_dir),str(archive)],check=True,env=env)
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
    (ROOT/'build/opencv-build.json').write_text(json.dumps({**config,'wheel':wheel.name,'wheel_sha256':hashlib.sha256(wheel.read_bytes()).hexdigest(),'build_information':build,'image_only_verified':True},indent=2)+'\n')
