"""C3 research safeguards: no semantic pointer/writing classification."""
import numpy as np
from scripts.detector_core_probe import broad_candidates

def change_mask(a,b,valid):
    return (np.abs(a.astype(np.int16)-b.astype(np.int16))>20)&valid

def group_candidates(gray,valid,candidate_indices,*,small_pixel_fraction=None):
    """Broad occurrences with retained small-change review alternatives."""
    boundaries=[0]+broad_candidates(gray,valid,pixel_fraction=.12,tile_fraction=.4)
    if small_pixel_fraction is not None:
        boundaries=sorted(set(boundaries+broad_candidates(gray,valid,pixel_fraction=small_pixel_fraction,tile_fraction=.4)))
    result=[]
    for start,end in zip(boundaries,boundaries[1:]+[len(gray)]):
        alternatives=sorted(set(i for i in candidate_indices if start<=i<end))
        if start not in alternatives: alternatives.insert(0,start)
        events=[]
        for i in range(start+1,end):
            mask=change_mask(gray[i-1],gray[i],valid)
            fraction=float(mask.sum()/valid.sum())
            if not mask.any(): continue
            # Observed reversion is evidence only, never a deletion instruction.
            returned=i+1<end and not change_mask(gray[i-1],gray[i+1],valid).any()
            events.append({'index':i,'changed_fraction':fraction,
                           'evidence':'localized_reversion' if fraction<.03 and returned else 'unresolved_change'})
        result.append({'start':start,'end_exclusive':end,'alternatives':alternatives,'events':events})
    return result

def run():
    import json
    from pathlib import Path
    baseline=json.loads(Path('docs/milestones/Detector-C1-baseline.json').read_text())
    output=[]
    for row in baseline:
        with np.load('build/detector-core/'+row['clip']+'.npz') as cache:
            for old in row['baseline']:
                stride=1 if old['policy']=='all' else 2
                gray=cache['gray'][::stride];times=cache['times'][::stride]
                indices=[int(np.argmin(abs(times-t))) for t in old['representatives']]
                groups=group_candidates(gray,cache['valid'],indices)
                for g in groups:
                    g['start_s']=float(times[g['start']])
                    g['alternative_times_s']=[float(times[i]) for i in g['alternatives']]
                    for e in g['events']:e['time_s']=float(times[e['index']])
                output.append({'clip':row['clip'],'policy':old['policy'],'baseline_pages':old['pages'],
                    'review_groups':len(groups),'alternative_count':sum(len(g['alternatives']) for g in groups),
                    'groups':groups,'baseline_representatives_retained':all(any(i in g['alternatives'] for g in groups) for i in indices)})
    Path('docs/milestones/Detector-C3-probe.json').write_text(json.dumps(output,indent=2))

if __name__=='__main__':run()
