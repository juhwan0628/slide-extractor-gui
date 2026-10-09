"""Bounded first-frame preparation using canonical display geometry."""
from math import floor,ceil
import numpy as np
from slide_core.display import build_display_pipeline
from slide_core.media import MediaError,source_matches,_run_process
from slide_core.models import Rect
from slide_core.roi import automatic_roi
from slide_core.tools import executable

def prepare_first_frame(source,*,cancel_token=None):
    if cancel_token is not None:cancel_token.raise_if_cancelled()
    if not source_matches(source):raise MediaError('SourceChanged',code='SourceChanged')
    meta=dict(source.metadata)
    pipe=build_display_pipeline(width=source.width,height=source.height,
        sar=source.transform.sample_aspect_ratio,rotation=source.transform.rotation,
        color_matrix=meta.get('color_matrix'),color_range=meta.get('color_range'),
        transfer=meta.get('color_transfer'),pixel_format=meta.get('pixel_format','yuv420p'))
    cmd=[executable('ffmpeg'),'-hide_banner','-loglevel','error','-nostdin',
         '-noautorotate','-i',str(source.path),'-map',f'0:{source.stream_index}',
         '-an','-sn','-dn','-vf',pipe.cache_filter,
         '-frames:v','1','-pix_fmt','rgb24','-f','rawvideo','pipe:1']
    try:
        result=_run_process(cmd,tool='ffmpeg',phase='first_frame',timeout=20,
                            cancel_token=cancel_token,binary_stdout=True)
    except MediaError as exc:
        if exc.code=='Timeout':raise MediaError('FirstFrameTimeout',code='FirstFrameTimeout') from exc
        raise
    if result.returncode!=0 or len(result.stdout)!=pipe.cache_width*pipe.cache_height*3:
        raise MediaError('Unable to decode first frame',code='FirstFrameDecodeFailed')
    if cancel_token is not None:cancel_token.raise_if_cancelled()
    if not source_matches(source):raise MediaError('SourceChanged',code='SourceChanged')
    rgb=np.frombuffer(result.stdout,dtype=np.uint8).reshape(pipe.cache_height,pipe.cache_width,3)
    suggestion,warning=automatic_roi([rgb])
    dw,dh=source.transform.display_width,source.transform.display_height
    x=floor(suggestion.x*dw/pipe.cache_width);y=floor(suggestion.y*dh/pipe.cache_height)
    right=ceil((suggestion.x+suggestion.width)*dw/pipe.cache_width)
    bottom=ceil((suggestion.y+suggestion.height)*dh/pipe.cache_height)
    return result.stdout,pipe.cache_width,pipe.cache_height,Rect(x,y,min(dw,right)-x,min(dh,bottom)-y),warning
