"""Reproducible synthetic, limited-duration benchmark. Not a 4K/120min qualification."""
import json,time,statistics,sys
try:
    import resource
except ImportError:
    resource=None
from pathlib import Path
from slide_core.analysis import analyze_project
from slide_core.config import AnalysisSettings
from slide_core.pdf_only_export import export_pdf_only
from slide_core.config import KEYFRAME_ALGORITHM


def memory_peaks():
    """ru_maxrss is bytes on macOS, KiB on Linux, unavailable on Windows."""
    if resource is None:return None,None
    scale=1024 if sys.platform=='darwin' else 1
    return tuple(resource.getrusage(kind).ru_maxrss//scale
                 for kind in (resource.RUSAGE_SELF,resource.RUSAGE_CHILDREN))


def run(video,root,rounds=3):
    if type(rounds) is not int or rounds<1:raise ValueError("Positive rounds required")
    root=Path(root)
    data=[]
    for index in range(rounds):
        folder=root/f'round-{index}';folder.mkdir(parents=True,exist_ok=True)
        t=time.monotonic();project,_=analyze_project(video,AnalysisSettings(roi_mode='full'),folder/'cache')
        try:
            analysed=time.monotonic()-t
            t=time.monotonic();pdf=folder/'result.pdf';export_pdf_only(project,pdf)
            published=time.monotonic()-t
            parent_rss,child_rss=memory_peaks()
            data.append(dict(analyze_s=analysed,export_s=published,
                 samples=len(project.samples),pages=len(project.pages),
                 cache_bytes=sum(p.stat().st_size for p in (folder/'cache').rglob('*.jpg')),
                 pdf_bytes=pdf.stat().st_size,sampling_algorithm=KEYFRAME_ALGORITHM,
                 parent_maxrss_kib=parent_rss,
                 child_maxrss_kib=child_rss))
        finally:
            if project._cache_pin is not None:project._cache_pin.close()
    return dict(runs=data,median_analyze_s=statistics.median(x['analyze_s'] for x in data),
        median_export_s=statistics.median(x['export_s'] for x in data),
        caveat='Synthetic 4s test at 320x180; parent+child concurrent peak and 30/60/120min 1080p/4K goals NOT measured')

if __name__=='__main__':
    import sys
    source=Path(sys.argv[1]);target=Path(sys.argv[2]);target.mkdir(exist_ok=True,parents=True)
    result=run(source,target)
    print(json.dumps(result,indent=2))
