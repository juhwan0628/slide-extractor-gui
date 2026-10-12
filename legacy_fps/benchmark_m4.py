"""External M4 validation worker. Never imported by the product.
Use separate --source trees for product and frozen FPS baseline.
FPS modes measure preparation/analysis only; full export is the current product.
"""
import argparse,json,os,resource,sys,time,traceback
from pathlib import Path

def worker(args):
 source=Path(args.source).resolve()
 sys.path.insert(0,str(source))
 output=Path(args.output).resolve();output.mkdir(parents=True,exist_ok=True)
 report={'status':'running','mode':args.mode,'worker_source':str(source),
         'timing_note':'Wall timings overlap: sampling includes decode_wait/JPEG/write; detection includes cache_prepare. decode_wait is pipe consumer wait, not decoder CPU. Fresh application cache; warm OS cache possible.'}
 project=None;prepared=None;task=None;decoder_module=None;original_decoder=None;decoder_commands=[]
 cpu0=resource.getrusage(resource.RUSAGE_SELF)
 child0=resource.getrusage(resource.RUSAGE_CHILDREN)
 try:
  if not (source/'slide_core'/'analysis.py').is_file():raise ValueError('Missing worker source tree')
  from slide_core.media import probe_source
  from slide_core.analysis import analyze_project
  from slide_core.config import AnalysisSettings
  from slide_core.profiling import AnalysisProfile
  from slide_core.models import CancelToken
  module_source=Path(sys.modules['slide_core.analysis'].__file__).resolve().parents[1]
  if module_source!=source:raise RuntimeError('Worker module source mismatch')
  report['runtime_module_source']=str(module_source)
  from slide_core import pts as decoder_module
  original_decoder=decoder_module._ffmpeg
  def observed_decoder(*a,**kw):
   command=original_decoder(*a,**kw);decoder_commands.append(command);return command
  decoder_module._ffmpeg=observed_decoder
  from slide_core.preparation import PreparedSamples
  from uuid import uuid4
  t=time.perf_counter();src=probe_source(Path(args.video));probe=time.perf_counter()-t
  report.update(source_fingerprint=src.fingerprint,duration_s=float(dict(src.metadata)['duration_s']),
                source_dimensions=[src.width,src.height],source_bytes=src.size_bytes)
  settings=AnalysisSettings() if args.mode=='keyframes' else AnalysisSettings(fps=float(args.mode))
  prep_profile=AnalysisProfile();analysis_profile=AnalysisProfile()
  started=time.perf_counter();wait=0
  if args.click:
   if args.mode!='keyframes':raise ValueError('Background test is current product only')
   from gui.sample_preparation import BackgroundSamples
   task=BackgroundSamples(src,output/'cache')
   report['background_producers']=1
   if args.click=='ready':
    if not task.ready.wait(3600):raise TimeoutError('Background preparation')
   clicked=time.perf_counter()
   prepared=task.wait(CancelToken());wait=time.perf_counter()-clicked
   prep_s=task.finished_at-task.started_at
  else:
   owners=[]
   if args.mode=='keyframes':
    from slide_core.pts import keyframe_stream
    samples,directory=keyframe_stream(src,output/'cache',profile=prep_profile,cache_owner=owners.append)
    prepared=PreparedSamples(src,tuple(samples),directory,output/'cache',str(uuid4()),owners[0])
   else:
    from fractions import Fraction
    from slide_core.pts import sample_stream
    samples,directory=sample_stream(src,output/'cache',fps=Fraction(args.mode),profile=prep_profile,cache_owner=owners.append,decode_options={'backend':'cpu-metadata','threads':0})
    prepared=PreparedSamples(src,float(args.mode),tuple(samples),directory,output/'cache',str(uuid4()),owners[0])
   prep_s=time.perf_counter()-started
  t=time.perf_counter()
  project,_=analyze_project(src,settings,output/'cache',prepared=prepared,profile=analysis_profile)
  analysis_s=time.perf_counter()-t
  samples=project.samples;byid={s.sample_id:s for s in samples}
  report.update(sampling_algorithm=getattr(project,'sampling_algorithm','fps-metadata'),
   sample_pts=[s.source_pts for s in samples],sample_times=[float(s.actual_time) for s in samples],
   representative_pts=[byid[p.representative_sample_id].source_pts for p in project.pages],
   representative_times=[float(byid[p.representative_sample_id].actual_time) for p in project.pages],
   transition_times=[float(t.observed_time) for t in project.transitions],
   transition_bounds=[[float(t.lower_time),float(t.upper_time)] for t in project.transitions],
   roi=vars(project.settings.effective_roi),samples=len(samples),pages=len(project.pages),
   cache_bytes=sum(Path(s.cache_path).stat().st_size for s in samples),
   preparation_profile=prep_profile.report(),analysis_profile=analysis_profile.report())
  report['decoder_invocations_before_export']=len(decoder_commands)
  report['decoder_modes_before_export']=['keyframes' if '-skip_frame' in c and 'nokey' in c else 'full' for c in decoder_commands]
  report['seconds']={'probe':probe,'preparation':prep_s,'ready_analysis':analysis_s,'cold_total':prep_s+analysis_s,'preparation_wait':wait,'click_to_result':wait+analysis_s,'export':None}
  # Retain small representative sheets privately for human inspection; no originals enter git.
  if args.sheets:
   from PIL import Image,ImageDraw
   for start in range(0,len(project.pages),40):
    batch=project.pages[start:start+40];sheet=Image.new('RGB',(1000,140*8),'#dddddd');draw=ImageDraw.Draw(sheet)
    for j,page in enumerate(batch):
     s=byid[page.representative_sample_id]
     with Image.open(s.cache_path) as im:
      im=im.copy();im.thumbnail((196,112));x=(j%5)*200;y=(j//5)*140;sheet.paste(im,(x,y))
     draw.text((x,y+114),str(start+j+1)+' @ '+str(round(float(s.actual_time),2)),fill='black')
    sheet.save(output/('sheet-'+str(start//40)+'.jpg'),quality=90)
  report['export_scope']='current-keyframe-product-only'
  if not args.no_export and args.mode=='keyframes':
   t=time.perf_counter();pdf=output/'result.pdf'
   from slide_core.keyframe_export import export_project
   events={}
   def export_progress(phase,current,total):
    if phase in ('writing','verifying','publishing') and phase not in events:events[phase]=time.perf_counter()-t
   export_project(project,pdf,progress=export_progress)
   report['json_schema']=4
   report['seconds']['export']=time.perf_counter()-t
   report['pdf_bytes']=pdf.stat().st_size
   report['export_phases']={'extract':events['writing'],'write_pdf_with_internal_verification_qpdf':events['verifying']-events['writing'],'verify':events['publishing']-events['verifying'],'publish_cleanup':report['seconds']['export']-events['publishing']}
   report['export_decoder_invocations']=len(decoder_commands)-report['decoder_invocations_before_export']
  report['status']='success'
 except BaseException as exc:
  report.update(status='failed',error_type=type(exc).__name__,error_code=getattr(exc,'code',None),error=str(exc))
  traceback.print_exc()
 finally:
  if decoder_module is not None and original_decoder is not None:decoder_module._ffmpeg=original_decoder
  if task is not None:
   task.close();report['background_done']=task.done.wait(30)
   if not report['background_done']:report.update(status='failed',error_type='TimeoutError',error='Background cleanup deadline exceeded')
   if task.cleanup_error is not None:report.update(status='failed',error='Background cleanup: '+str(task.cleanup_error))
  elif prepared is not None:
   try:prepared.discard()
   except Exception as exc:report.update(status='failed',error_type=type(exc).__name__,error='Cleanup failed: '+str(exc))
  cpu1=resource.getrusage(resource.RUSAGE_SELF);child1=resource.getrusage(resource.RUSAGE_CHILDREN)
  report['cpu_seconds']={'parent':cpu1.ru_utime+cpu1.ru_stime-cpu0.ru_utime-cpu0.ru_stime,'children':child1.ru_utime+child1.ru_stime-child0.ru_utime-child0.ru_stime}
  report['maxrss_kib']={'parent':cpu1.ru_maxrss,'largest_child':child1.ru_maxrss}
  (output/'report.json').write_text(json.dumps(report,indent=2)+'\n')
 return 0 if report['status']=='success' else 1

def main():
 p=argparse.ArgumentParser(description=__doc__)
 p.add_argument('--worker',action='store_true',required=True)
 p.add_argument('--source',required=True);p.add_argument('--video',required=True);p.add_argument('--output',required=True)
 p.add_argument('--mode',choices=['keyframes','0.5','1'],required=True)
 p.add_argument('--click',choices=['early','ready'])
 p.add_argument('--sheets',action='store_true');p.add_argument('--no-export',action='store_true')
 return worker(p.parse_args())

if __name__=='__main__':raise SystemExit(main())
