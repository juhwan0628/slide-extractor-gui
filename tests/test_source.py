import json
from fractions import Fraction
from pathlib import Path

import pytest
from slide_core import media
from slide_core.media import MediaError, fingerprint_source, probe_source, source_matches


def fake_probe(monkeypatch, *, duration="3.5", stream_duration=None, attached=False,
               first_pts="100", mutate=None, video_index=2):
    sources = [
        {"index":0, "codec_type":"audio"},
        {"index":1, "codec_type":"video", "disposition":{"attached_pic":1},
         "width":600,"height":600,"codec_name":"mjpeg"},
        {"index":video_index,"codec_type":"video","disposition":{"attached_pic":0},
         "codec_name":"h264","width":1920,"height":1080,
         "sample_aspect_ratio":"1:1","time_base":"1/90000",
         "side_data_list":[{"rotation":90}],"duration":stream_duration}
    ]
    if attached:
        sources = sources[:2]
    commands=[]
    def run(argv, **kw):
        commands.append(argv)
        assert kw["timeout"] == media.PROCESS_TIMEOUTS["probe"]
        if "-show_streams" in argv:
            return media._ProcessResult(json.dumps({"streams":sources, "format":{"duration":duration}}), "", 0)
        assert "-read_intervals" in argv and "%+#1" in argv
        assert argv[argv.index("-select_streams")+1] == str(video_index)
        if mutate:
            mutate()
        return media._ProcessResult(json.dumps({"frames":[{"best_effort_timestamp":first_pts}]}), "", 0)
    monkeypatch.setattr(media,"_run_process",run)
    return commands


def test_probe_selects_real_non_attached_stream_and_origin(tmp_path,monkeypatch):
    video=tmp_path/"demo.mp4";video.write_bytes(b"0123456789")
    commands=fake_probe(monkeypatch)
    source=probe_source(video)
    assert source.stream_index==2
    assert source.width==1920 and source.height==1080
    assert source.transform.rotation==90
    assert source.transform.display_width==1080
    assert source.transform.display_height==1920
    assert dict(source.metadata)["origin_pts"]==100
    assert dict(source.metadata)["duration_kind"]=="container_estimate"
    assert dict(source.metadata)["duration_s"]==3.5
    assert source_matches(source)
    assert len(commands)==2


@pytest.mark.parametrize("duration,stream",[(None,None),("NaN",None),("0",None),("-5",None)])
def test_probe_rejects_unknown_duration(tmp_path,monkeypatch,duration,stream):
    video=tmp_path/"x.mp4";video.write_bytes(b"data")
    fake_probe(monkeypatch,duration=duration,stream_duration=stream)
    with pytest.raises(MediaError) as err:probe_source(video)
    assert err.value.code=="InvalidTiming"


def test_stream_duration_preferred_over_container_estimate(tmp_path,monkeypatch):
    video=tmp_path/"x.mp4";video.write_bytes(b"data")
    fake_probe(monkeypatch,duration="9.0",stream_duration="2.0")
    s=probe_source(video)
    assert dict(s.metadata)["duration_s"]==2.0
    assert dict(s.metadata)["duration_kind"]=="video_metadata"


def test_probe_rejects_cover_art_only(tmp_path,monkeypatch):
    video=tmp_path/"x.mp4";video.write_bytes(b"data")
    fake_probe(monkeypatch,attached=True)
    with pytest.raises(MediaError,match="InvalidTiming"):probe_source(video)


def test_probe_rejects_replaced_source_during_probe(tmp_path,monkeypatch):
    video=tmp_path/"x.mp4";video.write_bytes(b"old-data")
    def mutate(): video.write_bytes(b"new-content")
    fake_probe(monkeypatch,mutate=mutate)
    with pytest.raises(MediaError) as err:probe_source(video)
    assert err.value.code=="SourceChanged"


def test_fingerprint_catches_same_size_same_mtime_mutation(tmp_path,monkeypatch):
    video=tmp_path/"x.mp4";video.write_bytes(b"abc"*100)
    fake_probe(monkeypatch)
    old=probe_source(video)
    stat=video.stat()
    video.write_bytes(b"xyz"*100)
    import os
    os.utime(video,ns=(stat.st_atime_ns, stat.st_mtime_ns))
    assert not source_matches(old)


def test_fingerprint_is_bounded_and_deterministic(tmp_path):
    path=tmp_path/"large.bin";path.write_bytes(b"A"*(4*1024*1024))
    a=fingerprint_source(path)
    b=fingerprint_source(path)
    assert a==b and len(a)==64
    with path.open("r+b") as stream:
        stream.seek(2*1024*1024);stream.write(b"mutated")
    assert fingerprint_source(path)!=a


def test_missing_source_is_error(tmp_path):
    with pytest.raises((OSError,MediaError)):
        probe_source(tmp_path/"does_not_exist.mp4")
