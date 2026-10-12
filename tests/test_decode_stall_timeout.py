"""Exercise real subprocess pipes, progress, consumer backpressure and reaping."""
import sys
import time
from types import SimpleNamespace
import pytest
from slide_core import pts
from slide_core.media import MediaError
from slide_core.models import CancelToken


def decoder(monkeypatch, tmp_path, body):
    script=tmp_path/'decoder.py'
    script.write_text('import sys,time\n'+body)
    monkeypatch.setattr(pts,'_ffmpeg',lambda *a,**kw:[sys.executable,str(script)])
    source=SimpleNamespace(width=2,height=2)
    return source


def emit(n):
    return f"sys.stderr.write('[showinfo@audit] n: {n} pts: {n} s:2x2 i:P iskey:1\\n[showinfo@sample] n: {n} pts: {n}\\n');sys.stderr.flush();sys.stdout.buffer.write(b'x'*12);sys.stdout.flush()\n"


def test_progressing_decode_outlives_total_budget(monkeypatch,tmp_path):
    source=decoder(monkeypatch,tmp_path,''.join(emit(n)+'time.sleep(.06)\n' for n in range(8)))
    frames=list(pts._decode_stream(source,'null',2,2,timeout=None,stall_timeout=.25))
    assert [pt for pt,_ in frames]==list(range(8))


def test_consumer_work_is_not_decoder_stall(monkeypatch,tmp_path):
    source=decoder(monkeypatch,tmp_path,''.join(emit(n) for n in range(32)))
    stream=pts._decode_stream(source,'null',2,2,timeout=None,stall_timeout=.15)
    assert next(stream)[0]==0
    time.sleep(.3)
    assert [pt for pt,_ in stream]==list(range(1,32))


def test_unselected_audited_frames_are_progress(monkeypatch,tmp_path):
    body=''
    for n in range(8):
        body+=f"sys.stderr.write('[showinfo@audit] n: {n} pts: {n} s:2x2 i:P iskey:1\\n');sys.stderr.flush();time.sleep(.06)\n"
    body+="sys.stderr.write('[showinfo@sample] n: 0 pts: 7\\n');sys.stderr.flush();sys.stdout.buffer.write(b'x'*12);sys.stdout.flush()\n"
    source=decoder(monkeypatch,tmp_path,body)
    assert [pt for pt,_ in pts._decode_stream(source,"showinfo@audit,select='gte(pts,7)',showinfo@sample,null",2,2,timeout=None,stall_timeout=.25)]==[7]


def test_log_noise_does_not_prevent_stall_and_child_is_reaped(monkeypatch,tmp_path):
    source=decoder(monkeypatch,tmp_path,"while True:\n sys.stderr.write('still alive\\n');sys.stderr.flush();time.sleep(.02)\n")
    real=pts.subprocess.Popen;children=[]
    def start(*a,**kw):
        proc=real(*a,**kw);children.append(proc);return proc
    monkeypatch.setattr(pts.subprocess,'Popen',start)
    with pytest.raises(MediaError) as error:
        list(pts._decode_stream(source,'null',2,2,timeout=None,stall_timeout=.2))
    assert error.value.code=='Timeout'
    assert children[0].poll() is not None
    assert children[0].stdout.closed and children[0].stderr.closed


def test_cancel_waiting_decoder_is_reaped(monkeypatch,tmp_path):
    source=decoder(monkeypatch,tmp_path,'time.sleep(10)\n');token=CancelToken();token.cancel()
    with pytest.raises(MediaError) as error:
        list(pts._decode_stream(source,'null',2,2,timeout=None,stall_timeout=5,cancelled=token))
    assert error.value.code=='Cancelled'


def test_explicit_total_deadline_still_applies_to_export(monkeypatch,tmp_path):
    source=decoder(monkeypatch,tmp_path,''.join(emit(n)+'time.sleep(.06)\n' for n in range(8)))
    with pytest.raises(MediaError) as error:
        list(pts._decode_stream(source,'null',2,2,timeout=.2))
    assert error.value.code=='Timeout'


def sampling_source(monkeypatch,source):
    from fractions import Fraction
    source.metadata=(('time_base_num',1),('time_base_den',1),('origin_pts',0))
    source.transform=SimpleNamespace(sample_aspect_ratio=Fraction(1),rotation=0)
    monkeypatch.setattr(pts,'source_matches',lambda _:True)
    return source


def test_sampling_uses_stall_budget_not_total_budget(monkeypatch,tmp_path):
    source=sampling_source(monkeypatch,decoder(monkeypatch,tmp_path,''.join(emit(n)+'time.sleep(.06)\n' for n in range(8))))
    samples,directory=pts.keyframe_stream(source,tmp_path/'cache',timeout=.25)
    assert len(samples)==8
    assert len(list(directory.glob('*.jpg')))==8


@pytest.mark.parametrize('cancel',[False,True])
def test_failed_sampling_discards_partial_jpegs(monkeypatch,tmp_path,cancel):
    source=sampling_source(monkeypatch,decoder(monkeypatch,tmp_path,emit(0)+'time.sleep(10)\n'))
    token=CancelToken()
    def progress(*args):
        if cancel and args[0]=='sampling' and list((tmp_path/'cache').rglob('*.jpg')):token.cancel()
    with pytest.raises(MediaError) as error:
        pts.keyframe_stream(source,tmp_path/'cache',timeout=.2,cancelled=token,progress=progress)
    assert error.value.code==('Cancelled' if cancel else 'Timeout')
    assert not list((tmp_path/'cache').rglob('*.jpg'))


def test_process_hanging_after_pipe_eof_times_out(monkeypatch,tmp_path):
    source=decoder(monkeypatch,tmp_path,emit(0)+'import os\nos.close(1);os.close(2);time.sleep(10)\n')
    with pytest.raises(MediaError) as error:
        list(pts._decode_stream(source,'null',2,2,timeout=None,stall_timeout=.2))
    assert error.value.code=='Timeout'
