"""EPERM cleanup regression; injected OS refusal, not native macOS QA."""
import errno
import os
import subprocess
import sys
from pathlib import Path
import pytest
from slide_core import pts
from slide_core.media import probe_source

@pytest.mark.skipif(os.name == 'nt', reason='POSIX process groups')
def test_group_permission_denied_still_reaps_owned_child(monkeypatch):
    proc=subprocess.Popen([sys.executable,'-c','import time; time.sleep(60)'],start_new_session=True)
    try:
        def denied(*args):
            raise PermissionError(errno.EPERM,'Operation not permitted')
        monkeypatch.setattr(pts.os,'killpg',denied)
        pts._kill(proc)
        assert proc.returncode is not None
        assert proc.poll() is not None
    finally:
        if proc.poll() is None:proc.kill()
        proc.wait(timeout=5)

@pytest.mark.skipif(os.name == 'nt', reason='POSIX process groups')
def test_natural_exit_needs_no_group_signal(monkeypatch):
    proc=subprocess.Popen([sys.executable,'-c','pass'],start_new_session=True)
    def unexpected(*args):raise AssertionError('Natural exit should be awaited')
    monkeypatch.setattr(pts.os,'killpg',unexpected)
    pts._kill(proc)
    assert proc.returncode == 0

@pytest.mark.skipif(os.name == 'nt', reason='POSIX process groups')
def test_group_disappeared_still_reaps_owned_child(monkeypatch):
    proc=subprocess.Popen([sys.executable,'-c','import time; time.sleep(60)'],start_new_session=True)
    try:
        def gone(*args):raise ProcessLookupError(errno.ESRCH,'No such process')
        monkeypatch.setattr(pts.os,'killpg',gone)
        pts._kill(proc)
        assert proc.returncode is not None
    finally:
        if proc.poll() is None:proc.kill()
        proc.wait(timeout=5)

def test_repeated_exact_frame_extraction_with_denied_group_signal(tmp_path,monkeypatch):
    video=tmp_path/'synthetic.mp4'
    subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y','-f','lavfi','-i','testsrc2=size=96x64:rate=4:duration=4','-c:v','mpeg4',str(video)],check=True)
    source=probe_source(video)
    samples,_=pts.sample_stream(source,tmp_path/'cache')
    def denied(*args):raise PermissionError(errno.EPERM,'Operation not permitted')
    monkeypatch.setattr(pts.os,'killpg',denied)
    for run in range(3):
        progress=[]
        frames=pts.extract_selected(source,samples,tmp_path/f'export{run}',progress=lambda *args:progress.append(args))
        assert len(frames)==len(samples)
        assert all(p.is_file() and p.stat().st_size for p in frames)
        assert progress[-1]==('extracting',len(samples),len(samples))
