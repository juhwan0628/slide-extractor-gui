import os,tempfile,sys,json,inspect
from pathlib import Path
from fractions import Fraction
from slide_core.preparation import prepare_samples
from slide_core.analysis import _resolve_roi,_prepared
from slide_core.config import AnalysisSettings,DetectorConfig
from slide_core.transitions import streaming_detect,_gates
from slide_core.compare import local_change_metrics
os.environ['SLIDE_NATIVE_KEYFRAME_HELPER']=str(Path.cwd()/'build/native/slide-keyframe-decode')
lines,start=inspect.getsourcelines(streaming_detect)
testline=start+next(i for i,line in enumerate(lines) if 'if significant(anchor,current):' in line)
doneline=start+next(i for i,line in enumerate(lines) if 'previous=current' in line)
output=[]
for policy in ('all','half'):
 with tempfile.TemporaryDirectory() as cache:
  p=prepare_samples('/home/ubuntu/workspace/01_lecture/slide-extractor-validation/keyframe-m4-20261012/clips/ethics.mp4',cache,backend='native-idr',selection_policy=policy)
  try:
   _,region=_resolve_roi(p.samples,AnalysisSettings(roi_mode='full'),p.source)
   rows=[];pending={}
   def trace(frame,event,arg):
    if frame.f_code is not streaming_detect.__code__ or event!='line':return trace
    v=frame.f_locals
    if frame.f_lineno==testline:
     t=float(p.samples[v['i']].actual_time)
     if 45<=t<=85:
      cfg=v['cfg']
      def changed(a,b):
       m=local_change_metrics(a,b,tile_size=cfg.tile_size,tile_stride=cfg.tile_stride,pixel_delta=cfg.candidate_pixel_delta,valid_mask=region.valid)
       return bool(_gates(m,cfg))
      pending.update(time=t,anchor_change=changed(v['anchor'],v['current']),future_change=changed(v['anchor'],v['future']) if v['future'] is not None else False,pair_stable=not changed(v['current'],v['future']) if v['future'] is not None else False,before=len(v['transitions']))
    if frame.f_lineno==doneline and pending:
     row=dict(pending);row['committed']=len(v['transitions'])>row.pop('before');rows.append(row);pending.clear()
    return trace
   sys.settrace(trace)
   try:trans,segs=streaming_detect(p.samples,_prepared(p.samples,region),duration=Fraction(str(dict(p.source.metadata)['duration_s'])),valid_mask=region.valid,config=DetectorConfig())
   finally:sys.settrace(None)
   output.append({'policy':policy,'pages':len(segs),'rows':rows})
  finally:p.discard()
Path('docs/milestones/Keyframe-M7-ethics-trace.json').write_text(json.dumps(output,indent=2))
for item in output:
 print(json.dumps({'policy':item['policy'],'pages':item['pages'],'rows':item['rows'] if item['policy']=='half' else [r for r in item['rows'] if r['committed']]}))
