"""Current half-default product validation against frozen all/half research."""
import json,tempfile,time
from pathlib import Path
from slide_core.preparation import prepare_samples
from slide_core.analysis import analyze_project
from slide_core.config import AnalysisSettings
from slide_core.lazy_frames import ensure_sample_image
from slide_core.editing import add_page,replace_page
from slide_core.keyframe_export import export_project
from slide_core.keyframe_json import loads


def run():
    original=Path('/home/ubuntu/workspace/01_lecture/slide-extractor-validation/keyframe-m4-20261012/clips')
    c4=json.loads(Path('docs/milestones/Detector-C4-representatives.json').read_text())
    v2=json.loads(Path('docs/milestones/Detector-Validation2.json').read_text())
    rows=[]
    for dataset,folder in [('original',original),('validation2',Path('build/detector-validation2'))]:
        for name in ('sp','multicore','ethics'):
            with tempfile.TemporaryDirectory(prefix='m8-half-') as cache:
                start=time.perf_counter();prep=prepare_samples(folder/(name+'.mp4'),cache)
                prepare_s=time.perf_counter()-start
                try:
                    jpeg_count=len(list(prep.directory.glob('*.jpg')))
                    p,_=analyze_project(prep.source,AnalysisSettings(roi_mode='full'),cache,prepared=prep)
                    times=[float(p.sample_time(x.representative_sample_id)) for x in p.pages]
                    wanted=(next(r for r in c4 if r['clip']==name and r['policy']==prep.selection_policy)['representatives'] if dataset=='original'
                        else next(policy for row in v2 if row['clip']==name for policy in row['policies'] if policy['policy']==prep.selection_policy)['representatives'])
                    assert len(times)==len(wanted) and all(abs(a-b['time_s'])<1e-5 for a,b in zip(times,wanted)),(dataset,name,times,wanted)
                    automatic=len(p.pages);lazy=None
                    if dataset=='original':
                        skipped=[s for s in p.samples if s.sample_id not in p.observation_sample_ids]
                        assert skipped and not Path(skipped[0].cache_path).exists()
                        ensure_sample_image(p,skipped[0]);added=add_page(p,skipped[0].actual_time)
                        assert added.status=='changed'
                        assert replace_page(p,added.focus_page_id,skipped[1].actual_time).status=='changed'
                        pdf,sidecar=export_project(p,Path(cache)/'edited.pdf')
                        value=loads(sidecar.read_bytes(),pdf_bytes=pdf.read_bytes())
                        assert value['schema_version']==7 and value['detector']['input_policy']=='half'
                        row=next(r for r in value['pages'] if r['page_id']==added.focus_page_id)
                        assert row['representative_timestamp_s']==float(skipped[1].actual_time)
                        lazy=dict(preview_pts=skipped[0].source_pts,edited_pts=skipped[1].source_pts,pdf_pages=value['artifact']['pdf_page_count'])
                    rows.append(dict(dataset=dataset,clip=name,policy=prep.selection_policy,backend=prep.decoder_backend,
                        indexed_keys=len(p.samples),decoded_analysis_images=len(prep.samples),initial_jpegs=jpeg_count,
                        prepare_s=prepare_s,automatic_pages=automatic,representatives_s=times,lazy_edit_export=lazy))
                    print(dataset,name,prep.selection_policy,len(prep.samples),'/',len(p.samples),'pages',automatic,flush=True)
                finally:prep.discard()
    Path('docs/milestones/Keyframe-M8-half-real-validation.json').write_text(json.dumps(rows,indent=2)+'\n')

if __name__=='__main__':run()
