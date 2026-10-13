"""Real all-keyframe index, odd-key edit and paired v6 export verification."""
import json,os,subprocess,tempfile
from pathlib import Path
from slide_core.preparation import prepare_samples
from slide_core.analysis import analyze_project
from slide_core.config import AnalysisSettings
from slide_core.editing import add_page,replace_page
from slide_core.keyframe_export import export_project
from slide_core.keyframe_json import loads
from slide_core.profiling import AnalysisProfile


def run():
    os.environ['SLIDE_NATIVE_KEYFRAME_HELPER']=str(Path.cwd()/'build/native/slide-keyframe-decode')
    source=Path('/home/ubuntu/workspace/01_lecture/slide-extractor-validation/keyframe-m4-20261012/clips/multicore.mp4')
    with tempfile.TemporaryDirectory(prefix='keyframe-m8-') as cache:
        prepared=prepare_samples(source,cache,backend='native-idr',selection_policy='all')
        try:
            profile=AnalysisProfile()
            p,_=analyze_project(prepared.source,AnalysisSettings(roi_mode='full'),cache,prepared=prepared,profile=profile)
            packets=json.loads(subprocess.check_output(['ffprobe','-v','error','-select_streams','v:0',
                '-show_packets','-show_entries','packet=pts,flags','-of','json',str(source)],timeout=60))['packets']
            keys=[int(x['pts']) for x in packets if 'K' in x['flags']]
            assert [s.source_pts for s in p.keyframe_index]==keys
            assert p.selection_policy=='all' and p.decoder_backend==prepared.decoder_backend=='native-idr'
            assert profile.report()['decoder_backend']=='native-idr' and profile.report()['selection_policy']=='all'
            before=len(p.pages)
            used={x.representative_sample_id for x in p.pages}
            odd=[s for s in p.keyframe_index if s.ordinal%2 and s.sample_id not in used]
            first,second=odd[:2]
            added=add_page(p,first.actual_time)
            assert added.status=='changed'
            assert replace_page(p,added.focus_page_id,second.actual_time).status=='changed'
            pdf,sidecar=export_project(p,Path(cache)/'edited.pdf')
            value=loads(sidecar.read_bytes(),pdf_bytes=pdf.read_bytes())
            assert value['schema_version']==6 and value['sampling']['selection_policy']=='all'
            page=next(x for x in value['pages'] if x['page_id']==added.focus_page_id)
            sample=next(x for x in value['samples'] if x['sample_id']==page['representative_sample_id'])
            assert sample['source_pts']==second.source_pts
            q,_=analyze_project(prepared.source,AnalysisSettings(roi_mode='full'),cache,previous=p)
            assert q.samples is p.samples and q.cache_generation==p.cache_generation
            row=dict(clip=source.name,source_key_packets=len(keys),indexed_keys=len(p.keyframe_index),
                selection_policy=p.selection_policy,decoder_backend=p.decoder_backend,
                automatic_pages=before,edited_pages=len(p.pages),edited_odd_ordinal=second.ordinal,
                edited_source_pts=second.source_pts,edited_time_s=float(second.actual_time),
                schema_version=value['schema_version'],pdf_page_count=value['artifact']['pdf_page_count'],
                cache_reused=profile.report()['cache_reused'],reanalysis_reused_exact_index=True)
            Path('docs/milestones/Keyframe-M8-real-validation.json').write_text(json.dumps(row,indent=2)+'\n')
            print(json.dumps(row,indent=2),flush=True)
        finally:prepared.discard()


if __name__=='__main__':run()
