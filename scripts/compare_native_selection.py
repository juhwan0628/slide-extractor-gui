"""M7 native all/half comparison; provisional one-run research evidence."""
import hashlib,json,tempfile,time
from pathlib import Path
from slide_core.media import probe_source
from slide_core.preparation import prepare_samples
from slide_core.analysis import analyze_project
from slide_core.config import AnalysisSettings
ROOT=Path('/home/ubuntu/workspace/01_lecture/slide-extractor-validation/keyframe-m4-20261012/clips')
OUT=Path('docs/milestones/Keyframe-M7-comparison.json')
results=[]
for name in ('sp','multicore','ethics'):
    source=probe_source(ROOT/(name+'.mp4'));item={'clip':name,'runs':[]}
    for policy in ('all','half'):
        with tempfile.TemporaryDirectory(prefix='m7-') as root:
            start=time.perf_counter()
            prepared=prepare_samples(source,root,backend='native-idr',selection_policy=policy)
            prep=time.perf_counter()-start
            try:
                start=time.perf_counter()
                project,result=analyze_project(source,AnalysisSettings(roi_mode='full'),root,prepared=prepared)
                detect=time.perf_counter()-start
                item['runs'].append({'policy':prepared.selection_policy,'backend':prepared.decoder_backend,
                    'prepare_s':prep,'detect_s':detect,'total_s':prep+detect,'frames':len(prepared.samples),
                    'pages':len(project.segments),'pts':[s.source_pts for s in prepared.samples],
                    'jpeg_hashes':[hashlib.sha256(Path(s.cache_path).read_bytes()).hexdigest() for s in prepared.samples],
                    'transitions':[str(t.observed_time) for t in result.transitions]})
            finally:
                prepared.discard()
    a,b=item['runs']
    if (a['policy'],b['policy'])!=('all','half'):
        raise RuntimeError('Native half fell back on '+name)
    item['exact_subset_pts']=b['pts']==a['pts'][::2]
    item['exact_subset_jpeg']=b['jpeg_hashes']==a['jpeg_hashes'][::2]
    assert item['exact_subset_pts'] and item['exact_subset_jpeg']
    item['total_savings_percent']=100*(a['total_s']-b['total_s'])/a['total_s']
    for row in item['runs']:
        del row['pts'];del row['jpeg_hashes']
    results.append(item);OUT.write_text(json.dumps(results,indent=2))
    print(json.dumps(item),flush=True)
