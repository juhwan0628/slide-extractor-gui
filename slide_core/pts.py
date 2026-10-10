"""Exact integer-PTS frame selection and extraction without OpenCV seeks.

FFmpeg select is a streaming prefilter; Python revalidates every audited PTS
and every emitted frame before committing a complete cache generation.
"""
from __future__ import annotations
from fractions import Fraction
from pathlib import Path
from queue import Queue, Empty
from threading import Thread, Event
from collections import deque
from uuid import uuid4
from PIL import Image
import io
import math
import os
import re
import shutil
import signal
import subprocess
import time

from .cache import CacheSession
from .tools import executable
from .display import build_display_pipeline
from .media import MediaError, source_matches
from .models import Sample, SourceRef

_AUDIT = re.compile(r"\[showinfo@audit[^]]*\].*\bn:\s*(\d+)\s+pts:\s*(-?\d+|N/A)\b")
_SELECTED = re.compile(r"\[showinfo@sample[^]]*\].*\bn:\s*(\d+)\s+pts:\s*(-?\d+|N/A)\b")
_FORMAT = re.compile(r"\bs:(\d+)x(\d+)\s+i:([PTB])")
_COLOR_FIELDS = re.compile(r"\b(color_range|color_space|color_primaries|color_trc):(\S+)")

def _frame_color_signature(line):
    """Parse showinfo color fields independently of trailing metadata/formatting."""
    return dict(_COLOR_FIELDS.findall(line))

def _validate_frame_color(line,previous):
    current=_frame_color_signature(line)
    if any(v.lower() in {'smpte2084','arib-std-b67','bt2020','bt2020nc','bt2020c'} for v in current.values()):
        raise MediaError('UnsupportedDisplayTransform: unsupported HDR metadata',
                         code='UnsupportedDisplayTransform')
    for key,value in current.items():
        prior=previous.get(key)
        # "unknown"/"unspecified" is absence of metadata, not a measured change.
        if prior not in (None,'unknown','unspecified') and value not in ('unknown','unspecified') and prior!=value:
            raise MediaError('UnsupportedDisplayTransform: dynamic color metadata',
                             code='UnsupportedDisplayTransform')
    return {**previous, **{k:v for k,v in current.items()
                           if v not in ('unknown','unspecified')}}
_STOP = object()


def _source_info(source):
    values=dict(source.metadata)
    tb=Fraction(values['time_base_num'],values['time_base_den'])
    origin=int(values['origin_pts'])
    if tb<=0: raise MediaError("InvalidTiming: time base",code="InvalidTiming")
    return tb,origin


def _ffmpeg(source, vf, *, output='pipe:1', raw=True, seek=None, frame_limit=None, decode_options=None):
    cmd=[executable('ffmpeg'),'-hide_banner','-loglevel','info',
         '-nostdin','-copyts','-noautorotate']
    options=decode_options or {}
    backend=options.get('backend','cpu')
    threads=options.get('threads',0)
    if backend not in ('cpu','cpu-metadata','videotoolbox','videotoolbox-select') or type(threads) is not int or not 0<=threads<=64:
        raise ValueError('Unsupported decoder backend/thread count')
    if threads:cmd+=['-threads',str(threads)]
    if backend in ('videotoolbox','videotoolbox-select'):
        # Explicit hardware surfaces + hwdownload: software fallback cannot
        # silently count as a successful VideoToolbox comparison.
        pixel=dict(source.metadata).get('pixel_format','yuv420p')
        if pixel in ('yuv420p','yuvj420p','nv12'):download='nv12'
        elif pixel in ('yuv420p10le','p010le'):download='p010le'
        else:raise ValueError('Unsupported VideoToolbox download pixel format')
        cmd+=['-hwaccel','videotoolbox','-hwaccel_output_format','videotoolbox_vld']
        transfer='hwdownload,format='+download+','
        if backend=='videotoolbox-select':
            # Audit every PTS/color/transform using metadata only. Selection
            # reads timestamps, never scene/pixel values, on hardware frames.
            if not vf.startswith('showinfo@audit,select=') or ',showinfo@sample,' not in vf:
                raise ValueError('Hardware preselection requires audited sampling pipeline')
            vf=vf.replace('showinfo@audit,','showinfo@audit=checksum=0,',1)
            vf=vf.replace(',showinfo@sample,',','+transfer+'showinfo@sample,',1)
        else:
            vf=transfer+vf
    elif backend=='cpu-metadata':
        vf=vf.replace('showinfo@audit,','showinfo@audit=checksum=0,',1)
    if seek is not None:
        cmd+=['-seek_timestamp','1','-ss',str(float(seek))]
    cmd+=['-i',str(source.path),'-map',f'0:{source.stream_index}',
          '-an','-sn','-dn','-vf',vf,'-fps_mode','passthrough']
    if frame_limit is not None:cmd+=['-frames:v',str(frame_limit)]
    if raw:
        cmd+=['-pix_fmt','rgb24','-f','rawvideo',output]
    else:
        cmd+=['-f','null','-']
    return cmd


def _kill(proc):
    # A frame-limited decoder normally exits on its own. Reap it before
    # signalling: generator.close() can race with that normal exit on macOS.
    if proc.poll() is not None:
        proc.wait()
        return
    try:
        proc.wait(timeout=.25)
        return
    except subprocess.TimeoutExpired:
        pass
    try:
        if os.name=='nt':
            proc.kill()
        else:
            try:
                os.killpg(proc.pid,signal.SIGKILL)
            except (ProcessLookupError,PermissionError):
                # The group can disappear or reject signalling while our
                # directly owned child can still be terminated and reaped.
                proc.kill()
    except (ProcessLookupError,PermissionError):
        if proc.poll() is None:
            raise
    proc.wait(timeout=5)


def _decode_stream(source, vf, width, height, *, timeout=120, cancelled=None, seek=None, frame_limit=None, decode_options=None):
    """Return ordered (PTS, RGB bytes) using bounded queues and stdout drains."""
    cmd=_ffmpeg(source,vf,seek=seek,frame_limit=frame_limit,decode_options=decode_options)
    proc=subprocess.Popen(cmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                          start_new_session=os.name!='nt',bufsize=0,
                          creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0) if os.name=='nt' else 0)
    frame_bytes=width*height*3
    pixels=Queue(maxsize=8)
    pts_meta=Queue(maxsize=16)
    errors=[]
    audits={'previous':None,'frames':0,'selected':0,'color':None}
    recent=deque(maxlen=30)
    ended=Event()
    def push(q,value):
        while not ended.is_set():
            try:q.put(value,timeout=.15);return
            except Exception:continue
    def stderr_reader():
        try:
            for raw in proc.stderr:
                line=raw.decode('utf-8','replace')
                match=_AUDIT.search(line)
                if match:
                    n,pts=int(match[1]),match[2]
                    if pts=='N/A' or n!=audits['frames']:
                        errors.append('InvalidTiming: missing/out-of-order audit PTS');break
                    value=int(pts)
                    if audits['previous'] is not None and value<=audits['previous']:
                        errors.append('InvalidTiming: repeated/regressing display PTS');break
                    if (m:=_FORMAT.search(line)) and (int(m[1])!=source.width or int(m[2])!=source.height or m[3]!='P'):
                        errors.append('UnsupportedDisplayTransform: dynamic/interlaced stream');break
                    audits['previous']=value
                    audits['frames']+=1
                elif match:=_SELECTED.search(line):
                    n,pts=int(match[1]),match[2]
                    if pts=='N/A' or n!=audits['selected']:
                        errors.append('InvalidTiming: selected ordinal/PTS mismatch');break
                    audits['selected']+=1
                    push(pts_meta,int(pts))
                elif '[showinfo@audit' in line and 'color_range:' in line:
                    try:
                        audits['color']=_validate_frame_color(line,audits['color'] or {})
                    except MediaError as exc:
                        errors.append(str(exc));break
                elif 'Error' in line or 'error' in line.lower():recent.append(line.strip()[:250])
        finally:
            push(pts_meta,_STOP)
    def stdout_reader():
        try:
            while not ended.is_set():
                chunks=[];remaining=frame_bytes
                while remaining>0:
                    blob=proc.stdout.read(remaining)
                    if not blob:
                        if chunks:errors.append('DecodeFailed: truncated raw RGB frame')
                        remaining=0;break
                    chunks.append(blob);remaining-=len(blob)
                if sum(map(len,chunks))!=frame_bytes:break
                push(pixels,b''.join(chunks))
        finally:
            push(pixels,_STOP)
    a=Thread(target=stderr_reader,daemon=True)
    b=Thread(target=stdout_reader,daemon=True)
    a.start();b.start()
    started=time.monotonic()
    try:
        pixels_done=pts_done=False
        emitted=0
        # This is a generator: each decoded frame is consumed before the next.
        while True:
            if cancelled is not None and cancelled.cancelled:
                raise MediaError('Cancelled',code='Cancelled')
            if errors:raise MediaError(errors[0],code=errors[0].split(':')[0])
            if time.monotonic()-started>=timeout:raise MediaError('Timeout',code='Timeout')
            if not pts_done:
                try:
                    item=pts_meta.get(timeout=.05)
                    if item is _STOP:pts_done=True
                    else:
                        try:
                            payload=pixels.get(timeout=.2)
                        except Empty:
                            # Metadata can lead pixels; try on following iterations.
                            while True:
                                if errors:raise MediaError(errors[0],code=errors[0].split(':')[0])
                                if time.monotonic()-started>=timeout:raise MediaError('Timeout',code='Timeout')
                                if cancelled is not None and cancelled.cancelled:
                                    raise MediaError('Cancelled',code='Cancelled')
                                try:payload=pixels.get(timeout=.05);break
                                except Empty:continue
                        if payload is _STOP:
                            raise MediaError('DecodeFailed: frame count mismatch',code='DecodeFailed')
                        emitted+=1
                        yield item,payload
                except Empty:pass
            if pts_done:
                # The raw decoder must have exactly the same ordinal count.
                try:
                    tail=pixels.get(timeout=.5)
                except Empty:
                    if proc.poll() is None:continue
                    raise MediaError('DecodeFailed: raw reader did not complete',code='DecodeFailed')
                if tail is not _STOP:
                    raise MediaError('DecodeFailed: unexpected extra raw frame',code='DecodeFailed')
                break
        if errors:raise MediaError(errors[0],code=errors[0].split(':')[0])
        proc.wait(timeout=max(1,timeout-(time.monotonic()-started)))
        if proc.returncode!=0:
            raise MediaError('DecodeFailed: FFmpeg process error '+str(list(recent)),code='DecodeFailed')
        if emitted!=audits['selected'] or audits['frames']<emitted:
            raise MediaError('DecodeFailed: raw frame/PTS count mismatch',code='DecodeFailed')
    finally:
        ended.set()
        try:
            _kill(proc)
        finally:
            a.join(timeout=2);b.join(timeout=2)
            proc.stdout.close();proc.stderr.close()


def sample_stream(source:SourceRef,cache_root:Path,*,fps:Fraction=Fraction(1),
                  cancelled=None,timeout=120,progress=None,profile=None,decode_options=None,cache_owner=None):
    """Select bucket-first frames, 1 or 0.5 fps, preserving source PTS."""
    fps=Fraction(fps)
    if fps not in (Fraction(1),Fraction(1,2)):
        raise ValueError('sampling rate must be 1 or 0.5 fps')
    tb,origin=_source_info(source)
    period=1/fps
    numerator=tb.numerator*period.denominator
    denominator=tb.denominator*period.numerator
    if max(abs(origin),abs(numerator),abs(denominator))>2**53:
        raise MediaError('InvalidTiming: select exceeds exact arithmetic envelope',code='InvalidTiming')
    # prev_selected_pts is available in supported FFmpeg select versions.
    bucket=lambda x:f'floor(({x}-({origin}))*{numerator}/{denominator})'
    expr=f'isnan(prev_selected_pts)+gt({bucket("pts")},{bucket("prev_selected_pts")})'
    info=dict(source.metadata)
    pipe=build_display_pipeline(
        width=source.width,height=source.height,
        sar=source.transform.sample_aspect_ratio,rotation=source.transform.rotation,
        color_matrix=info.get('color_matrix'),color_range=info.get('color_range'),
        transfer=info.get('color_transfer'),pixel_format=info.get('pixel_format','yuv420p'))
    vf=f'showinfo@audit,select={expr!r},showinfo@sample,{pipe.cache_filter}'
    if not source_matches(source):raise MediaError('SourceChanged',code='SourceChanged')
    from .profiling import measured
    samples=[]
    if progress:progress('sampling',None,None)
    with CacheSession(cache_root, auto_prune=True, discard_on_error=True) as session:
        prior=-1
        decoded=_decode_stream(source,vf,pipe.cache_width,pipe.cache_height,
                               timeout=timeout,cancelled=cancelled,decode_options=decode_options)
        def observed():
            try:
                while True:
                    with measured(profile,'decode_wait'):
                        try:item=next(decoded)
                        except StopIteration:return
                    yield item
            finally:decoded.close()
        for index,(pts,data) in enumerate(observed()):
            grid=(pts-origin)*numerator//denominator
            if grid<=prior or pts<origin:
                raise MediaError('InvalidTiming: wrong sample grid',code='InvalidTiming')
            prior=grid
            with measured(profile,'jpeg_encode'):
                rgb=Image.frombytes('RGB',(pipe.cache_width,pipe.cache_height),data)
                with io.BytesIO() as file:
                    rgb.save(file,format='JPEG',quality=90)
                    jpeg=file.getvalue()
            with measured(profile,'cache_write'):
                path=session.write_jpeg(index,jpeg)
            if progress and index%16==0:progress('sampling',None,None)
            samples.append(Sample(
                sample_id=str(uuid4()),grid_index=grid,source_pts=pts,
                time_base=tb,nominal_time=grid*period,cache_path=str(path),
                width=pipe.cache_width,height=pipe.cache_height,pts_origin=origin))
        if not samples:
            raise MediaError('InvalidTiming: empty decoded video',code='InvalidTiming')
        if not source_matches(source):raise MediaError('SourceChanged',code='SourceChanged')
        session.complete()
        if cache_owner is not None:
            cache_owner(session.retain())
        return tuple(samples),session.directory


def extract_selected(source:SourceRef,pages,output_root:Path,*,cancelled=None,roi=None,progress=None,decode_options=None):
    """Decode requested integer PTS exactly; never substitute adjacent frames."""
    tb,origin=_source_info(source)
    decode_options={'backend':'cpu-metadata','threads':0} if decode_options is None else decode_options
    info=dict(source.metadata)
    pipe=build_display_pipeline(width=source.width,height=source.height,
        sar=source.transform.sample_aspect_ratio,rotation=source.transform.rotation,
        color_matrix=info.get('color_matrix'),color_range=info.get('color_range'),
        transfer=info.get('color_transfer'),pixel_format=info.get('pixel_format','yuv420p'))
    output_root=Path(output_root)
    output_root.mkdir(parents=True,exist_ok=True)
    result=[]
    for index,requested in enumerate(pages):
        if progress:progress('extracting',index,len(pages))
        pts=requested.source_pts if hasattr(requested,'source_pts') else int(requested)
        if pts<origin:raise MediaError('DecodeFailed: PTS precedes origin',code='DecodeFailed')
        # Select by exact decoded PTS. No nominal seconds or OpenCV seek used.
        vf=f"showinfo@audit,select='gte(pts,{pts})',showinfo@sample,{pipe.full_filter}"
        if not source_matches(source):raise MediaError('SourceChanged',code='SourceChanged')
        started=time.monotonic()
        # Input seek decodes from the nearest preceding keyframe. Recheck exact
        # source PTS after decode; a missed target retries once from the origin.
        target_seconds=pts*tb
        origin_seconds=origin*tb
        seeks=(max(origin_seconds,target_seconds-Fraction(2,1)),None)
        payload=None
        for attempt,seek in enumerate(seeks):
            remaining=120-(time.monotonic()-started)
            if remaining<=0:raise MediaError('Timeout',code='Timeout')
            decoded = _decode_stream(source,vf,pipe.transform.display_width,
                                     pipe.transform.display_height,
                                     timeout=remaining,cancelled=cancelled,seek=seek,frame_limit=2,decode_options=decode_options)
            try:
                try:
                    actual, image_data = next(decoded)
                except StopIteration:
                    if attempt==0:continue
                    raise MediaError('DecodeFailed: selected PTS missing',code='DecodeFailed')
                if actual != pts:
                    if attempt==0:continue
                    raise MediaError('DecodeFailed: selected PTS missing',code='DecodeFailed')
                try:
                    following,_ = next(decoded)
                except StopIteration:
                    pass
                else:
                    if following == pts:
                        raise MediaError('DecodeFailed: duplicated selected PTS',code='DecodeFailed')
                payload=image_data
                break
            finally:
                decoded.close()
        if payload is None:raise MediaError('DecodeFailed: selected PTS missing',code='DecodeFailed')
        rgb=Image.frombytes('RGB',(pipe.transform.display_width,pipe.transform.display_height),payload)
        if roi is not None:
            if roi.x+roi.width>rgb.width or roi.y+roi.height>rgb.height:
                raise MediaError('DecodeFailed: invalid ROI',code='DecodeFailed')
            rgb=rgb.crop((roi.x,roi.y,roi.x+roi.width,roi.y+roi.height))
        path=output_root/f'page_{index:06d}.png'
        rgb.save(path)
        result.append(path)
    if not source_matches(source):raise MediaError('SourceChanged',code='SourceChanged')
    if progress:progress('extracting',len(pages),len(pages))
    return tuple(result)
