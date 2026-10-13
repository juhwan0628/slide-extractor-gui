"""Profile the keyframe-only product; historical FPS comparisons run separately."""
import argparse,json,sys,tempfile,platform,subprocess
from pathlib import Path
from uuid import uuid4
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from slide_core.analysis import analyze_project
from slide_core.config import AnalysisSettings,KEYFRAME_ALGORITHM
from slide_core.profiling import AnalysisProfile
from slide_core.media import probe_source
from slide_core.tools import executable

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('video',nargs='?')
    parser.add_argument('--rounds',type=int,default=3)
    args=parser.parse_args()
    if not 1<=args.rounds<=20:parser.error('--rounds must be between 1 and 20')
    if not args.video:
        from PySide6.QtWidgets import QApplication,QFileDialog
        app=QApplication.instance() or QApplication([])
        args.video,_=QFileDialog.getOpenFileName(None,'Choose a lecture video for keyframe analysis profiling')
        if not args.video:return 0
    source=probe_source(Path(args.video))
    version=subprocess.run([executable('ffmpeg'),'-version'],capture_output=True,text=True,check=True,timeout=10).stdout.splitlines()[0]
    report={'schema_version':1,'platform':platform.system(),'ffmpeg_version':version,
            'sampling_algorithm':KEYFRAME_ALGORITHM,'runs':[],
            'note':'Repeated keyframe-only analysis with fresh cache per run. Not a FPS/hardware comparison or full decoder CPU measurement.'}
    failed=False
    with tempfile.TemporaryDirectory(prefix='slide-keyframe-benchmark-') as temp:
        for index in range(args.rounds):
            profile=AnalysisProfile();project=None
            try:
                project,_=analyze_project(source,AnalysisSettings(),Path(temp)/str(index),profile=profile)
                entry={'status':'success','profile':profile.report()}
            except Exception as exc:
                failed=True
                entry={'status':'failed','error_type':type(exc).__name__,'error_code':getattr(exc,'code',None),'profile':profile.report()}
            finally:
                if project is not None and project._cache_pin is not None:project._cache_pin.close()
            report['runs'].append(entry)
    target=ROOT/'profiles'/('benchmark-'+str(uuid4())+'.json')
    target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(json.dumps(report,indent=2)+'\n')
    print('Benchmark report:',target,flush=True)
    return 1 if failed else 0

if __name__=='__main__':raise SystemExit(main())
