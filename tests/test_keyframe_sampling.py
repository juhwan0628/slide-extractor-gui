"""Real keyframe decoder/PTS regressions; generated media only."""
import json,runpy,shutil,subprocess,sys,time
from fractions import Fraction
from pathlib import Path
import pytest
from PIL import Image
import numpy as np
from slide_core import pts
from slide_core.media import probe_source,MediaError
from slide_core.models import CancelToken
from tests.decoder_fixtures import decoder,sampling_source

def keyframes(source):
 result=subprocess.check_output(['ffprobe','-v','error','-select_streams','v:0','-show_frames','-show_entries','frame=key_frame,pts','-of','json',str(source.path)],timeout=30)
 return [int(f['pts']) for f in json.loads(result)['frames'] if f['key_frame']==1]

def video(path,codec='mpeg4',offset=0,vfr=False):
 encoders=subprocess.check_output(['ffmpeg','-hide_banner','-encoders'],stderr=subprocess.DEVNULL,text=True)
 if codec not in encoders:pytest.skip('Test encoder unavailable: '+codec)
 cmd=['ffmpeg','-hide_banner','-loglevel','error','-y','-f','lavfi','-i','testsrc2=size=96x64:rate=10:duration=2.4']
 if vfr:cmd+=['-vf','setpts=floor(N/2)*3+mod(N\\,2)']
 elif offset:cmd+=['-vf',f'setpts=PTS+{offset}/TB']
 cmd+=['-c:v',codec,'-g','5','-bf','2','-fps_mode','passthrough']
 if codec=='libx264':cmd+=['-preset','ultrafast','-x264-params','scenecut=0']
 if codec=='libx265':cmd+=['-preset','ultrafast','-x265-params','pools=1:frame-threads=1:scenecut=0']
 subprocess.run(cmd+[str(path)],check=True,timeout=40,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
 return probe_source(path)

@pytest.mark.parametrize('codec,offset,vfr',[('mpeg4',0,False),('mpeg4',8,False),('mpeg4',0,True),('libx264',0,False),('libx265',0,False)])
def test_keyframe_images_pair_with_original_decoder_pts(tmp_path,codec,offset,vfr):
 source=video(tmp_path/'source.mkv',codec,offset,vfr)
 samples,directory=pts.keyframe_stream(source,tmp_path/'cache')
 expected=keyframes(source);origin=dict(source.metadata)['origin_pts']
 assert [s.source_pts for s in samples]==expected
 assert len(samples)<24
 assert [s.ordinal for s in samples]==list(range(len(samples)))
 assert all(s.actual_time==(s.source_pts-origin)*s.time_base for s in samples)
 assert len(list(directory.glob('*.jpg')))==len(samples)
 full=pts.extract_selected(source,samples,tmp_path/'full')
 for sample,path in zip(samples,full):
  a=np.array(Image.open(sample.cache_path).convert('RGB'),dtype='int16')
  b=np.array(Image.open(path).convert('RGB'),dtype='int16')
  assert np.abs(a-b).mean()<14
 assert json.loads((directory/'manifest.json').read_text())['complete']

def test_decoder_skip_precedes_input_and_has_no_grid_filter(tmp_path):
 source=video(tmp_path/'source.mkv')
 cmd=pts._ffmpeg(source,'showinfo@audit,showinfo@sample,null',decode_options={'backend':'cpu-keyframes'})
 assert cmd.index('-skip_frame')<cmd.index('-i')
 assert cmd[cmd.index('-skip_frame')+1]=='nokey'
 assert cmd[cmd.index('-fps_mode')+1]=='passthrough'

def emit(n,pt,key=1,selected=None):
 selected=pt if selected is None else selected
 return f"sys.stderr.write('[showinfo@audit] n: {n} pts: {pt} s:2x2 i:P iskey:{key} type:I\\n[showinfo@sample] n: {n} pts: {selected}\\n');sys.stderr.flush();sys.stdout.buffer.write(b'x'*12);sys.stdout.flush()\n"

@pytest.mark.parametrize('body,code',[
 (emit(0,0,0),'DecodeFailed'),
 (emit(0,0,selected=1),'InvalidTiming'),
 (emit(0,0)+emit(1,0),'InvalidTiming')])
def test_keyframe_audit_refuses_false_keyframe_or_mismatched_pts(monkeypatch,tmp_path,body,code):
 source=sampling_source(monkeypatch,decoder(monkeypatch,tmp_path,body))
 with pytest.raises(MediaError) as err:pts.keyframe_stream(source,tmp_path/'cache')
 assert err.value.code==code
 assert not list((tmp_path/'cache').rglob('*.jpg'))

@pytest.mark.parametrize('cancel',[False,True])
def test_keyframe_stall_or_cancel_discards_partial_cache_and_reaps(monkeypatch,tmp_path,cancel):
 source=sampling_source(monkeypatch,decoder(monkeypatch,tmp_path,emit(0,0)+'time.sleep(10)\n'))
 children=[];real=pts.subprocess.Popen
 def start(*a,**kw):
  child=real(*a,**kw);children.append(child);return child
 monkeypatch.setattr(pts.subprocess,'Popen',start)
 token=CancelToken()
 def progress(*a):
  if cancel and list((tmp_path/'cache').rglob('*.jpg')):token.cancel()
 with pytest.raises(MediaError) as err:pts.keyframe_stream(source,tmp_path/'cache',timeout=.2,cancelled=token,progress=progress)
 assert err.value.code==('Cancelled' if cancel else 'Timeout')
 assert all(p.poll() is not None and p.stdout.closed and p.stderr.closed for p in children)
 assert not list((tmp_path/'cache').rglob('*.jpg'))

def test_keyframe_progress_exceeds_total_time_budget(monkeypatch,tmp_path):
 source=sampling_source(monkeypatch,decoder(monkeypatch,tmp_path,''.join(emit(n,n)+'time.sleep(.06)\n' for n in range(8))))
 samples,_=pts.keyframe_stream(source,tmp_path/'cache',timeout=.25)
 assert len(samples)==8

def test_keyframe_bad_source_refused_before_cache(tmp_path):
 source=video(tmp_path/'source.mkv')
 source.path.write_bytes(b'changed')
 with pytest.raises(MediaError) as err:pts.keyframe_stream(source,tmp_path/'cache')
 assert err.value.code=='SourceChanged'
 assert not list((tmp_path/'cache').rglob('*.jpg'))

@pytest.mark.parametrize('body,code',[
 ('','InvalidTiming'),
 ("sys.stderr.write('[showinfo@audit] n: 0 pts: 0 s:2x2 i:P iskey:1 type:I\\n[showinfo@sample] n: 0 pts: 0\\n');sys.stderr.flush();sys.stdout.buffer.write(b'x'*3);sys.stdout.flush()\n",'DecodeFailed'),
 ("sys.stderr.write('[showinfo@audit] n: 0 pts: N/A s:2x2 i:P iskey:1 type:I\\n');sys.stderr.flush()\n",'InvalidTiming')])
def test_keyframe_empty_truncated_or_missing_timestamp_refused(monkeypatch,tmp_path,body,code):
 source=sampling_source(monkeypatch,decoder(monkeypatch,tmp_path,body))
 with pytest.raises(MediaError) as err:pts.keyframe_stream(source,tmp_path/'cache')
 assert err.value.code==code
 assert not list((tmp_path/'cache').rglob('*.jpg'))

def test_keyframe_source_mutation_during_decode_cleans_cache(tmp_path):
 source=video(tmp_path/'source.mkv')
 def mutate(*a):
  if a[1]==1:source.path.write_bytes(b'mutated')
 with pytest.raises(MediaError) as err:pts.keyframe_stream(source,tmp_path/'cache',progress=mutate)
 assert err.value.code=='SourceChanged'
 assert not list((tmp_path/'cache').rglob('*.jpg'))

@pytest.mark.parametrize('gop',[1,1000])
def test_all_intra_and_long_gop_keep_actual_keyframes(tmp_path,gop):
 path=tmp_path/'source.mkv'
 subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y','-f','lavfi','-i','testsrc2=size=96x64:rate=10:duration=1','-c:v','mpeg4','-g',str(gop),str(path)],check=True,timeout=20)
 source=probe_source(path);samples,_=pts.keyframe_stream(source,tmp_path/'cache')
 assert [s.source_pts for s in samples]==keyframes(source)
 assert len(samples)==(10 if gop==1 else 1)
