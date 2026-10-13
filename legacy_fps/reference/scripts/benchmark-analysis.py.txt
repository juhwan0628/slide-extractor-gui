"""Run the real analysis path on one video; no automatic backend change."""
import argparse,json,sys,tempfile,platform,subprocess,time
from pathlib import Path
from uuid import uuid4
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from slide_core.analysis import analyze_project
from slide_core.config import AnalysisSettings
from slide_core.profiling import AnalysisProfile
from slide_core.media import probe_source
from slide_core.tools import executable
from PIL import Image
import numpy as np

def signature(project):
    lookup={s.sample_id:s.source_pts for s in project.samples}
    return {'sample_pts':[s.source_pts for s in project.samples],
            'page_pts':[lookup[p.representative_sample_id] for p in project.pages],
            'segments':[(float(x.start_time),float(x.end_time)) for x in project.segments]}

def compare(a,b):
    left,right=signature(a),signature(b)
    result={key+'_equal':left[key]==right[key] for key in left}
    result['pixel_comparison']='not_run_pts_mismatch'
    if result['sample_pts_equal']:
        means=[];maximum=0
        for x,y in zip(a.samples,b.samples,strict=True):
            with Image.open(x.cache_path) as image:xx=np.asarray(image.convert('RGB'),dtype=np.int16)
            with Image.open(y.cache_path) as image:yy=np.asarray(image.convert('RGB'),dtype=np.int16)
            if xx.shape!=yy.shape:
                result['pixel_comparison']='dimensions_mismatch';return result
            delta=np.abs(xx-yy);means.append(float(delta.mean()));maximum=max(maximum,int(delta.max()))
        result.update(pixel_comparison='completed',jpeg_rgb_mean_absolute_difference=float(np.mean(means)),
                      jpeg_rgb_max_absolute_difference=maximum)
    return result

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('video',nargs='?')
    parser.add_argument('--cpu-threads',nargs='+',type=int,default=[0])
    parser.add_argument('--fps',type=float,choices=[.5,1.],default=.5)
    args=parser.parse_args()
    if not args.video:
        from PySide6.QtWidgets import QApplication,QFileDialog
        app=QApplication.instance() or QApplication([])
        args.video,_=QFileDialog.getOpenFileName(None,'Choose the same lecture video for CPU / VideoToolbox comparison')
        if not args.video:return 0
    source=probe_source(Path(args.video))
    ffmpeg=executable('ffmpeg')
    builds=subprocess.run([ffmpeg,'-hide_banner','-hwaccels'],capture_output=True,text=True,timeout=10)
    version=subprocess.run([ffmpeg,'-version'],capture_output=True,text=True,timeout=10).stdout.splitlines()[0]
    report={'schema_version':1,'platform':platform.system(),'ffmpeg_version':version,'runs':[],
            'settings':{'fps':args.fps,'roi_mode':'auto'},
            'note':'Single run per configuration, CPU first. JPEG comparisons include encoding quantization; native backend speed/precision require this local run.'}
    configs=[('cpu',n) for n in args.cpu_threads]+[('cpu-metadata',0),('videotoolbox',0),('videotoolbox-select',0)]
    baseline=None
    with tempfile.TemporaryDirectory(prefix='slide-decoder-benchmark-') as temp:
        for backend,threads in configs:
            label=backend+('-auto' if not threads else '-'+str(threads))
            print('Running',label,'...',flush=True)
            if backend.startswith('videotoolbox') and (platform.system()!='Darwin' or 'videotoolbox' not in builds.stdout.split()):
                report['runs'].append({'label':label,'status':'unavailable'});print('VideoToolbox unavailable on this build/platform',flush=True);continue
            profile=AnalysisProfile()
            try:
                project,_=analyze_project(source,AnalysisSettings(fps=args.fps,roi_mode='auto'),Path(temp)/label,profile=profile,
                    decode_options={'backend':backend,'threads':threads})
                entry={'label':label,'profile':profile.report(),'status':'success'}
                if baseline is None:baseline=project
                else:entry['comparison_with_cpu']=compare(baseline,project)
                report['runs'].append(entry)
                print(label,round(profile.report()['seconds']['total'],3),'seconds',flush=True)
            except Exception as exc:
                report['runs'].append({'label':label,'status':'failed','error_type':type(exc).__name__,
                    'error_code':getattr(exc,'code',None),'profile':profile.report()})
                print(label,'failed:',str(exc),flush=True)
    target=ROOT/'profiles'/('benchmark-'+str(uuid4())+'.json')
    target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(json.dumps(report,indent=2)+'\n')
    print('Benchmark report:',target,flush=True)
    return 0

if __name__=='__main__':raise SystemExit(main())
