"""Reproducible synthetic, limited-duration benchmark. Not a 4K/120min qualification."""
import json,time,resource,statistics,tempfile,subprocess
from pathlib import Path
from slide_core.analysis import analyze_project
from slide_core.config import AnalysisSettings
from slide_core.export_v3 import export_project


def run(video,root,rounds=3):
    data=[]
    for index in range(rounds):
        folder=root/f'round-{index}';folder.mkdir(parents=True,exist_ok=True)
        t=time.monotonic();project,_=analyze_project(video,AnalysisSettings(roi_mode='full'),folder/'cache')
        analysed=time.monotonic()-t
        t=time.monotonic();pdf,js=export_project(project,folder/'result.pdf')
        published=time.monotonic()-t
        data.append(dict(analyze_s=analysed,export_s=published,
             samples=len(project.samples),pages=len(project.pages),
             cache_bytes=sum(p.stat().st_size for p in (folder/'cache').rglob('*.jpg')),
             pdf_bytes=pdf.stat().st_size,json_bytes=js.stat().st_size,
             parent_maxrss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
             child_maxrss_kib=resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss))
    return dict(runs=data,median_analyze_s=statistics.median(x['analyze_s'] for x in data),
        median_export_s=statistics.median(x['export_s'] for x in data),
        caveat='Synthetic 4s test at 320x180; parent+child concurrent peak and 30/60/120min 1080p/4K goals NOT measured')

if __name__=='__main__':
    import sys
    source=Path(sys.argv[1]);target=Path(sys.argv[2]);target.mkdir(exist_ok=True,parents=True)
    result=run(source,target)
    print(json.dumps(result,indent=2))
