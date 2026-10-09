"""Release correctness: real tagged media and precise cancellation boundaries."""
import errno
import os
from pathlib import Path
import subprocess
import numpy as np
from PIL import Image
import pytest
from slide_core import analysis, export, media, pdf_only_export, pts
from slide_core.config import AnalysisSettings
from slide_core.models import CancelToken, CancelledError
from tests.test_sampling import make_video


def test_tagged_media_first_frame_and_export_use_probe_transform(tmp_path):
    from gui.preparation import prepare_first_frame
    path=tmp_path/'tagged.mkv'
    subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y','-f','lavfi',
        '-i','color=c=0xC03020:size=80x48:rate=4:duration=1','-c:v','ffv1',
        '-pix_fmt','yuv444p','-colorspace','bt709','-color_range','pc',
        '-color_trc','bt709',str(path)],check=True,capture_output=True,timeout=20)
    source=media.probe_source(path)
    meta=dict(source.metadata)
    expected=subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-noautorotate',
        '-i',str(path),'-vf',meta['display_filter'],'-frames:v','1','-pix_fmt','rgb24',
        '-f','rawvideo','pipe:1'],check=True,capture_output=True,timeout=20).stdout
    prepared,w,h,*_=prepare_first_frame(source)
    assert (w,h)==(80,48)
    assert prepared==expected
    frames=pts.extract_selected(source,[meta['origin_pts']],tmp_path/'frames')
    with Image.open(frames[0]) as image: assert image.convert('RGB').tobytes()==expected
    samples,_=pts.sample_stream(source,tmp_path/'cache')
    with Image.open(samples[0].cache_path) as image:
        error=np.abs(np.asarray(image.convert('RGB')).astype(int)-np.frombuffer(expected,np.uint8).reshape(48,80,3))
        assert error.mean()<3


def test_reanalysis_checks_cancel_before_next_cached_image(tmp_path,monkeypatch):
    source=make_video(tmp_path/'video.mp4',duration=4,fps=4)
    settings=AnalysisSettings(roi_mode='full')
    previous,_=analysis.analyze_project(source,settings,tmp_path/'cache')
    token=CancelToken();calls=[];read=analysis._read_cache
    def cancel_after_first(sample):
        calls.append(sample.sample_id)
        image=read(sample);token.cancel();return image
    monkeypatch.setattr(analysis,'_read_cache',cancel_after_first)
    with pytest.raises(CancelledError):
        analysis.analyze_project(source,settings,tmp_path/'cache',previous=previous,cancel_token=token)
    assert len(calls)==1
    assert all(Path(s.cache_path).is_file() for s in previous.samples)


def test_source_preparation_passes_cancel_to_probe(tmp_path,monkeypatch):
    from gui.window import Window
    token=CancelToken();seen=[]
    def probe(path,*,cancel_token=None):
        seen.append(cancel_token)
        token.cancel();cancel_token.raise_if_cancelled()
    monkeypatch.setattr('gui.window.probe_source',probe)
    with pytest.raises(CancelledError):Window._prepare_source(tmp_path/'video.mp4',cancel_token=token)
    assert seen==[token]


def test_pdf_only_supports_windows_directory_handle_rejection(tmp_path,monkeypatch):
    source=make_video(tmp_path/'video.mp4',duration=2,fps=4)
    project,_=analysis.analyze_project(source,AnalysisSettings(roi_mode='full'),tmp_path/'cache')
    destination=tmp_path/'slides.pdf';original=os.open
    def open_without_directory_handles(path,flags,*args,**kwargs):
        if isinstance(path,(str,os.PathLike)) and Path(path).is_dir() and flags==os.O_RDONLY:
            exc=OSError(errno.EACCES,'Windows directory handle unavailable');exc.winerror=5;raise exc
        return original(path,flags,*args,**kwargs)
    monkeypatch.setattr(os,'open',open_without_directory_handles)
    assert pdf_only_export.export_pdf_only(project,destination)==(destination,)
    assert destination.is_file()


def test_directory_sync_real_permission_failure_is_not_silenced(tmp_path,monkeypatch):
    source=tmp_path/'source';source.write_bytes(b'source')
    tx=export.ExportTransaction(source,export.snapshot_export(source,tmp_path/'slides.pdf'))
    def denied(*args,**kwargs):raise OSError(errno.EACCES,'ordinary permission denial')
    monkeypatch.setattr(os,'open',denied)
    with pytest.raises(OSError) as result:tx._sync_dir(tmp_path)
    assert result.value.errno==errno.EACCES


def test_first_frame_cancel_reaps_stalled_decoder(tmp_path,monkeypatch):
    import sys,time,threading
    from gui import preparation
    source=make_video(tmp_path/'video.mp4',duration=1,fps=4)
    marker=tmp_path/'started'
    decoder=tmp_path/'fake-ffmpeg'
    decoder.write_text('#!'+sys.executable+'\nimport time\nfrom pathlib import Path\nPath('+repr(str(marker))+').write_text("ready")\ntime.sleep(5)\n')
    decoder.chmod(0o755)
    monkeypatch.setattr(preparation,'executable',lambda name:str(decoder))
    token=CancelToken()
    def cancel_when_started():
        until=time.monotonic()+3
        while not marker.exists() and time.monotonic()<until:time.sleep(.01)
        token.cancel()
    thread=threading.Thread(target=cancel_when_started);thread.start();started=time.monotonic()
    try:
        with pytest.raises((CancelledError,media.MediaError)) as result:
            preparation.prepare_first_frame(source,cancel_token=token)
        assert result.value.code.lower()=='cancelled'
        assert time.monotonic()-started<2, 'Cancellation waited for stalled FFmpeg to finish'
    finally:thread.join(timeout=4)
