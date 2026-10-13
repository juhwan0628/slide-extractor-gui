"""Fresh windows, frozen6% pixel/30%tile/C4 ranking; revisit work deferred."""
import hashlib,json,os,subprocess,tempfile
from pathlib import Path
import numpy as np
from fractions import Fraction
from slide_core.preparation import prepare_samples
from slide_core.analysis import _resolve_roi,_prepared
from slide_core.config import AnalysisSettings
from slide_core.transitions import streaming_detect
from scripts.representative_probe import choose_representative
from scripts.detector_core_probe import broad_candidates

def run():
    os.environ['SLIDE_NATIVE_KEYFRAME_HELPER']=str(Path.cwd()/'build/native/slide-keyframe-decode')
    source_root=Path('/home/ubuntu/workspace/01_lecture/skku-lecture-downloader/downloads')
    out=Path('build/detector-validation2');out.mkdir(parents=True,exist_ok=True)
    rows=[]
    for name,pattern,offset in [('sp','*SP01-S01-15*.mp4',600),('multicore','*Issue (Memory)*.mp4',1200),('ethics','*제5장*.mp4',600)]:
        sources=list(source_root.glob(pattern))
        if len(sources)!=1:raise ValueError((name,sources))
        source=sources[0];clip=out/(name+'.mp4')
        subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y','-ss',str(offset),'-i',str(source),'-t','300','-map','0:v:0','-an','-c','copy','-avoid_negative_ts','make_zero',str(clip)],check=True)
        with tempfile.TemporaryDirectory(prefix='c5-heldout-') as cache:
            prepared=prepare_samples(clip,cache,backend='native-idr')
            try:
                _,region=_resolve_roi(prepared.samples,AnalysisSettings(roi_mode='full'),prepared.source)
                gray=np.stack(list(_prepared(prepared.samples,region)))
                times=np.asarray([float(s.actual_time) for s in prepared.samples])
                np.savez_compressed(out/(name+'.npz'),gray=gray,times=times,valid=region.valid)
                row={'clip':name,'source_name':source.name,'requested_source_offset_s':offset,'clip_sha256':hashlib.sha256(clip.read_bytes()).hexdigest(),'policies':[]}
                for policy,stride in [('all',1),('half',2)]:
                    a=gray[::stride];t=times[::stride];samples=prepared.samples[::stride]
                    _,segments=streaming_detect(samples,iter(a),duration=Fraction(str(dict(prepared.source.metadata)['duration_s'])),valid_mask=region.valid)
                    starts=[0]+broad_candidates(a,region.valid,pixel_fraction=.06,tile_fraction=.3)
                    groups=[{'start':i,'end_exclusive':j} for i,j in zip(starts,starts[1:]+[len(a)])]
                    reps=[]
                    for g in groups:
                        selected=choose_representative(a[g['start']:g['end_exclusive']],region.valid)
                        i=g['start']+selected.pop('index')
                        reps.append(dict(selected,index=i,time_s=float(t[i]),start_s=float(t[g['start']]),end_s=float(t[g['end_exclusive']-1])))
                    row['policies'].append({'policy':policy,'observations':len(a),'baseline_pages':len(segments),'representatives':reps,'baseline_representatives_s':[float(next(sample.actual_time for sample in samples if sample.sample_id==segment.representative_sample_id)) for segment in segments]})
                    print(name,policy,'baseline',len(segments),'groups',len(groups),flush=True)
                rows.append(row)
            finally:prepared.discard()
    Path('docs/milestones/Detector-Validation2.json').write_text(json.dumps(rows,indent=2,ensure_ascii=False)+'\n')

if __name__=='__main__':run()
