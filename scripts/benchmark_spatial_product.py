"""Separate-process memory probes and a full-lecture analysis benchmark."""
import json,os,resource,sys,tempfile,time
from pathlib import Path
import numpy as np
from slide_core.config import SpatialConfig,AnalysisSettings,DetectorConfig
from slide_core.representatives import select_representative

def rank(n):
    frame=np.full((180,320),255,np.uint8);mask=np.ones(frame.shape,bool)
    start=time.perf_counter()
    index=select_representative(lambda i:frame,0,n,mask,SpatialConfig(),lambda:None)
    assert index==n-1
    print(json.dumps(dict(observations=n,peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,seconds=time.perf_counter()-start)))

def lecture():
    from slide_core.preparation import prepare_samples
    from slide_core.analysis import analyze_project
    from slide_core.profiling import AnalysisProfile
    os.environ['SLIDE_NATIVE_KEYFRAME_HELPER']=str(Path.cwd()/'build/native/slide-keyframe-decode')
    source=next(Path('/home/ubuntu/workspace/01_lecture/skku-lecture-downloader/downloads').glob('*SP01-S01-15*.mp4'))
    with tempfile.TemporaryDirectory(prefix='spatial-full-') as cache:
        start=time.perf_counter();prepared=prepare_samples(source,cache,backend='native-idr',selection_policy='all');prepared_s=time.perf_counter()-start
        try:
            profile=AnalysisProfile()
            project,_=analyze_project(prepared.source,AnalysisSettings(roi_mode='full',detector=DetectorConfig(algorithm='spatial-groups-v1')),cache,prepared=prepared,profile=profile)
            row=dict(source_name=source.name,prepare_s=prepared_s,observations=len(prepared.samples),pages=len(project.pages),
                peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,profile=profile.report(),
                representative_times_s=[float(project.sample_time(p.representative_sample_id)) for p in project.pages])
            Path('docs/milestones/Detector-Integration-full-lecture.json').write_text(json.dumps(row,indent=2,ensure_ascii=False)+'\n')
            print(json.dumps(row),flush=True)
        finally:prepared.discard()

if __name__=='__main__':
    if len(sys.argv)>1:rank(int(sys.argv[1]))
    else:lecture()
