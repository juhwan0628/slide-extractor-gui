"""Atomic multi-page edits preserve sample/analysis data and stable IDs."""
from fractions import Fraction
from uuid import uuid4
import pytest
from slide_core.models import Project,SourceRef,DisplayTransform,Sample,Page
from slide_core import editing

@pytest.fixture
def project(tmp_path):
    samples=tuple(Sample(str(uuid4()),i,i,Fraction(1),Fraction(i),str(i),80,60) for i in range(6))
    source=SourceRef(tmp_path/'input.mp4',100,1,0,80,60,DisplayTransform(80,60))
    return Project(source,samples=samples,pages=[Page(str(uuid4()),s.sample_id,'auto',None,None,'auto') for s in samples])

def test_merge_uses_last_timestamp_not_selection_input_order(project):
    old=tuple(project.pages);samples=project.samples;generation=project.analysis_generation
    result=editing.merge_pages(project,[old[4].page_id,old[1].page_id,old[2].page_id])
    assert result.status=='changed' and result.focus_page_id==old[4].page_id
    assert [p.page_id for p in project.pages]==[old[i].page_id for i in (0,3,4,5)]
    assert project.pages[2].representative_sample_id==old[4].representative_sample_id
    assert project.pages[2]==old[4]
    assert project.revision==1 and project.samples is samples and project.analysis_generation==generation

def test_merge_rejects_unknown_ids_without_partial_changes(project):
    old=list(project.pages)
    r=editing.merge_pages(project,[old[0].page_id,str(uuid4())])
    assert r.status=='rejected' and r.code=='UnknownPage'
    assert project.pages==old and project.revision==0

def test_empty_single_duplicate_selection_noop(project):
    old=list(project.pages)
    for ids in ([],[old[0].page_id],[old[0].page_id,old[0].page_id]):
        assert editing.merge_pages(project,ids).status=='no_op'
    assert project.pages==old and project.revision==0

def test_bulk_delete_is_one_revision_and_focuses_nearest_survivor(project):
    old=list(project.pages)
    r=editing.delete_pages(project,[p.page_id for p in old[1:4]])
    assert project.pages==[old[0],old[4],old[5]]
    assert project.revision==1 and r.focus_page_id==old[4].page_id

def test_bulk_delete_all_then_noop(project):
    assert editing.delete_pages(project,[p.page_id for p in project.pages]).focus_page_id is None
    assert project.pages==[] and project.revision==1
    assert editing.delete_pages(project,[]).status=='no_op' and project.revision==1

def test_bulk_delete_rejects_stale_selection(project):
    old=list(project.pages)
    assert editing.delete_pages(project,[old[0].page_id,str(uuid4())]).status=='rejected'
    assert project.pages==old and project.revision==0

def test_merge_preserves_exact_last_page_and_exports_matching_json(tmp_path):
    import hashlib
    from tests.test_sampling import make_video
    from slide_core.analysis import analyze_project
    from slide_core.config import AnalysisSettings
    from slide_core.export_v3 import export_project
    from slide_core.pdf_only_export import export_pdf_only
    from slide_core.timeline_json import loads
    from pypdf import PdfReader
    source=make_video(tmp_path/'synthetic.mp4',duration=6)
    project,_=analyze_project(source,AnalysisSettings(fps=1,roi_mode='full'),tmp_path/'cache')
    for sample in project.samples:editing.add_page(project,sample.actual_time)
    original=tuple(project.pages);before=hashlib.sha256(source.path.read_bytes()).hexdigest()
    editing.merge_pages(project,[p.page_id for p in original[1:5]])
    pdf,side=export_project(project,tmp_path/'merged.pdf')
    payload=loads(side.read_bytes(),pdf_bytes=pdf.read_bytes())
    expected=[original[i] for i in (0,4,5)]
    assert project.pages==expected
    assert [page['page_id'] for page in payload['pages']]==[page.page_id for page in expected]
    assert [page['representative_timestamp_s'] for page in payload['pages']]==[float(project.sample_time(page.representative_sample_id)) for page in expected]
    assert len(PdfReader(pdf).pages)==3
    export_pdf_only(project,tmp_path/'only.pdf')
    assert len(PdfReader(tmp_path/'only.pdf').pages)==3
    assert not list(tmp_path.glob('*.lock'))
    assert hashlib.sha256(source.path.read_bytes()).hexdigest()==before
