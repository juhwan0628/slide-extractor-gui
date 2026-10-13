"""Held-out lecture windows; fixed C3/C4 settings, no retuning."""
import hashlib,json,os,subprocess,tempfile
from pathlib import Path
import numpy as np
from fractions import Fraction
from slide_core.preparation import prepare_samples
from slide_core.analysis import _resolve_roi,_prepared
from slide_core.config import AnalysisSettings
from slide_core.transitions import streaming_detect
from scripts.detector_grouping_probe import group_candidates
from scripts.representative_probe import choose_representative
from scripts.revisit_probe import link_occurrences

def run():
    os.environ['SLIDE_NATIVE_KEYFRAME_HELPER']=str(Path.cwd()/'build/native/slide-keyframe-decode')
    source_root=Path('/home/ubuntu/workspace/01_lecture/skku-lecture-downloader/downloads')
    out=Path('build/detector-heldout');out.mkdir(parents=True,exist_ok=True)
    rows=[]
    for name,pattern in [('sp','*SP02-2-S01-12*.mp4'),('multicore','*Issue (Memory)*.mp4'),('ethics','*제4장*.mp4')]:
        sources=list(source_root.glob(pattern))
        if len(sources)!=1:raise ValueError((name,sources))
        source=sources[0];clip=out/(name+'.mp4')
        subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y','-ss','600','-i',str(source),'-t','300','-map','0:v:0','-an','-c','copy','-avoid_negative_ts','make_zero',str(clip)],check=True)
        with tempfile.TemporaryDirectory(prefix='c5-heldout-') as cache:
            prepared=prepare_samples(clip,cache,backend='native-idr')
            try:
                _,region=_resolve_roi(prepared.samples,AnalysisSettings(roi_mode='full'),prepared.source)
                gray=np.stack(list(_prepared(prepared.samples,region)))
                times=np.asarray([float(s.actual_time) for s in prepared.samples])
                np.savez_compressed(out/(name+'.npz'),gray=gray,times=times,valid=region.valid)
                row={'clip':name,'source_name':source.name,'requested_source_offset_s':600,'clip_sha256':hashlib.sha256(clip.read_bytes()).hexdigest(),'policies':[]}
                for policy,stride in [('all',1),('half',2)]:
                    a=gray[::stride];t=times[::stride];samples=prepared.samples[::stride]
                    _,segments=streaming_detect(samples,iter(a),duration=Fraction(str(dict(prepared.source.metadata)['duration_s'])),valid_mask=region.valid)
                    groups=group_candidates(a,region.valid,[],small_pixel_fraction=.06)
                    reps=[];images=[]
                    for g in groups:
                        selected=choose_representative(a[g['start']:g['end_exclusive']],region.valid)
                        i=g['start']+selected.pop('index');images.append(a[i])
                        reps.append(dict(selected,index=i,time_s=float(t[i]),start_s=float(t[g['start']]),end_s=float(t[g['end_exclusive']-1])))
                    row['policies'].append({'policy':policy,'observations':len(a),'baseline_pages':len(segments),'representatives':reps,'identities':link_occurrences(images)})
                    print(name,policy,'baseline',len(segments),'groups',len(groups),flush=True)
                rows.append(row)
            finally:prepared.discard()
    Path('docs/milestones/Detector-C5-heldout.json').write_text(json.dumps(rows,indent=2,ensure_ascii=False)+'\n')

if __name__=='__main__':run()
