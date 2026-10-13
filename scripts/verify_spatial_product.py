"""Real analysis API parity, strict v6 sidecars and owned-cache cleanup."""
import hashlib,json,os,resource,tempfile,time
from pathlib import Path
from uuid import uuid4
from slide_core.config import AnalysisSettings,DetectorConfig
from slide_core.preparation import prepare_samples
from slide_core.analysis import analyze_project
from slide_core.models import make_export_snapshot
from slide_core.keyframe_json import payload_keyframes,dumps,loads
from slide_core.keyframe_export import export_project

def run():
    os.environ['SLIDE_NATIVE_KEYFRAME_HELPER']=str(Path.cwd()/'build/native/slide-keyframe-decode')
    original=Path('/home/ubuntu/workspace/01_lecture/slide-extractor-validation/keyframe-m4-20261012/clips')
    c4=json.loads(Path('docs/milestones/Detector-C4-representatives.json').read_text())
    old=json.loads(Path('docs/milestones/Detector-C5-heldout.json').read_text())
    new=json.loads(Path('docs/milestones/Detector-Validation2.json').read_text())
    recovery=json.loads(Path('docs/milestones/Detector-C5-sp-recovery.json').read_text())
    rows=[]
    for dataset,folder in [('original',original),('validation1',Path('build/detector-heldout')),('validation2',Path('build/detector-validation2'))]:
        for name in ('sp','multicore','ethics'):
            expected=(next(r for r in c4 if r['clip']==name and r['policy']=='all')['representatives'] if dataset=='original'
                else (recovery['representatives'] if dataset=='validation1' and name=='sp'
                else next(p for row in (old if dataset=='validation1' else new) if row['clip']==name for p in row['policies'] if p['policy']=='all')['representatives']))
            with tempfile.TemporaryDirectory(prefix='spatial-product-') as cache:
                start=time.perf_counter();prepared=prepare_samples(folder/(name+'.mp4'),cache,backend='native-idr',selection_policy='all')
                try:
                    prepared_s=time.perf_counter()-start;start=time.perf_counter()
                    settings=AnalysisSettings(roi_mode='full',detector=DetectorConfig(algorithm='spatial-groups-v1'))
                    project,_=analyze_project(prepared.source,settings,cache,prepared=prepared)
                    analysis_s=time.perf_counter()-start
                    times=[float(project.sample_time(p.representative_sample_id)) for p in project.pages]
                    wanted=[r['time_s'] for r in expected]
                    assert len(times)==len(wanted) and all(abs(a-b)<1e-5 for a,b in zip(times,wanted)),(dataset,name,times,wanted)
                    snap=make_export_snapshot(project);payload=payload_keyframes(snap,Path(cache)/'slides.pdf',hashlib.sha256(b'pdf').hexdigest(),str(uuid4()))
                    assert loads(dumps(payload))['schema_version']==6
                    if dataset=='original':
                        pdf,sidecar=export_project(project,Path(cache)/'slides.pdf')
                        assert loads(sidecar.read_bytes(),pdf_bytes=pdf.read_bytes())['artifact']['pdf_page_count']==len(project.pages)
                    rows.append(dict(dataset=dataset,clip=name,pages=len(times),representatives_s=times,prepare_s=prepared_s,analysis_s=analysis_s,peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss))
                    print(dataset,name,'API/export parity',len(times),'analysis_s',round(analysis_s,3),flush=True)
                finally:prepared.discard()
    Path('docs/milestones/Detector-Integration-parity.json').write_text(json.dumps(rows,indent=2)+'\n')

if __name__=='__main__':run()
