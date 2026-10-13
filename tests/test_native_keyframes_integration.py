"""Real generated media: exact PTS/RGB equivalence, no tolerance."""
from fractions import Fraction
from pathlib import Path
from dataclasses import replace
import subprocess
import shutil
import pytest
from slide_core.media import probe_source
from slide_core.display import build_display_pipeline
from slide_core import pts
from slide_core.native_keyframes import decode_native, NativeUnsupported

ROOT=Path(__file__).resolve().parents[1]
@pytest.fixture(scope='module')
def helper():
    path=ROOT/'build/native/slide-keyframe-decode'
    if not path.is_file():
        if not shutil.which('cmake') or not shutil.which('pkg-config'):
            pytest.skip('Native build tools unavailable')
        probe=subprocess.run(['pkg-config','--exists','libavformat','libavcodec','libavfilter','libavutil'])
        if probe.returncode:
            pytest.skip('Native FFmpeg development libraries unavailable')
        subprocess.run(['cmake','-S',str(ROOT/'native'),'-B',str(path.parent),
                        '-DCMAKE_BUILD_TYPE=Release'],check=True,timeout=60)
        subprocess.run(['cmake','--build',str(path.parent),'-j2'],check=True,timeout=60)
    return path

def pipeline(source):
    info=dict(source.metadata)
    return build_display_pipeline(width=source.width,height=source.height,
        sar=source.transform.sample_aspect_ratio,rotation=source.transform.rotation,
        color_matrix=info.get('color_matrix'),color_range=info.get('color_range'),
        transfer=info.get('color_transfer'),pixel_format=info.get('pixel_format','yuv420p'))

def make(path, *, offset=0, matrix='bt709', rng='tv', sar='1', open_gop=False, duration=2, repeat_headers=False):
    subprocess.run(['ffmpeg','-v','error','-y','-f','lavfi','-i',
        f'testsrc2=size=800x450:rate=8:duration={duration}',
        '-vf',f'setsar={sar},setpts=PTS+{offset}/TB','-c:v','libx264',
        '-preset','ultrafast','-g','4','-bf','2','-x264-params',
        'scenecut=0:open-gop='+str(int(open_gop))+':repeat-headers='+str(int(repeat_headers)),
        '-colorspace',matrix,'-color_range',rng,str(path)],check=True,timeout=30)
    return probe_source(path)

@pytest.mark.parametrize('rotation,offset,sar,matrix,rng', [
    (0,0,'1','bt709','tv'),(90,8,'1','bt709','tv'),
    (180,0,'4/3','smpte170m','tv'),(270,0,'1','bt709','pc')])
def test_native_rgb_exactly_matches_ffmpeg(tmp_path,monkeypatch,helper,rotation,offset,sar,matrix,rng):
    source=make(tmp_path/'input.mp4',offset=offset,sar=sar,matrix=matrix,rng=rng)
    source=replace(source,transform=replace(source.transform,rotation=rotation))
    pipe=pipeline(source)
    monkeypatch.setenv('SLIDE_NATIVE_KEYFRAME_HELPER',str(helper))
    expected=list(pts._decode_stream(source,
        'showinfo@audit,showinfo@sample,'+pipe.cache_filter,
        pipe.cache_width,pipe.cache_height,timeout=None,stall_timeout=120))
    actual=list(decode_native(source,pipe))
    assert actual == expected

def test_non_idr_key_packet_is_unsupported(tmp_path,monkeypatch,helper):
    source=make(tmp_path/'open.mp4',open_gop=True)
    monkeypatch.setenv('SLIDE_NATIVE_KEYFRAME_HELPER',str(helper))
    with pytest.raises(NativeUnsupported):
        list(decode_native(source,pipeline(source)))

def test_selected_video_stream_is_respected(tmp_path,monkeypatch,helper):
    first=make(tmp_path/'first.mp4')
    subprocess.run(['ffmpeg','-v','error','-y','-f','lavfi','-i',
        'color=red:size=800x450:rate=8:duration=2','-c:v','libx264','-g','4',
        '-bf','2','-colorspace','bt709','-color_range','tv',str(tmp_path/'second.mp4')],
        check=True,timeout=30)
    path=tmp_path/'multi.mp4'
    subprocess.run(['ffmpeg','-v','error','-y','-i',str(first.path),'-i',
        str(tmp_path/'second.mp4'),'-map','0:v:0','-map','1:v:0','-c','copy',str(path)],
        check=True,timeout=30)
    source=replace(probe_source(path),stream_index=1)
    pipe=pipeline(source);monkeypatch.setenv('SLIDE_NATIVE_KEYFRAME_HELPER',str(helper))
    expected=list(pts._decode_stream(source,'showinfo@audit,showinfo@sample,'+pipe.cache_filter,
        pipe.cache_width,pipe.cache_height,timeout=None,stall_timeout=120))
    assert list(decode_native(source,pipe)) == expected

def test_real_unsupported_codec_uses_full_fallback(tmp_path,monkeypatch,helper):
    from tests.media_fixtures import make_video
    source=make_video(tmp_path/'mpeg4.mp4')
    monkeypatch.setenv('SLIDE_NATIVE_KEYFRAME_HELPER',str(helper))
    a,_=pts.keyframe_stream(source,tmp_path/'all')
    b,_=pts.keyframe_stream(source,tmp_path/'fallback',backend='native-idr')
    assert [s.source_pts for s in a] == [s.source_pts for s in b]
    assert [Path(s.cache_path).read_bytes() for s in a] == [Path(s.cache_path).read_bytes() for s in b]

@pytest.mark.parametrize('duration',[1.25,2])
def test_half_native_is_exact_subset_before_cache(tmp_path,monkeypatch,helper,duration):
    source=make(tmp_path/'subset.mp4',duration=duration)
    pipe=pipeline(source);monkeypatch.setenv('SLIDE_NATIVE_KEYFRAME_HELPER',str(helper))
    all_frames=list(decode_native(source,pipe))
    half_frames=list(decode_native(source,pipe,selection_policy='half'))
    assert half_frames == all_frames[::2]
    assert len(half_frames)==(len(all_frames)+1)//2
    all_samples,_=pts.keyframe_stream(source,tmp_path/'all')
    half_samples,_=pts.keyframe_stream(source,tmp_path/'half',backend='native-idr',selection_policy='half')
    assert [s.source_pts for s in half_samples] == [s.source_pts for s in all_samples[::2]]
    assert [Path(s.cache_path).read_bytes() for s in half_samples] == [Path(s.cache_path).read_bytes() for s in all_samples[::2]]

def test_half_validates_skipped_non_idr_key_packets(tmp_path,monkeypatch,helper):
    source=make(tmp_path/'open-half.mp4',open_gop=True)
    monkeypatch.setenv('SLIDE_NATIVE_KEYFRAME_HELPER',str(helper))
    # The second key packet is skipped by half policy, but must still reject open GOP.
    with pytest.raises(NativeUnsupported):
        list(decode_native(source,pipeline(source),selection_policy='half'))

def test_prepared_half_records_effective_selection(tmp_path,monkeypatch,helper):
    from slide_core.preparation import prepare_samples
    source=make(tmp_path/'prepared.mp4')
    monkeypatch.setenv('SLIDE_NATIVE_KEYFRAME_HELPER',str(helper))
    prepared=prepare_samples(source,tmp_path/'cache',backend='native-idr',selection_policy='half')
    try:
        assert prepared.selection_policy=='half'
        assert prepared.decoder_backend=='native-idr'
    finally:
        prepared.discard()

def test_prepared_half_fallback_records_all(tmp_path,monkeypatch,helper):
    from slide_core.preparation import prepare_samples
    from tests.media_fixtures import make_video
    source=make_video(tmp_path/'unsupported.mp4')
    monkeypatch.setenv('SLIDE_NATIVE_KEYFRAME_HELPER',str(helper))
    prepared=prepare_samples(source,tmp_path/'cache',backend='native-idr',selection_policy='half')
    try:
        assert prepared.selection_policy=='all'
        assert prepared.decoder_backend=='cpu-keyframes'
    finally:
        prepared.discard()

def test_half_rejects_inband_configuration_on_skipped_packet(tmp_path,monkeypatch,helper):
    source=make(tmp_path/'repeat.mp4',repeat_headers=True)
    monkeypatch.setenv('SLIDE_NATIVE_KEYFRAME_HELPER',str(helper))
    with pytest.raises(NativeUnsupported):
        list(decode_native(source,pipeline(source),selection_policy='half'))

def test_half_cannot_hide_dynamic_dimensions_on_skipped_key(tmp_path,monkeypatch,helper):
    segments=[]
    for i,size in enumerate(('800x450','640x360','800x450')):
        path=tmp_path/f'segment-{i}.h264'
        subprocess.run(['ffmpeg','-v','error','-y','-f','lavfi','-i',
            f'testsrc2=size={size}:rate=8:duration=0.5','-c:v','libx264',
            '-preset','ultrafast','-g','100','-bf','0','-f','h264',str(path)],
            check=True,timeout=30)
        segments.append(path.read_bytes())
    raw=tmp_path/'dynamic.h264';raw.write_bytes(b''.join(segments))
    path=tmp_path/'dynamic.mp4'
    subprocess.run(['ffmpeg','-v','error','-y','-framerate','8','-i',str(raw),
        '-c','copy',str(path)],check=True,timeout=30)
    source=probe_source(path);monkeypatch.setenv('SLIDE_NATIVE_KEYFRAME_HELPER',str(helper))
    with pytest.raises(NativeUnsupported):
        list(decode_native(source,pipeline(source),selection_policy='half'))

def test_helper_version_exposes_linked_ffmpeg(helper):
    result=subprocess.run([str(helper),'-version'],capture_output=True,text=True)
    assert result.returncode==0
    assert 'configuration:' in result.stdout and 'license:' in result.stdout
