from uuid import uuid4
from fractions import Fraction
from PySide6.QtWidgets import QApplication
from slide_core.models import Project,SourceRef,DisplayTransform,Sample,Page
from gui.page_model import PageModel
from gui.state import Controller,State
from slide_core.editing import replace_page,delete_page

def create(tmp_path):
    samples=tuple(Sample(str(uuid4()),i,i,Fraction(1),Fraction(i),str(i),80,60) for i in range(4))
    source=SourceRef(tmp_path/'video.mp4',100,1,0,80,60,DisplayTransform(80,60))
    pages=[Page(str(uuid4()),samples[i].sample_id,'manual',None,None,'add') for i in (0,2)]
    return Project(source,samples=samples,pages=pages)

def test_incremental_model_insert_remove_move(tmp_path):
    app=QApplication.instance() or QApplication([])
    p=create(tmp_path);m=PageModel();m.set_project(p)
    first=p.pages[0].page_id;old=[x.page_id for x in p.pages]
    result=replace_page(p,first,3)
    m.sync(old)
    assert m.rowCount()==2 and m.data(m.index(1),m.PageId)==first
    old=[x.page_id for x in p.pages]
    delete_page(p,first);m.sync(old)
    assert m.rowCount()==1

def test_focus_is_not_changed_by_active_playback(tmp_path):
    p=create(tmp_path);c=Controller(project=p,source=p.source,state=State.REVIEW_READY)
    c.focus_page_id=p.pages[0].page_id;c.active_page_id=p.pages[1].page_id
    assert c.focus_page_id!=c.active_page_id


def test_five_hundred_pages_have_bounded_model_rows(tmp_path):
    app=QApplication.instance() or QApplication([])
    samples=tuple(Sample(str(uuid4()),i,i,Fraction(1),Fraction(i),str(i),80,60) for i in range(500))
    source=SourceRef(tmp_path/'video.mp4',1000,1,0,80,60,DisplayTransform(80,60))
    pages=[Page(str(uuid4()),s.sample_id,'auto',None,None,'auto') for s in samples]
    project=Project(source,samples=samples,pages=pages)
    model=PageModel();model.set_project(project)
    assert model.rowCount()==500
    assert model.data(model.index(499),model.SampleId)==samples[-1].sample_id
    old=[p.page_id for p in project.pages]
    delete_page(project,pages[250].page_id)
    model.sync(old)
    assert model.rowCount()==499
    assert model.data(model.index(250),model.PageId)==pages[251].page_id
