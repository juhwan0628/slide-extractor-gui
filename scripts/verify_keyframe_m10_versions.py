"""Compare fixed detector grouping and representative content across FFmpeg 6/8.

Research QA: requires private validation clips and both locally built helpers.
Chronological groups and observation PTS must match; exact representative times
may differ with decoder/scaler pixels. Pair images are local review artifacts.
"""
import json,os,tempfile
from pathlib import Path
import numpy as np
import cv2
from PIL import Image,ImageDraw
from slide_core.preparation import prepare_samples
from slide_core.analysis import analyze_project,_resolve_roi,_prepared
from slide_core.config import AnalysisSettings,SpatialConfig
from slide_core.spatial_groups import spatial_metrics
from slide_core.representatives import select_representative
original=Path('/home/ubuntu/workspace/01_lecture/slide-extractor-validation/keyframe-m4-20261012/clips')
c4=json.loads(Path('docs/milestones/Detector-C4-representatives.json').read_text());v2=json.loads(Path('docs/milestones/Detector-Validation2.json').read_text())
rows=[];pictures=[];cfg=SpatialConfig()
for dataset,folder in [('original',original),('validation2',Path('build/detector-validation2'))]:
 for name in ('sp','multicore','ethics'):
  with tempfile.TemporaryDirectory(prefix='m10-quality-') as temp:
   preparations=[];cases=[]
   try:
    for version,helper in [('6',Path('build/native/slide-keyframe-decode')),('8',Path('vendor/approved/slide-keyframe-decode'))]:
     os.environ['SLIDE_NATIVE_KEYFRAME_HELPER']=str(helper.resolve())
     prep=prepare_samples(folder/(name+'.mp4'),Path(temp)/version);preparations.append(prep)
     assert prep.decoder_backend=='native-idr' and prep.selection_policy=='half'
     project,_=analyze_project(prep.source,AnalysisSettings(roi_mode='full'),Path(temp)/version,prepared=prep)
     _,region=_resolve_roi(prep.samples,project.settings,prep.source)
     frames=list(_prepared(prep.samples,region));positions={s.sample_id:i for i,s in enumerate(prep.samples)}
     groups=[dict(start_s=float(project.sample_time(g.first_sample_id)),end_s=float(project.sample_time(g.last_sample_id)),representative_s=float(project.sample_time(g.representative_sample_id)),start=positions[g.first_sample_id],end=positions[g.last_sample_id]+1,rep=positions[g.representative_sample_id]) for g in project.segments]
     cases.append(dict(version=version,groups=groups,frames=frames,valid=region.valid,prep=prep))
    old,new=cases
    wanted=(next(r for r in c4 if r['clip']==name and r['policy']=='half')['representatives'] if dataset=='original' else next(p for r in v2 if r['clip']==name for p in r['policies'] if p['policy']=='half')['representatives'])
    assert len(old['groups'])==len(wanted) and all(abs(g['representative_s']-w['time_s'])<1e-5 for g,w in zip(old['groups'],wanted)),'Baseline6 does not reproduce frozen references'
    assert [s.source_pts for s in old['prep'].samples]==[s.source_pts for s in new['prep'].samples]
    intervals=lambda c:[(g['start_s'],g['end_s']) for g in c['groups']]
    same_intervals=intervals(old)==intervals(new)
    out=dict(dataset=dataset,clip=name,indexed_keys=len(new['prep'].keyframe_index),observations=len(new['prep'].samples),groups_identical=same_intervals,groups=[])
    assert same_intervals,('Group interval changed',dataset,name)
    for i,(a,b) in enumerate(zip(old['groups'],new['groups'])):
     gray=np.stack(new['frames'][b['start']:b['end']]);valid=new['valid'];reference=gray.max(axis=0).astype(np.int16)
     marks=((reference[None]-gray.astype(np.int16))>cfg.pixel_delta)&valid
     supported=marks.sum(axis=0)>=min(cfg.support_samples,len(gray))
     edges=np.zeros_like(gray,dtype=bool)
     edges[:,:,1:] |= np.abs(np.diff(gray.astype(np.int16),axis=2))>cfg.edge_delta
     edges[:,1:,:] |= np.abs(np.diff(gray.astype(np.int16),axis=1))>cfg.edge_delta
     edges &= valid
     core=edges.sum(axis=0)>=max(1,int(np.ceil(len(gray)*cfg.core_edge_fraction)))
     def score(idx):
      m=marks[idx-b['start']];retained=int((m&supported).sum());transient=int((m&~supported).sum())
      lost=core&~edges[idx-b['start']];tiles=set();size=cfg.tile_size
      for y in range(0,valid.shape[0],size):
       for x in range(0,valid.shape[1],size):
        mask=valid[y:y+size,x:x+size]
        if mask.any() and m[y:y+size,x:x+size].sum()/mask.sum()>=cfg.overlay_fraction and lost[y:y+size,x:x+size].sum()>=cfg.overlay_missing_edges:tiles.add((y//size,x//size))
      occluded=sum(any((y+dy,x+dx) in tiles for dy,dx in ((1,0),(-1,0),(0,1),(0,-1))) for y,x in tiles)
      return dict(retained=retained,transient=transient,occlusion_tiles=occluded,score=retained-cfg.transient_penalty*transient)
     diagnostic={};selected=select_representative(lambda j:new['frames'][j],b['start'],b['end'],valid,cfg,lambda:None,diagnostics=diagnostic)
     assert selected==b['rep']
     pixels,cells=spatial_metrics(new['frames'][a['rep']],new['frames'][b['rep']],valid,cfg)
     row=dict(start_s=b['start_s'],end_s=b['end_s'],old_s=a['representative_s'],new_s=b['representative_s'],old_score_on_v8=score(a['rep']),new_score_on_v8=score(b['rep']),new_diagnostics=diagnostic,pair_changed_fraction=pixels,pair_changed_cell_fraction=cells,pair_structural_change=bool(pixels>=cfg.changed_fraction and cells>=cfg.cell_fraction))
     def rgb(idx):
      with Image.open(new['prep'].samples[idx].cache_path) as im:return np.array(im.convert('RGB'))
     old_rgb,new_rgb=rgb(a['rep']),rgb(b['rep'])
     def red_mask(image):
      data=image.astype(np.int16);return (data[:,:,0]>80)&(data[:,:,0]-data[:,:,1]>35)&(data[:,:,0]-data[:,:,2]>35)
     red_old,red_new=red_mask(old_rgb),red_mask(new_rgb)
     retained_red=cv2.dilate(red_new.astype(np.uint8),np.ones((3,3),np.uint8)).astype(bool)
     row['old_red_pixels']=int(red_old.sum());row['red_retention_with_1px_tolerance']=float((red_old&retained_red).sum()/max(1,red_old.sum()))
     out['groups'].append(row)
     if a['representative_s']!=b['representative_s']:
      canvas=Image.new('RGB',(640,212),'white');draw=ImageDraw.Draw(canvas)
      for j,(case,index) in enumerate(((old,a['rep']),(new,b['rep']))):
       sample=case['prep'].samples[index]
       with Image.open(sample.cache_path) as im:canvas.paste(im.convert('RGB').resize((320,180)),(j*320,32))
      pair_root=Path('build/m10-review/pairs');pair_root.mkdir(parents=True,exist_ok=True)
      for label,arr in [('reference_v8',old_rgb),('selected_v8',new_rgb)]:Image.fromarray(arr).save(pair_root/f'{dataset}-{name}-{i+1}-{label}.png')
      draw.text((4,3),f'{dataset}/{name} group{i+1}: old6 {a["representative_s"]:.2f}s / new8 {b["representative_s"]:.2f}s',fill='black');pictures.append(canvas)
    assert same_intervals,('Group interval changed',dataset,name)
    assert all(not g['pair_structural_change'] for g in out['groups']),('Representative content changed structurally',dataset,name)
    assert all((-g['new_score_on_v8']['occlusion_tiles'],g['new_score_on_v8']['score'])>=(-g['old_score_on_v8']['occlusion_tiles'],g['old_score_on_v8']['score']) for g in out['groups']),('New representative has lower supported-mark score',dataset,name)
    rows.append(out);print(dataset,name,'groups_identical',same_intervals,'reps',[(g['old_s'],g['new_s'],g['pair_structural_change']) for g in out['groups']],flush=True)
   finally:
    for p in preparations:p.discard()
Path('docs/milestones/Keyframe-M10-version-quality.json').write_text(json.dumps(rows,indent=2)+'\n')
if pictures:
 Path('build/m10-review').mkdir(parents=True,exist_ok=True)
 sheet=Image.new('RGB',(1280,212*((len(pictures)+1)//2)),'white')
 for i,picture in enumerate(pictures):sheet.paste(picture,((i%2)*640,(i//2)*212))
 sheet.save('build/m10-review/representative-version-pairs.png')
print('quality rows',len(rows),'changed representative pairs',len(pictures))
