"""Build reproducible research cache and baseline evidence; no detector mutation."""
import json,hashlib,tempfile,time
from pathlib import Path
from dataclasses import asdict
from fractions import Fraction
import numpy as np
from slide_core.preparation import prepare_samples
from slide_core.analysis import _resolve_roi,_prepared
from slide_core.config import AnalysisSettings,DetectorConfig
from slide_core.transitions import streaming_detect
from slide_core.compare import local_change_metrics
ROOT=Path('/home/ubuntu/workspace/01_lecture/slide-extractor-validation/keyframe-m4-20261012/clips')
OUT=Path('build/detector-core');OUT.mkdir(parents=True,exist_ok=True)
report=[]
for name in ('sp','multicore','ethics'):
 with tempfile.TemporaryDirectory(prefix='core-evidence-') as cache:
  p=prepare_samples(ROOT/(name+'.mp4'),cache,backend='native-idr')
  try:
   _,region=_resolve_roi(p.samples,AnalysisSettings(roi_mode='full'),p.source)
   gray=np.stack(list(_prepared(p.samples,region)))
   pts=np.asarray([s.source_pts for s in p.samples],dtype=np.int64)
   times=np.asarray([float(s.actual_time) for s in p.samples])
   np.savez_compressed(OUT/(name+'.npz'),gray=gray,pts=pts,times=times,valid=region.valid)
   item={'clip':name,'source_sha256':hashlib.sha256(ROOT.joinpath(name+'.mp4').read_bytes()).hexdigest(),'shape':list(gray.shape),'baseline':[]}
   for policy,indices in [('all',list(range(len(p.samples)))),('half',list(range(0,len(p.samples),2)))]:
    samples=tuple(p.samples[i] for i in indices)
    trans,segs=streaming_detect(samples,(gray[i] for i in indices),duration=Fraction(str(dict(p.source.metadata)['duration_s'])),valid_mask=region.valid)
    sample_by_id={s.sample_id:s for s in samples}
    item['baseline'].append({'policy':policy,'pages':len(segs),'transitions':[float(t.observed_time) for t in trans],'representatives':[float(sample_by_id[s.representative_sample_id].actual_time) for s in segs]})
   if name=='ethics':
    selected=[40,51.4,56.4,74.4,79.4,81,82,82.6666667,97.6666667]
    nearest=[int(np.argmin(abs(times-t))) for t in selected]
    item['reference_comparisons']=[]
    for ia,ib in [(0,1),(1,2),(1,3),(1,4),(4,5),(5,6),(6,7),(7,8)]:
     a,b=nearest[ia],nearest[ib]
     metrics=asdict(local_change_metrics(gray[a],gray[b],valid_mask=region.valid))
     delta=np.abs(gray[a].astype(np.int16)-gray[b].astype(np.int16))
     changed=(delta>20)&region.valid
     # Spatial coverage over nonoverlapping cells, distinct from peak local change.
     tiles=[]
     for y in range(0,gray.shape[1],20):
      for x in range(0,gray.shape[2],20):
       mask=region.valid[y:y+20,x:x+20]
       if mask.any():tiles.append(float(changed[y:y+20,x:x+20].sum()/mask.sum()))
     metrics['changed_tile_fraction']=sum(v>=.02 for v in tiles)/len(tiles)
     item['reference_comparisons'].append({'from_s':float(times[a]),'to_s':float(times[b]),'metrics':metrics})
   report.append(item)
   print(json.dumps(item),flush=True)
  finally:p.discard()
Path('docs/milestones/Detector-C1-baseline.json').write_text(json.dumps(report,indent=2))
