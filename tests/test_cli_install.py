"""Install the built wheel into a genuinely Qt-free isolated environment."""
import importlib.util
import json
import os
from pathlib import Path
import runpy
import shutil
import subprocess
import sys
import zipfile
import pytest
from tests.cli_fixtures import video

ROOT=Path(__file__).resolve().parents[1]

@pytest.fixture(scope='module')
def installed(tmp_path_factory):
    root=tmp_path_factory.mktemp('cli-installed')
    wheels=root/'wheels';wheels.mkdir()
    build=subprocess.run([sys.executable,'-m','pip','wheel','--no-deps','--no-build-isolation',
                          '--wheel-dir',str(wheels),str(ROOT)],capture_output=True,text=True,timeout=120)
    assert build.returncode==0,build.stdout+build.stderr
    wheel=next(wheels.glob('*.whl'))
    subprocess.run([sys.executable,'-m','venv',str(root/'venv')],check=True,timeout=30)
    bin_dir=root/'venv'/('Scripts' if os.name=='nt' else 'bin')
    python=bin_dir/('python.exe' if os.name=='nt' else 'python')
    install=subprocess.run([str(python),'-m','pip','install','--disable-pip-version-check',
                            '--constraint',str(ROOT/'packaging/requirements-linux-aarch64-validation.lock'),
                            str(wheel)],cwd=root,capture_output=True,text=True,timeout=180)
    assert install.returncode==0,install.stdout+install.stderr
    env=dict(os.environ)
    env.pop('PYTHONPATH',None);env.pop('SLIDE_NATIVE_KEYFRAME_HELPER',None)
    command=bin_dir/('slide-extractor.exe' if os.name=='nt' else 'slide-extractor')
    return root,wheel,python,command,env

def test_wheel_contains_only_product_packages_and_gui_extra(installed):
    _,wheel,_,_,_=installed
    with zipfile.ZipFile(wheel) as z:
        names=z.namelist()
        assert 'slide_core/pipeline.py' in names and 'slide_cli/batch.py' in names
        assert 'gui/window.py' in names and 'app.py' in names
        assert not any(n.startswith(('tests/','legacy_fps/','packaging/')) for n in names)
        metadata=z.read(next(n for n in names if n.endswith('.dist-info/METADATA'))).decode()
        assert 'Provides-Extra: gui' in metadata
        qt=[line for line in metadata.splitlines() if line.startswith('Requires-Dist: PySide6')]
        assert qt and all('extra == "gui"' in line for line in qt)

def test_installed_entry_points_and_no_qt(installed):
    root,_,python,command,env=installed
    check=subprocess.run([str(python),'-c',
        "import importlib.util; assert importlib.util.find_spec('PySide6') is None; assert importlib.util.find_spec('shiboken6') is None"],
        cwd=root,env=env,capture_output=True,text=True)
    assert check.returncode==0,check.stderr
    for args in ([str(command),'--help'],[str(command),'--version'],[str(python),'-m','slide_cli','--help']):
        result=subprocess.run(args,cwd=root,env=env,capture_output=True,text=True,timeout=20)
        assert result.returncode==0,result.stderr
    assert subprocess.run([str(python),'-m','pip','check'],cwd=root,env=env,capture_output=True).returncode==0

def test_installed_cpu_fallback_without_qpdf_produces_valid_pair(installed):
    root,_,python,command,env=installed
    source=video(root/'lecture.mkv',codec='libx264')
    if os.name != 'nt':
        tools=root/'tools';tools.mkdir(exist_ok=True)
        for name in ('ffmpeg','ffprobe'):
            (tools/name).symlink_to(shutil.which(name))
        env={**env,'PATH':str(tools)}
    output=root/'installed.pdf'
    result=subprocess.run([str(command),str(source.path),'-o',str(output),
                           '--json','detailed','--result-json','--quiet'],
                          cwd=root,env=env,capture_output=True,text=True,timeout=60)
    assert result.returncode==0,result.stderr
    summary=json.loads(result.stdout)
    assert summary['decoder_backend']=='cpu-keyframes'
    assert summary['selection_policy']=='all'
    check=subprocess.run([str(python),'-c',
        "from pathlib import Path;from pypdf import PdfReader;from slide_core.keyframe_json import loads;p=Path('installed.pdf');r=PdfReader(p);loads(p.with_suffix('.json').read_bytes(),pdf_bytes=p.read_bytes(),pdf_page_count=len(r.pages));assert len(r.pages)>0"],
        cwd=root,env=env,capture_output=True,text=True,timeout=20)
    assert check.returncode==0,check.stderr
    assert not list(root.glob('.slide-cli-*'))

def test_installed_missing_ffmpeg_reports_error(installed):
    root,_,_,command,env=installed
    source=video(root/'no-tools.mkv')
    empty=root/'empty';empty.mkdir()
    result=subprocess.run([str(command),str(source.path),'--result-json'],cwd=root,
                          env={**env,'PATH':str(empty)},capture_output=True,text=True,timeout=20)
    assert result.returncode==1
    summary=json.loads(result.stdout)
    assert summary['status']=='error' and not summary['published']
    assert 'FFmpeg' in summary['message'] or 'ffprobe' in summary['message']

def test_source_zip_includes_cli_and_install_metadata(tmp_path):
    module=runpy.run_path(str(ROOT/'packaging/build_source_zip.py'))
    path=tmp_path/'source.zip';module['build'](path)
    with zipfile.ZipFile(path) as z:
        for name in ['pyproject.toml','slide_cli/cli.py','slide_cli/batch.py','slide_cli/outcomes.py','docs/cli.md']:
            assert 'SlideExtractor/'+name in z.namelist()
