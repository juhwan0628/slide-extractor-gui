"""Throwaway C2 hypothesis probe, deliberately not imported by product code."""
import json
from pathlib import Path
import numpy as np

def broad_candidates(gray,valid,*,pixel_fraction,tile_fraction,pixel_delta=20):
    if gray.ndim!=3 or gray.dtype!=np.uint8 or valid.shape!=gray.shape[1:] or valid.dtype!=bool:
        raise ValueError('Invalid grayscale observation series')
    if not valid.any() or not (0<pixel_fraction<=1 and 0<tile_fraction<=1):
        raise ValueError('Invalid mask/threshold')
    result=[]
    for i in range(1,len(gray)):
        change=(np.abs(gray[i].astype(np.int16)-gray[i-1].astype(np.int16))>pixel_delta)&valid
        fraction=float(change.sum()/valid.sum());tiles=[]
        for y in range(0,gray.shape[1],20):
            for x in range(0,gray.shape[2],20):
                mask=valid[y:y+20,x:x+20]
                if mask.any():tiles.append(change[y:y+20,x:x+20].sum()/mask.sum())
        coverage=sum(t>=.02 for t in tiles)/len(tiles)
        if fraction>=pixel_fraction and coverage>=tile_fraction:
            result.append(i)
    return result

def run():
    baseline={r['clip']:r for r in json.loads(Path('docs/milestones/Detector-C1-baseline.json').read_text())}
    output=[]
    for name in ('sp','multicore','ethics'):
        with np.load(Path('build/detector-core')/(name+'.npz')) as cache:
            for policy,stride in [('all',1),('half',2)]:
                gray=cache['gray'][::stride];times=cache['times'][::stride];valid=cache['valid']
                old=next(r for r in baseline[name]['baseline'] if r['policy']==policy)
                for pixel in (.03,.06,.12,.2):
                    for tile in (.1,.25,.4,.55):
                        indices=broad_candidates(gray,valid,pixel_fraction=pixel,tile_fraction=tile)
                        broad=[float(times[i]) for i in indices]
                        merged=sorted(set(old['transitions']+broad))
                        output.append({'clip':name,'policy':policy,'pixel_fraction':pixel,'tile_fraction':tile,
                            'baseline_pages':old['pages'],'broad_only_candidate_count':len(broad),
                            'combined_candidate_count':len(merged),'combined_candidate_page_count':len(merged)+1,
                            'broad_times':broad,
                            'ethics_brief_onset_candidate':any(80.5<=t<=81.5 for t in broad) if name=='ethics' else None})
    Path('docs/milestones/Detector-C2-probe.json').write_text(json.dumps(output,indent=2))
    for policy in ('all','half'):
        rows=[r for r in output if r['clip']=='ethics' and r['policy']==policy]
        print(policy,'settings adding brief-onset candidates (diagnostic timing)',sum(r['ethics_brief_onset_candidate'] for r in rows),'/',len(rows))
    for name in ('sp','multicore','ethics'):
        r=next(r for r in output if r['clip']==name and r['policy']=='half' and r['pixel_fraction']==.12 and r['tile_fraction']==.4)
        print(json.dumps(r))
if __name__=='__main__':run()
