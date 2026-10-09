from pathlib import Path
import hashlib,json
import pytest
from PIL import Image
from pypdf import PdfReader
from slide_core.analysis import analyze_project
from slide_core.config import AnalysisSettings
from slide_core.models import Rect
from slide_core.export_v3 import export_project
from slide_core.export import OutputOverwriteRequired,RecoveryRequired
from slide_core.timeline_json import loads
from slide_core.editing import add_page,delete_page,replace_page
from tests.test_sampling import make_video

def prepare(tmp_path, settings=None):
    video=make_video(tmp_path/'synthetic.mp4',duration=4,fps=4)
    project,_=analyze_project(video, settings or AnalysisSettings(roi_mode='full'), tmp_path/'cache')
    return video,project

def inspect(pdf,json_path):
    pdf_raw=pdf.read_bytes()
    payload=loads(json_path.read_bytes(),pdf_bytes=pdf_raw)
    assert PdfReader(pdf).metadata.subject.endswith(payload['artifact']['export_id'])
    assert len(PdfReader(pdf).pages)==len(payload['pages'])
    assert payload['artifact']['pdf_sha256']==hashlib.sha256(pdf_raw).hexdigest()
    return payload

def test_roundtrip_m5_real_video(tmp_path):
    video,project=prepare(tmp_path)
    before=video.path.read_bytes()
    out,side=export_project(project,tmp_path/'lecture.slides.pdf')
    value=inspect(out,side)
    assert value['schema_version']==3
    assert len(value['pages'])==len(project.pages)
    assert video.path.read_bytes()==before
    assert not list(tmp_path.glob('.slide-export-*.journal.json'))

def test_manual_edit_keeps_ids_and_order(tmp_path):
    _,project=prepare(tmp_path)
    page=project.pages[0]
    result=replace_page(project,page.page_id,project.samples[1].actual_time)
    assert result.status=='changed'
    new=add_page(project,project.samples[-1].actual_time)
    assert new.status in ('changed','no_op')
    out,side=export_project(project,tmp_path/'edit.pdf')
    value=inspect(out,side)
    assert value['artifact']['project_revision']==project.revision
    assert [p['page_id'] for p in value['pages']]==[p.page_id for p in project.pages]
    assert len(value['pages'])==len(project.pages)

def test_odd_roi_mask_and_full_frame_crop(tmp_path):
    settings=AnalysisSettings(roi_mode='manual',effective_roi=Rect(3,5,77,43),
                               masks=(Rect(5,7,7,7),))
    _,project=prepare(tmp_path,settings)
    out,side=export_project(project,tmp_path/'roi.pdf')
    value=inspect(out,side)
    for page in PdfReader(out).pages:
        assert (int(page.mediabox.width),int(page.mediabox.height))==(77,43)
    assert value['ignore_masks'][0]['width']==7

def test_overwrite_requires_approval(tmp_path):
    _,project=prepare(tmp_path)
    first=export_project(project,tmp_path/'out.pdf')
    original=(first[0].read_bytes(),first[1].read_bytes())
    with pytest.raises(OutputOverwriteRequired):
        export_project(project,tmp_path/'out.pdf')
    assert (first[0].read_bytes(),first[1].read_bytes())==original
    second=export_project(project,tmp_path/'out.pdf',overwrite=True)
    assert inspect(*second)['artifact']['export_id']!=json.loads(original[1])['artifact']['export_id']

def test_changed_source_blocks_write(tmp_path):
    video,project=prepare(tmp_path)
    video.path.write_bytes(video.path.read_bytes()+b'added')
    with pytest.raises(Exception,match='SourceChanged'):
        export_project(project,tmp_path/'cannot.pdf')
    assert not (tmp_path/'cannot.pdf').exists()

def test_empty_pages_and_missing_cache_or_frame_fails_safe(tmp_path,monkeypatch):
    _,project=prepare(tmp_path)
    old=project.pages.copy();project.pages=[]
    with pytest.raises(ValueError):export_project(project,tmp_path/'empty.pdf')
    project.pages=old
    from slide_core import export_v3
    def missing(*a,**kw):return []
    monkeypatch.setattr(export_v3,'extract_selected',missing)
    with pytest.raises(ValueError,match='count mismatch'):
        export_project(project,tmp_path/'bad.pdf')
    assert not (tmp_path/'bad.pdf').exists()

def test_failed_staging_preserves_original_pair(tmp_path,monkeypatch):
    _,project=prepare(tmp_path)
    out,js=export_project(project,tmp_path/'out.pdf')
    previous=out.read_bytes(),js.read_bytes()
    from slide_core import export_v3
    def fail(*a,**kw):raise OSError('injected out of space')
    monkeypatch.setattr(export_v3.ExportTransaction,'prepare',fail)
    with pytest.raises(OSError,match='out of space'):
        export_project(project,tmp_path/'out.pdf',overwrite=True)
    assert (out.read_bytes(),js.read_bytes())==previous


def test_missing_cached_representative_blocks_export(tmp_path):
    _,project=prepare(tmp_path)
    sid=project.pages[0].representative_sample_id
    sample=next(s for s in project.samples if s.sample_id==sid)
    Path(sample.cache_path).write_bytes(b'broken jpeg')
    with pytest.raises(Exception,match='CacheUnavailable'):
        export_project(project,tmp_path/'cachebroken.pdf')
    assert not (tmp_path/'cachebroken.pdf').exists()
