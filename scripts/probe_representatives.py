"""Reproducible C4 representative experiment; no product imports."""
import json
from pathlib import Path
import numpy as np
from scripts.detector_grouping_probe import group_candidates
from scripts.representative_probe import choose_representative

def run():
    rows=[]
    for name in ('sp','multicore','ethics'):
        with np.load('build/detector-core/'+name+'.npz') as cache:
            for policy,stride in [('all',1),('half',2)]:
                gray=cache['gray'][::stride];times=cache['times'][::stride];valid=cache['valid']
                groups=group_candidates(gray,valid,[],small_pixel_fraction=.06)
                results=[]
                for g in groups:
                    selection=choose_representative(gray[g['start']:g['end_exclusive']],valid)
                    index=g['start']+selection.pop('index')
                    results.append(dict(selection,index=index,time_s=float(times[index]),
                        start_s=float(times[g['start']]),end_s=float(times[g['end_exclusive']-1])))
                rows.append({'clip':name,'policy':policy,'representatives':results})
    Path('docs/milestones/Detector-C4-representatives.json').write_text(json.dumps(rows,indent=2)+'\n')
    for r in rows:
        print(r['clip'],r['policy'],[(round(g['time_s'],2),round(g['missing_supported_fraction'],4)) for g in r['representatives']])

if __name__=='__main__':run()
