"""Real FFmpeg bucket/PTS tests, never fixtures from private lecture media."""
from fractions import Fraction
from pathlib import Path
import subprocess
import shutil
import pytest
from PIL import Image
from slide_core.media import probe_source, MediaError
from slide_core.pts import sample_stream,extract_selected

pytestmark = pytest.mark.skipif(shutil.which('ffmpeg') is None,reason='FFmpeg unavailable')


def make_video(path,duration=4,fps=4,offset=0,bframes=0):
    cmd=['ffmpeg','-hide_banner','-loglevel','error','-y','-f','lavfi',
         '-i',f'testsrc2=size=96x64:rate={fps}:duration={duration}',
         '-vf',f'setpts=PTS+({offset})/TB' if offset else 'null',
         '-c:v','mpeg4','-bf',str(bframes),'-q:v','2',str(path)]
    subprocess.run(cmd,check=True,timeout=25)
    return probe_source(path)


@pytest.mark.parametrize('duration',(.1,.4,1.,2.2))
def test_short_first_frame_and_exact_bucket(tmp_path,duration):
    source=make_video(tmp_path/'short.mp4',duration=duration,fps=10)
    samples,session=sample_stream(source,tmp_path/'cache')
    assert samples and samples[0].grid_index==0
    assert samples[0].source_pts==dict(source.metadata)['origin_pts']
    assert [s.grid_index for s in samples]==list(range(len(samples)))
    assert all(Path(s.cache_path).exists() for s in samples)
    assert session.exists()


@pytest.mark.parametrize('sample_rate,grid',( (Fraction(1),[0,1,2,3]),
                                             (Fraction(1,2),[0,1]) ))
def test_bucket_rate_and_selected_full_frame(tmp_path,sample_rate,grid):
    source=make_video(tmp_path/'video.mp4',duration=4,fps=4,bframes=2)
    samples,_=sample_stream(source,tmp_path/'cache',fps=sample_rate)
    assert [x.grid_index for x in samples]==grid
    extracted=extract_selected(source,samples,tmp_path/'full')
    for path,s in zip(extracted,samples):
        full=Image.open(path).convert('RGB')
        sample=Image.open(s.cache_path).convert('RGB')
        assert full.size==(96,64)
        # JPEG sampling should be perceptually near the full RGB export.
        import numpy as np
        assert np.abs(np.array(full,dtype='int16')-np.array(sample,dtype='int16')).mean()<14


def test_nonzero_source_origin(tmp_path):
    source=make_video(tmp_path/'offset.mkv',duration=2,fps=4,offset=8)
    samples,_=sample_stream(source,tmp_path/'cache')
    assert len(samples)==2
    assert samples[0].source_pts==dict(source.metadata)['origin_pts']
    assert [s.grid_index for s in samples]==[0,1]
    assert samples[0].actual_time==0


def test_missing_selected_pts_fails_instead_of_substitution(tmp_path):
    source=make_video(tmp_path/'video.mp4',duration=1,fps=4)
    pts=dict(source.metadata)['origin_pts']
    with pytest.raises(MediaError,match='PTS missing'):
        extract_selected(source,[pts+9],tmp_path/'full')


def test_bad_source_detected_before_sampling(tmp_path):
    source=make_video(tmp_path/'video.mp4',duration=1,fps=4)
    path=source.path
    data=bytearray(path.read_bytes());data[100]^=255
    path.write_bytes(data)
    with pytest.raises(MediaError,match='SourceChanged'):
        sample_stream(source,tmp_path/'cache')


def test_small_video_no_upscale(tmp_path):
    source=make_video(tmp_path/'short.mp4',duration=1,fps=4)
    samples,_=sample_stream(source,tmp_path/'cache')
    assert (samples[0].width,samples[0].height)==(96,64)


def test_invalid_rate_fails(tmp_path):
    source=make_video(tmp_path/'v.mp4',duration=1,fps=4)
    with pytest.raises(ValueError):sample_stream(source,tmp_path/'cache',fps=Fraction(3,2))


def test_cancelled_does_not_publish_complete_cache(tmp_path):
    from slide_core.models import CancelToken
    source=make_video(tmp_path/'source.mp4',duration=3,fps=4)
    cancellation=CancelToken();cancellation.cancel()
    with pytest.raises(MediaError,match='Cancelled'):
        sample_stream(source,tmp_path/'cache',cancelled=cancellation)
    for path in (tmp_path/'cache').glob('session-*/manifest.json'):
        import json
        assert json.loads(path.read_text())['complete'] is False
