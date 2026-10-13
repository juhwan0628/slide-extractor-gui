from dataclasses import replace,FrozenInstanceError
from pathlib import Path
import pytest
from slide_core.analysis import analyze_project
from slide_core.config import AnalysisSettings
from slide_core.preparation import prepare_samples
from slide_core.editing import add_page,replace_page,nearest_sample
from slide_core.models import make_export_snapshot
from slide_core.keyframe_export import export_project
from slide_core.keyframe_json import loads
from tests.media_fixtures import make_scene_video


def test_all_index_exposes_odd_keys_for_editing_and_exact_export(tmp_path):
    source=make_scene_video(tmp_path/'v.mp4')
    prepared=prepare_samples(source,tmp_path/'cache')
    try:
        p,_=analyze_project(prepared.source,AnalysisSettings(roi_mode='full'),tmp_path/'cache',prepared=prepared)
        assert p.keyframe_index is prepared.samples
        assert len(p.keyframe_index)==12
        assert [s.ordinal for s in p.keyframe_index]==list(range(12))
        used={x.representative_sample_id for x in p.pages}
        candidates=[s for s in p.keyframe_index if s.ordinal%2 and s.sample_id not in used]
        first,second=candidates[:2]
        assert Path(first.cache_path).is_file() and Path(second.cache_path).is_file()
        added=add_page(p,first.actual_time)
        assert added.status=='changed'
        replaced=replace_page(p,added.focus_page_id,second.actual_time)
        assert replaced.status=='changed'
        assert p.selection_policy=='all' and p.decoder_backend==prepared.decoder_backend
        snap=make_export_snapshot(p)
        with pytest.raises(FrozenInstanceError):snap.selection_policy='half'
        pdf,sidecar=export_project(p,tmp_path/'edited.pdf')
        value=loads(sidecar.read_bytes(),pdf_bytes=pdf.read_bytes())
        assert value['sampling']['selection_policy']=='all'
        row=next(x for x in value['pages'] if x['page_id']==added.focus_page_id)
        sample=next(x for x in value['samples'] if x['sample_id']==row['representative_sample_id'])
        assert sample['source_pts']==second.source_pts
        assert row['representative_timestamp_s']==float(second.actual_time)
        assert value['artifact']['pdf_page_count']==len(p.pages)
    finally:prepared.discard()


def test_experimental_half_is_not_a_complete_edit_index(tmp_path):
    from tests.test_keyframe_json import irregular_project
    p=replace(irregular_project(tmp_path),selection_policy='half',decoder_backend='native-idr',keyframe_index_complete=False)
    with pytest.raises(ValueError,match='FullKeyframesRequired'):nearest_sample(p,0)
