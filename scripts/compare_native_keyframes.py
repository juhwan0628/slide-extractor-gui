"""Compare native all-IDR and shipped keyframe preparation on supplied videos."""
import argparse, hashlib, json, os, tempfile, time
from pathlib import Path
from slide_core.media import probe_source
from slide_core.pts import keyframe_stream, _decode_stream
from slide_core.native_keyframes import decode_native
from slide_core.display import build_display_pipeline
from slide_core.preparation import PreparedSamples
from slide_core.analysis import analyze_project
from slide_core.config import AnalysisSettings
from slide_core.profiling import AnalysisProfile

def run(paths, output):
    results=[]
    for path in paths:
        source=probe_source(path);info=dict(source.metadata)
        pipe=build_display_pipeline(width=source.width,height=source.height,
            sar=source.transform.sample_aspect_ratio,rotation=source.transform.rotation,
            color_matrix=info.get('color_matrix'),color_range=info.get('color_range'),
            transfer=info.get('color_transfer'),pixel_format=info.get('pixel_format','yuv420p'))
        hashes=[]
        for backend in ('cpu-keyframes','native-idr'):
            decoded=(_decode_stream(source,'showinfo@audit,showinfo@sample,'+pipe.cache_filter,
                        pipe.cache_width,pipe.cache_height,timeout=None,stall_timeout=120)
                     if backend=='cpu-keyframes' else decode_native(source,pipe))
            try:
                signatures=[(pts,hashlib.sha256(rgb).hexdigest()) for pts,rgb in decoded]
            finally:
                decoded.close()
            hashes.append(signatures)
        if hashes[0]!=hashes[1]:
            raise RuntimeError('Exact PTS/RGB mismatch: '+str(path))
        item={'clip':Path(path).stem,'exact_pts_rgb':True,'frames':len(hashes[0]),'runs':[]}
        for backend in ('cpu-keyframes','native-idr'):
            with tempfile.TemporaryDirectory(prefix='m6-compare-') as root:
                owners=[];profile=AnalysisProfile();start=time.perf_counter()
                samples,directory=keyframe_stream(source,Path(root),backend=backend,
                    cache_owner=owners.append,profile=profile)
                prep=time.perf_counter()-start
                prepared=PreparedSamples(source,samples,directory,Path(root),'comparison',owners[0])
                try:
                    start=time.perf_counter()
                    project,result=analyze_project(source,AnalysisSettings(roi_mode='full'),root,prepared=prepared)
                    detect=time.perf_counter()-start
                    item['runs'].append({'backend':backend,'prepare_s':prep,'detect_s':detect,
                        'pages':len(project.segments),'pts':[s.source_pts for s in samples],
                        'jpeg_sha256':[hashlib.sha256(Path(s.cache_path).read_bytes()).hexdigest() for s in samples],
                        'transitions':[str(t.observed_time) for t in result.transitions],
                        'metadata':profile.metadata})
                finally:
                    prepared.discard()
        a,b=item['runs']
        item['exact_jpeg']=a['jpeg_sha256']==b['jpeg_sha256']
        item['exact_transitions']=a['transitions']==b['transitions']
        if not item['exact_jpeg'] or not item['exact_transitions']:
            raise RuntimeError('Cache/detector mismatch: '+str(path))
        for run in item['runs']:
            del run['pts'];del run['jpeg_sha256']
        results.append(item)
        Path(output).write_text(json.dumps(results,indent=2))
        print(json.dumps(item),flush=True)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',required=True);p.add_argument('videos',nargs='+')
    args=p.parse_args();run(args.videos,args.output)
