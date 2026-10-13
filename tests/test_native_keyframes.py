import io
import struct
import sys
from fractions import Fraction
from types import SimpleNamespace
import pytest
from slide_core import native_keyframes as native
from slide_core.media import MediaError
from slide_core.models import CancelToken

TB = Fraction(1, 1000)
def stream(records, complete=True):
    body = b'SEKF0001'
    for ordinal, pts, pixels in records:
        body += struct.pack('<BqQiiIII', 1, pts, ordinal, 1, 1000, 2, 2, len(pixels)) + pixels
    if complete:
        body += struct.pack('<BQ', 2, len(records))
    return body

def parse(payload):
    return list(native.parse_frames(io.BytesIO(payload).read, 2, 2, TB))

def test_valid_records_keep_decoded_pts():
    assert parse(stream([(0, 9000, b'x'*12), (1, 11000, b'y'*12)])) == [(9000,b'x'*12),(11000,b'y'*12)]

@pytest.mark.parametrize('payload', [
    b'', b'SEKF0002',
    stream([(0,1,b'x'*11)]),
    stream([(0,2,b'x'*12),(1,1,b'x'*12)]),
    stream([(0,1,b'x'*12),(2,2,b'x'*12)]),
    stream([(0,1,b'x'*12)], False),
    stream([], True),
    stream([(0,1,b'x'*12)])[:-1],
    stream([(0,1,b'x'*12)]) + b'junk',
])
def test_invalid_protocol_cannot_complete(payload):
    with pytest.raises(MediaError):
        parse(payload)

def worker(monkeypatch, tmp_path, body):
    script=tmp_path/'worker.py'
    script.write_text('import sys,time\n'+body)
    monkeypatch.setattr(native,'native_command',lambda *a:[sys.executable,str(script)])
    source=SimpleNamespace(metadata=(('time_base_num',1),('time_base_den',1000)))
    pipe=SimpleNamespace(cache_width=2,cache_height=2)
    return source,pipe

def test_worker_success(monkeypatch,tmp_path):
    payload=stream([(0,3,b'x'*12)])
    source,pipe=worker(monkeypatch,tmp_path,f'sys.stdout.buffer.write({payload!r})\n')
    assert list(native.decode_native(source,pipe)) == [(3,b'x'*12)]

def test_worker_nonzero_exit_is_not_success(monkeypatch,tmp_path):
    payload=stream([(0,3,b'x'*12)])
    source,pipe=worker(monkeypatch,tmp_path,f'sys.stdout.buffer.write({payload!r})\nsys.exit(7)\n')
    with pytest.raises(MediaError):
        list(native.decode_native(source,pipe))

def test_unsupported_exit_can_fallback(monkeypatch,tmp_path):
    source,pipe=worker(monkeypatch,tmp_path,'sys.exit(20)\n')
    with pytest.raises(native.NativeUnsupported):
        list(native.decode_native(source,pipe))

def test_inactivity_reaps_worker(monkeypatch,tmp_path):
    source,pipe=worker(monkeypatch,tmp_path,'time.sleep(5)\n')
    with pytest.raises(MediaError) as error:
        list(native.decode_native(source,pipe,stall_timeout=.1))
    assert error.value.code == 'Timeout'

def test_cancel_reaps_worker(monkeypatch,tmp_path):
    source,pipe=worker(monkeypatch,tmp_path,'time.sleep(5)\n')
    token=CancelToken();token.cancel()
    with pytest.raises(MediaError) as error:
        list(native.decode_native(source,pipe,cancelled=token))
    assert error.value.code == 'Cancelled'

def test_native_preparation_uses_existing_cache_contract(monkeypatch,tmp_path):
    from slide_core import pts
    from tests.decoder_fixtures import sampling_source
    source=sampling_source(monkeypatch,SimpleNamespace(width=2,height=2))
    def images(*a,**k):
        yield 0,b'x'*12
        yield 1,b'y'*12
    monkeypatch.setattr(native,'decode_native',images)
    owners=[]
    samples,directory=pts.keyframe_stream(source,tmp_path/'cache',backend='native-idr',cache_owner=owners.append)
    assert [s.source_pts for s in samples] == [0,1]
    assert len(list(directory.glob('*.jpg'))) == 2
    assert len(owners) == 1
    owners[0].close()

def test_unsupported_partial_generation_restarts_whole_cache(monkeypatch,tmp_path):
    from slide_core import pts
    from tests.decoder_fixtures import sampling_source
    source=sampling_source(monkeypatch,SimpleNamespace(width=2,height=2))
    def unsupported(*a,**k):
        yield 0,b'x'*12
        raise native.NativeUnsupported('non-IDR')
    monkeypatch.setattr(native,'decode_native',unsupported)
    def fallback(*a,**k):
        assert not list((tmp_path/'cache').rglob('*.jpg'))
        yield 0,b'y'*12
        yield 1,b'z'*12
    monkeypatch.setattr(pts,'_decode_stream',fallback)
    samples,directory=pts.keyframe_stream(source,tmp_path/'cache',backend='native-idr')
    assert len(samples) == 2
    assert len(list((tmp_path/'cache').rglob('*.jpg'))) == 2

@pytest.mark.parametrize('code',['Cancelled','InvalidTiming','Timeout','SourceChanged'])
def test_native_errors_do_not_fallback(monkeypatch,tmp_path,code):
    from slide_core import pts
    from tests.decoder_fixtures import sampling_source
    source=sampling_source(monkeypatch,SimpleNamespace(width=2,height=2))
    def broken(*a,**k):
        yield 0,b'x'*12
        raise MediaError(code,code=code)
    monkeypatch.setattr(native,'decode_native',broken)
    def forbidden(*a,**k):
        pytest.fail('must not fall back')
    monkeypatch.setattr(pts,'_decode_stream',forbidden)
    with pytest.raises(MediaError) as err:
        pts.keyframe_stream(source,tmp_path/'cache',backend='native-idr')
    assert err.value.code == code
    assert not list((tmp_path/'cache').rglob('*.jpg'))

def test_native_can_progress_beyond_total_budget(monkeypatch,tmp_path):
    records=[(i,i,b'x'*12) for i in range(6)]
    payloads=[stream([record],False) for record in records]
    # Emit the actual ordinal, sharing one header and terminal completion.
    body="sys.stdout.buffer.write(b'SEKF0001');sys.stdout.flush()\n"
    for ordinal,pts,pixels in records:
        record=struct.pack('<BqQiiIII',1,pts,ordinal,1,1000,2,2,12)+pixels
        body+=f"sys.stdout.buffer.write({record!r});sys.stdout.flush();time.sleep(.06)\n"
    body+="sys.stdout.buffer.write("+repr(struct.pack('<BQ',2,6))+");sys.stdout.flush()\n"
    source,pipe=worker(monkeypatch,tmp_path,body)
    assert len(list(native.decode_native(source,pipe,stall_timeout=.25))) == 6

def test_partial_output_cancel_reaps_and_closes(monkeypatch,tmp_path):
    source,pipe=worker(monkeypatch,tmp_path,
        f"sys.stdout.buffer.write({stream([(0,1,b'x'*12)],False)!r});sys.stdout.flush();time.sleep(5)\n")
    children=[];real=native.subprocess.Popen
    def start(*a,**kw):
        child=real(*a,**kw);children.append(child);return child
    monkeypatch.setattr(native.subprocess,'Popen',start)
    token=CancelToken();decoded=native.decode_native(source,pipe,cancelled=token)
    assert next(decoded) == (1,b'x'*12)
    token.cancel()
    with pytest.raises(MediaError) as error:
        next(decoded)
    assert error.value.code == 'Cancelled'
    assert all(p.poll() is not None and p.stdout.closed and p.stderr.closed for p in children)

def test_slow_cache_consumer_does_not_count_as_decoder_stall(monkeypatch,tmp_path):
    import time
    source,pipe=worker(monkeypatch,tmp_path,
        f"sys.stdout.buffer.write({stream([(0,1,b'x'*12),(1,2,b'y'*12)])!r});sys.stdout.flush()\n")
    decoded=native.decode_native(source,pipe,stall_timeout=.15)
    assert next(decoded) == (1,b'x'*12)
    time.sleep(.2)
    assert list(decoded) == [(2,b'y'*12)]

def test_demux_progress_records_keep_sparse_stream_alive(monkeypatch,tmp_path):
    body="sys.stdout.buffer.write(b'SEKF0001');sys.stdout.flush()\n"
    for counter in range(1,7):
        progress=struct.pack('<BQ',3,counter)
        body+=f"sys.stdout.buffer.write({progress!r});sys.stdout.flush();time.sleep(.06)\n"
    payload=stream([(0,1,b'x'*12)])[8:]
    body+=f"sys.stdout.buffer.write({payload!r});sys.stdout.flush()\n"
    source,pipe=worker(monkeypatch,tmp_path,body)
    assert list(native.decode_native(source,pipe,stall_timeout=.25)) == [(1,b'x'*12)]

def test_regressing_demux_progress_is_invalid():
    payload=b'SEKF0001'+struct.pack('<BQ',3,2)+struct.pack('<BQ',3,1)+stream([(0,1,b'x'*12)])[8:]
    with pytest.raises(MediaError):
        parse(payload)

def test_half_protocol_preserves_source_keyframe_ordinals():
    payload=stream([(0,1,b'x'*12),(2,3,b'y'*12)])
    assert list(native.parse_frames(io.BytesIO(payload).read,2,2,TB,selection_policy='half')) == [(1,b'x'*12),(3,b'y'*12)]

def test_half_preparation_reports_effective_policy(monkeypatch,tmp_path):
    from slide_core import pts
    from slide_core.profiling import AnalysisProfile
    from tests.decoder_fixtures import sampling_source
    source=sampling_source(monkeypatch,SimpleNamespace(width=2,height=2))
    def images(*a,**k):
        assert k['selection_policy'] == 'half'
        yield 0,b'x'*12
    monkeypatch.setattr(native,'decode_native',images)
    profile=AnalysisProfile()
    pts.keyframe_stream(source,tmp_path/'cache',backend='native-idr',selection_policy='half',profile=profile)
    assert profile.metadata['selection_policy'] == 'half'

def test_half_fallback_reports_all_policy(monkeypatch,tmp_path):
    from slide_core import pts
    from slide_core.profiling import AnalysisProfile
    from tests.decoder_fixtures import sampling_source
    source=sampling_source(monkeypatch,SimpleNamespace(width=2,height=2))
    def unsupported(*a,**k):
        raise native.NativeUnsupported('unavailable')
        yield
    def full(*a,**k):
        yield 0,b'x'*12
        yield 1,b'y'*12
    monkeypatch.setattr(native,'decode_native',unsupported)
    monkeypatch.setattr(pts,'_decode_stream',full)
    profile=AnalysisProfile()
    samples,_=pts.keyframe_stream(source,tmp_path/'cache',backend='native-idr',selection_policy='half',profile=profile)
    assert len(samples)==2
    assert profile.metadata['selection_policy']=='all'
    assert profile.metadata['requested_selection_policy']=='half'
