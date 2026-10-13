"""Generate local research evidence for owner review; never publish lecture images."""
import json,math,tempfile
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
from slide_core.preparation import prepare_samples
from slide_core.analysis import analyze_project
from slide_core.config import AnalysisSettings
ROOT=Path('/home/ubuntu/workspace/01_lecture/slide-extractor-validation/keyframe-m4-20261012/clips')
OUT=Path('/home/ubuntu/workspace/01_lecture/experiments/selective-keyframe/results/m7-review')
OUT.mkdir(parents=True,exist_ok=True)
font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',17)
for name in ('multicore','ethics'):
    images={};times={};events={}
    for policy in ('all','half'):
        with tempfile.TemporaryDirectory(prefix='m7-review-') as cache:
            prepared=prepare_samples(ROOT/(name+'.mp4'),cache,backend='native-idr',selection_policy=policy)
            try:
                project,result=analyze_project(prepared.source,AnalysisSettings(roi_mode='full'),cache,prepared=prepared)
                samples={s.sample_id:s for s in prepared.samples}
                images[policy]=[];times[policy]=[]
                for page in project.pages:
                    sample=samples[page.representative_sample_id]
                    with Image.open(sample.cache_path) as im:
                        images[policy].append(im.convert('RGB').copy())
                    times[policy].append(float(sample.actual_time))
                events[policy]=[float(t.observed_time) for t in result.transitions]
            finally:
                prepared.discard()
    def sheet(label,indices,policy):
        cols=3;tw=420;th=280
        count=len(indices);out=Image.new('RGB',(cols*tw,max(1,math.ceil(count/cols))*th+45),'#eeeeee')
        draw=ImageDraw.Draw(out);draw.text((10,8),f'{name} {label}: {count} candidates',fill='black',font=font)
        for pos,index in enumerate(indices):
            im=images[policy][index].copy();im.thumbnail((410,235))
            x=pos%cols*tw+5;y=pos//cols*th+45;out.paste(im,(x,y))
            draw.text((x,y+240),f'page {index+1} / representative {times[policy][index]:.2f}s',fill='black',font=font)
        path=OUT/f'{name}-{label}.jpg';out.save(path,quality=90)
        return str(path)
    used=set()
    for b in events['half']:
        matches=[(abs(a-b),i) for i,a in enumerate(events['all']) if i not in used and abs(a-b)<=2]
        if matches:used.add(min(matches)[1])
    unmatched=[i+1 for i in range(len(events['all'])) if i not in used]
    files=[sheet('all',list(range(len(images['all']))),'all'),
           sheet('half',list(range(len(images['half']))),'half'),
           sheet('full-only',unmatched,'all')]
    report={'clip':name,'all_pages':len(images['all']),'half_pages':len(images['half']),
        'matching_rule':'greedy one-to-one transition agreement within 2 seconds; not ground-truth recall',
        'full_only_page_numbers':[i+1 for i in unmatched],'files':files,
        'all_representative_times':times['all'],'half_representative_times':times['half']}
    (OUT/f'{name}-review.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report),flush=True)
