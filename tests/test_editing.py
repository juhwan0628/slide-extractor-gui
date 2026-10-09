from fractions import Fraction
from uuid import uuid4
import pytest
from slide_core.models import SourceRef,DisplayTransform,Sample,Page,Project
from slide_core.editing import add_page,replace_page,delete_page,navigate,nearest_sample

@pytest.fixture
def project(tmp_path):
    samples=tuple(Sample(str(uuid4()),i,i,Fraction(1),Fraction(i),str(i),80,60) for i in range(5))
    source=SourceRef(tmp_path/'input.mp4',5,1,0,80,60,DisplayTransform(80,60))
    pages=[Page(str(uuid4()),samples[0].sample_id,'auto',None,None,'auto'),
           Page(str(uuid4()),samples[3].sample_id,'auto',None,None,'auto')]
    return Project(source,samples=samples,pages=pages)

def test_add_duplicate_no_revision_change(project):
    result=add_page(project,0)
    assert result.status=='no_op' and project.revision==0
    assert len(project.pages)==2

def test_replacement_collision_keeps_everything(project):
    before=(project.pages.copy(),project.revision,project.transitions)
    result=replace_page(project,project.pages[0].page_id,3)
    assert result.code=='DuplicateSample'
    assert (project.pages,project.revision,project.transitions)==before

def test_replacement_cross_order_stable_id_origin(project):
    old=project.pages[0]
    result=replace_page(project,old.page_id,4)
    assert result.status=='changed' and project.pages[-1].page_id==old.page_id
    assert project.pages[-1].origin=='auto'
    assert project.revision==1 and result.focus_page_id==old.page_id

def test_delete_focus_and_zero_pages(project):
    first=project.pages[0].page_id
    result=delete_page(project,first)
    assert result.focus_page_id==project.pages[0].page_id
    result=delete_page(project,project.pages[0].page_id)
    assert project.pages==[] and result.focus_page_id is None
    assert navigate(project,None,1) is None and project.revision==2

def test_unknown_id_and_self_replace(project):
    before=project.revision
    assert delete_page(project,str(uuid4())).code=='UnknownPage'
    assert replace_page(project,project.pages[0].page_id,0).status=='no_op'
    assert project.revision==before

def test_nearest_tie_earlier_and_clamp(project):
    assert nearest_sample(project,Fraction(3,2)).sample_id==project.samples[1].sample_id
    assert nearest_sample(project,-100).sample_id==project.samples[0].sample_id
    assert nearest_sample(project,100).sample_id==project.samples[-1].sample_id
    with pytest.raises(ValueError):nearest_sample(project,float('nan'))
    with pytest.raises(ValueError):nearest_sample(project,float('inf'))

def test_add_sorted_navigation_from_first_page(project):
    result=add_page(project,2)
    assert result.status=='changed' and project.revision==1
    assert [project.sample_time(p.representative_sample_id) for p in project.pages]==[0,2,3]
    assert navigate(project,None,1)==project.pages[1].page_id
    assert navigate(project,None,-1)==project.pages[0].page_id
