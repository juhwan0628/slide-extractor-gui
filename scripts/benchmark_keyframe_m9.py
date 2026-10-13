"""Linux/Unix serial fresh-process benchmark; no product policy overrides for auto.

PYTHONPATH=. python scripts/benchmark_keyframe_m9.py --output report.json SOURCE...
Application caches are new per run. OS page cache is uncontrolled, not cold.
RSS self/children are independent maxima, never summed as concurrent peak.
"""
import argparse
import hashlib
import json
import os
import platform
import resource
import statistics
import subprocess
import sys
import tempfile
import time
from pathlib import Path

MODES=('cpu-all','native-all','auto')

def summarize(rows):
    groups={}
    for row in rows:groups.setdefault((row['source'],row['mode']),[]).append(row)
    result=[]
    for (source,mode),values in sorted(groups.items()):
        signature=lambda r:tuple(json.dumps(r[k],sort_keys=True) for k in ('observations','indexed_keys','pages','policy','backend','representatives_s'))
        if len({signature(r) for r in values})!=1:raise ValueError(f'Non-deterministic output: {source}/{mode}')
        item={k:values[0][k] for k in ('source','mode','observations','indexed_keys','pages','policy','backend','representatives_s')}
        item['runs']=len(values)
        for key in ('total_s','prepare_s','analysis_s','jpeg_bytes','jpeg_count','self_cpu_s','child_cpu_s','self_peak_rss_kib','child_peak_rss_kib'):
            if key in values[0]:
                numbers=[r[key] for r in values]
                item[key]=dict(median=statistics.median(numbers),min=min(numbers),max=max(numbers))
        result.append(item)
    return result

def worker(source,mode):
    from slide_core.preparation import prepare_samples
    from slide_core.analysis import analyze_project
    from slide_core.config import AnalysisSettings
    from slide_core.profiling import AnalysisProfile
    settings={'cpu-all':dict(backend='cpu-keyframes',selection_policy='all'),
              'native-all':dict(backend='native-idr',selection_policy='all'),'auto':{}}[mode]
    start=time.perf_counter();before_self=resource.getrusage(resource.RUSAGE_SELF);before_child=resource.getrusage(resource.RUSAGE_CHILDREN)
    with tempfile.TemporaryDirectory(prefix='keyframe-m9-') as cache:
        preparation=AnalysisProfile();analysis=AnalysisProfile()
        prepared=prepare_samples(source,cache,profile=preparation,**settings)
        prepare_s=time.perf_counter()-start
        try:
            analysis_start=time.perf_counter()
            project,_=analyze_project(prepared.source,AnalysisSettings(roi_mode='full'),cache,prepared=prepared,profile=analysis)
            analysis_s=time.perf_counter()-analysis_start
            total_s=time.perf_counter()-start
            jpegs=list(prepared.directory.glob('*.jpg'))
            after_self=resource.getrusage(resource.RUSAGE_SELF);after_child=resource.getrusage(resource.RUSAGE_CHILDREN)
            row=dict(source=str(Path(source).resolve()),mode=mode,policy=prepared.selection_policy,backend=prepared.decoder_backend,
                prepare_s=prepare_s,analysis_s=analysis_s,total_s=total_s,
                observations=len(prepared.samples),indexed_keys=len(prepared.keyframe_index),pages=len(project.pages),
                jpeg_count=len(jpegs),jpeg_bytes=sum(p.stat().st_size for p in jpegs),
                self_cpu_s=after_self.ru_utime+after_self.ru_stime-before_self.ru_utime-before_self.ru_stime,
                child_cpu_s=after_child.ru_utime+after_child.ru_stime-before_child.ru_utime-before_child.ru_stime,
                self_peak_rss_kib=after_self.ru_maxrss,child_peak_rss_kib=after_child.ru_maxrss,
                preparation_profile=preparation.report(),analysis_profile=analysis.report(),
                representatives_s=[float(project.sample_time(p.representative_sample_id)) for p in project.pages])
            if mode=='native-all' and row['backend']!='native-idr':raise RuntimeError('Native baseline fell back')
            return row
        finally:prepared.discard()

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('sources',nargs='+',type=Path);parser.add_argument('--output',type=Path)
    parser.add_argument('--repetitions',type=int,default=3);parser.add_argument('--worker',choices=MODES)
    args=parser.parse_args()
    if args.worker:
        if len(args.sources)!=1:parser.error('worker takes one source')
        print(json.dumps(worker(args.sources[0],args.worker)));return
    if args.output is None or args.repetitions<3:parser.error('output required; at least three repetitions')
    args.output.parent.mkdir(parents=True,exist_ok=True)
    record=dict(schema_version=1,environment=dict(platform=platform.platform(),python=sys.version,cpu_count=os.cpu_count(),
        git_head=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
        ffmpeg=subprocess.check_output(['ffmpeg','-version'],text=True).splitlines()[0]),
        scope='Fresh worker and application cache; uncontrolled OS page cache; serial runs. Self/child RSS separate lifetime maxima in KiB (Linux). Total excludes interpreter import, cleanup, source hashing; includes probe, prepare and analysis. No GUI/export timing.',sources=[],runs=[])
    for source in args.sources:
        digest=hashlib.sha256()
        with source.open('rb') as stream:
            for chunk in iter(lambda:stream.read(1024*1024),b''):digest.update(chunk)
        record['sources'].append(dict(path=str(source.resolve()),bytes=source.stat().st_size,sha256=digest.hexdigest()))
    for repetition in range(args.repetitions):
        for source in args.sources:
            for mode in MODES[repetition%3:]+MODES[:repetition%3]:
                print(f'RUN {repetition+1} {source.name} {mode}',flush=True)
                output=subprocess.check_output([sys.executable,str(Path(__file__).resolve()),'--worker',mode,str(source.resolve())],text=True,env={**os.environ,'PYTHONPATH':str(Path(__file__).resolve().parents[1])})
                row=json.loads(output);row['repetition']=repetition+1;record['runs'].append(row)
                record['summary']=summarize(record['runs'])
                temporary=args.output.with_suffix('.tmp');temporary.write_text(json.dumps(record,indent=2,ensure_ascii=False)+'\n');temporary.replace(args.output)
                print(f"DONE prepare={row['prepare_s']:.3f}s analyze={row['analysis_s']:.3f}s total={row['total_s']:.3f}s images={row['jpeg_count']} policy={row['policy']}",flush=True)

if __name__=='__main__':main()
