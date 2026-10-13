"""C3 threshold sensitivity probe; research only."""
import json
from pathlib import Path
import numpy as np
from scripts.detector_grouping_probe import group_candidates

def run():
    output=[]
    baseline=json.loads(Path('docs/milestones/Detector-C1-baseline.json').read_text())
    for row in baseline:
        with np.load('build/detector-core/'+row['clip']+'.npz') as cache:
            for old in row['baseline']:
                stride=1 if old['policy']=='all' else 2
                gray=cache['gray'][::stride];times=cache['times'][::stride]
                indices=[int(np.argmin(abs(times-t))) for t in old['representatives']]
                for threshold in (.03,.06,.09,.12):
                    groups=group_candidates(gray,cache['valid'],indices,small_pixel_fraction=threshold)
                    output.append({'clip':row['clip'],'policy':old['policy'],
                        'small_pixel_fraction':threshold,'tile_fraction':.4,
                        'starts_s':[float(times[g['start']]) for g in groups],
                        'alternative_times_s':[[float(times[i]) for i in g['alternatives']] for g in groups]})
    Path('docs/milestones/Detector-C3-boundary-probe.json').write_text(json.dumps(output,indent=2)+'\n')

if __name__=='__main__':run()
