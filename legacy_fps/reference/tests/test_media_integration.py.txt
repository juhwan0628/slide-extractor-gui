"""End-to-end FFmpeg oracle for M2: only generated fixture videos."""
from fractions import Fraction
from pathlib import Path
import json
import shutil
import subprocess
import pytest
from PIL import Image

from slide_core.media import probe_source,MediaError
from slide_core.pts import sample_stream,extract_selected

pytestmark=pytest.mark.skipif(not shutil.which('ffmpeg') or not shutil.which('ffprobe'),reason='FFmpeg/FFprobe required')


def encode(path,*,duration=3,fps=4,filter='null',bframes=0):
    subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y','-f','lavfi',
                   '-i',f'testsrc2=size=96x64:rate={fps}:duration={duration}',
                   '-vf',filter,'-c:v','mpeg4','-bf',str(bframes),'-q:v','3',str(path)],
                   capture_output=True,check=True,timeout=25)
    return probe_source(path)


def oracle(source,fps):
    probe=subprocess.run(['ffprobe','-v','error','-select_streams',f'v:{0}',
        '-show_frames','-show_entries','frame=best_effort_timestamp',
        '-of','json',str(source.path)],capture_output=True,text=True,check=True,timeout=25)
    frames=json.loads(probe.stdout)['frames']
    pts=[int(f['best_effort_timestamp']) for f in frames if 'best_effort_timestamp' in f]
    assert pts and pts==sorted(set(pts))
    origin=dict(source.metadata)['origin_pts']
    tb=Fraction(dict(source.metadata)['time_base_num'],dict(source.metadata)['time_base_den'])
    seen=set();expected=[]
    for p in pts:
        bucket=int((p-origin)*tb*fps)
        if bucket not in seen:
            expected.append((bucket,p));seen.add(bucket)
    return expected


@pytest.mark.parametrize('duration,fps,container,offset,bframes,rate',[
    (.1,10,'mp4',0,0,Fraction(1)),
    (.4,10,'mp4',0,0,Fraction(1)),
    (1.,4,'mp4',0,0,Fraction(1)),
    (3.4,6,'mkv',0,2,Fraction(1)),
    (3.4,6,'mkv',0,2,Fraction(1,2)),
    (3.4,4,'mkv',8,2,Fraction(1)),
    (3.4,4,'mkv',-1,0,Fraction(1)),
])
def test_bucket_oracle_and_exact_frame(tmp_path,duration,fps,container,offset,bframes,rate):
    path=tmp_path/f'fixture.{container}'
    source=encode(path,duration=duration,fps=fps,
                  filter=f'setpts=PTS+({offset})/TB' if offset else 'null',bframes=bframes)
    expected=oracle(source,rate)
    samples,_=sample_stream(source,tmp_path/'cache',fps=rate)
    assert [(s.grid_index,s.source_pts) for s in samples]==expected
    for sample in samples:assert Path(sample.cache_path).exists()
    extracted=extract_selected(source,samples,tmp_path/'output')
    assert len(extracted)==len(samples)
    for path in extracted:
        assert Image.open(path).size==(96,64)


def test_unicode_path_and_sar(tmp_path):
    filename=tmp_path/'한글 0 space.mkv'
    source=encode(filename,filter='setsar=4/3')
    assert source.transform.display_width==128
    samples,_=sample_stream(source,tmp_path/'cache')
    assert samples[0].width==128
    paths=extract_selected(source,samples[:1],tmp_path/'full')
    assert Image.open(paths[0]).size==(128,64)


def test_corrupt_or_missing_input_rejected(tmp_path):
    file=tmp_path/'corrupted.mp4';file.write_bytes(b'not a video')
    with pytest.raises(MediaError):probe_source(file)
    with pytest.raises(FileNotFoundError):probe_source(tmp_path/'missing.mp4')


def test_true_vfr_gaps_no_synthetic_buckets(tmp_path):
    path=tmp_path/'variable frame rate.mkv'
    source=encode(path,duration=4,fps=4,
                  filter="setpts='PTS+if(gte(N,8),2/TB,0)'")
    expected=oracle(source,Fraction(1))
    assert [b for b,_ in expected]==[0,1,4,5]
    samples,_=sample_stream(source,tmp_path/'cache')
    assert [(s.grid_index,s.source_pts) for s in samples]==expected
    full=extract_selected(source,samples,tmp_path/'full')
    assert len(full)==len(samples)


def test_odd_roi_on_exact_full_resolution_frame(tmp_path):
    from slide_core.models import Rect
    source=encode(tmp_path/'odd.mp4',duration=2,fps=4)
    samples,_=sample_stream(source,tmp_path/'cache')
    crop=Rect(3,5,57,41)
    images=extract_selected(source,samples[:1],tmp_path/'full',roi=crop)
    assert Image.open(images[0]).size==(57,41)
    with pytest.raises(MediaError,match='invalid ROI'):
        extract_selected(source,samples[:1],tmp_path/'bad',roi=Rect(90,60,30,20))
