"""Current exporter and GUI approval path contracts; migrated from old app."""
import os
from dataclasses import replace
from pathlib import Path
import pytest
from PySide6.QtWidgets import QApplication,QFileDialog,QMessageBox
from PySide6.QtCore import Qt
from gui.window import Window
from gui.workers import Worker
from gui.state import State
from slide_core import export_v3,pdf_only_export,export
from slide_core.models import CancelToken
from slide_core.export import OutputCollision,OutputOverwriteRequired,preflight_export,snapshot_export
from tests.export_fixtures import make_project,extract_stub

@pytest.fixture
def project(tmp_path):return make_project(tmp_path)

@pytest.fixture
def extraction(project,monkeypatch):
    calls=[];stub=extract_stub(project)
    def extract(*args,**kwargs):calls.append(args);return stub(*args,**kwargs)
    monkeypatch.setattr(export_v3,'extract_selected',extract)
    monkeypatch.setattr(pdf_only_export,'extract_selected',extract)
    return calls

@pytest.mark.parametrize('suffix',['.pdf','.json'])
@pytest.mark.parametrize('alias',['direct','symlink','hardlink','relative'])
def test_source_collision_preserves_files(project,extraction,tmp_path,suffix,alias):
    target=tmp_path/('output'+suffix);source=project.source.path
    if alias=='direct':source.rename(target);project.source=replace(project.source,path=target)
    elif alias=='symlink':
        link=tmp_path/'source-alias';link.symlink_to(source);os.link(source,target)
        project.source=replace(project.source,path=link)
    elif alias=='hardlink':os.link(source,target)
    else:
        source.rename(target);(tmp_path/'unused').mkdir()
        project.source=replace(project.source,path=tmp_path/'unused'/'..'/target.name)
    before=target.read_bytes()
    with pytest.raises(OutputCollision):export_v3.export_project(project,tmp_path/'output.PDF',overwrite=True)
    assert target.read_bytes()==before and not extraction

@pytest.mark.parametrize('leaf',['pdf','json'])
@pytest.mark.parametrize('kind',['directory','symlink','dangling'])
def test_invalid_output_leaf_rejected(project,extraction,tmp_path,leaf,kind):
    target=tmp_path/('output.'+leaf);other=tmp_path/'unrelated';other.write_bytes(b'keep')
    if kind=='directory':target.mkdir()
    else:target.symlink_to(other if kind=='symlink' else tmp_path/'missing')
    with pytest.raises(OutputCollision):export_v3.export_project(project,tmp_path/'output.pdf',overwrite=True)
    assert other.read_bytes()==b'keep' and not extraction

def test_output_pair_hardlink_rejected(project,extraction,tmp_path):
    target=tmp_path/'output.pdf';target.write_bytes(b'old pair');os.link(target,target.with_suffix('.json'))
    with pytest.raises(OutputCollision):export_v3.export_project(project,target,overwrite=True)
    assert target.read_bytes()==b'old pair' and not extraction

@pytest.mark.parametrize('existing',[('pdf',),('json',),('pdf','json')])
def test_existing_outputs_require_approval(project,extraction,tmp_path,existing):
    for ext in existing:(tmp_path/('output.'+ext)).write_bytes(b'keep')
    with pytest.raises(OutputOverwriteRequired):export_v3.export_project(project,tmp_path/'output.pdf')
    assert not extraction

@pytest.mark.parametrize('name',['output','output.txt','output.PDF','output.pdf'])
def test_normalizes_suffix_before_export(project,extraction,tmp_path,name):
    paths=export_v3.export_project(project,tmp_path/name)
    assert paths==(tmp_path/'output.pdf',tmp_path/'output.json')
    assert paths[0].read_bytes().startswith(b'%PDF')

def test_snapshot_does_not_grant_overwrite_approval(project,extraction,tmp_path):
    target=tmp_path/'output.pdf';target.write_bytes(b'old pdf');target.with_suffix('.json').write_bytes(b'old json')
    snap=snapshot_export(project.source.path,target,overwrite=True)
    with pytest.raises(OutputOverwriteRequired):export_v3.export_project(project,target,snapshot=snap)
    assert target.read_bytes()==b'old pdf' and not extraction

@pytest.mark.parametrize('alias',['hardlink','symlink'])
def test_sidecar_alias_added_during_extraction_never_truncates_source(project,extraction,tmp_path,monkeypatch,alias):
    sidecar=tmp_path/'output.json';before=project.source.path.read_bytes();stub=extract_stub(project)
    def add_alias(*args,**kwargs):
        if alias=='hardlink':os.link(project.source.path,sidecar)
        else:sidecar.symlink_to(project.source.path)
        return stub(*args,**kwargs)
    monkeypatch.setattr(export_v3,'extract_selected',add_alias)
    with pytest.raises(OutputCollision):export_v3.export_project(project,tmp_path/'output.pdf')
    assert project.source.path.read_bytes()==before

@pytest.mark.parametrize('suffix',['pdf','json'])
def test_output_created_during_extraction_requires_approval(project,extraction,tmp_path,monkeypatch,suffix):
    target=tmp_path/('output.'+suffix);stub=extract_stub(project)
    def create(*args,**kwargs):target.write_bytes(b'created during export');return stub(*args,**kwargs)
    monkeypatch.setattr(export_v3,'extract_selected',create)
    with pytest.raises(OutputOverwriteRequired):export_v3.export_project(project,tmp_path/'output.pdf')
    assert target.read_bytes()==b'created during export'

def test_parent_symlink_resolves_to_source_collision(project,tmp_path):
    alias=tmp_path/'alias';alias.symlink_to(tmp_path,target_is_directory=True)
    source=tmp_path/'output.json';source.write_bytes(b'source')
    with pytest.raises(OutputCollision):preflight_export(source,alias/'output')

@pytest.mark.parametrize('paired',[False,True])
@pytest.mark.parametrize('approve',[False,True])
def test_gui_confirms_normalized_paths(project,extraction,tmp_path,monkeypatch,paired,approve):
    qt=QApplication.instance() or QApplication([]);w=Window();w.controller.project=project
    w.controller.source=project.source;w.controller.state=State.REVIEW_READY;w.json_enabled=paired
    target=tmp_path/'output.pdf';target.write_bytes(b'keep pdf');target.with_suffix('.json').write_bytes(b'keep json')
    monkeypatch.setattr(QFileDialog,'getSaveFileName',lambda *a,**k:(str(target.with_suffix('.PDF')),''))
    prompts=[];workers=[]
    def question(*args):prompts.append(args[2]);return QMessageBox.StandardButton.Yes if approve else QMessageBox.StandardButton.No
    monkeypatch.setattr(QMessageBox,'question',question)
    def start(fn,*args,**kwargs):workers.append((fn,args,kwargs));return 'export-job'
    monkeypatch.setattr(w.jobs,'start',start)
    try:
        w.export_pending();assert str(target) in prompts[0]
        assert (str(target.with_suffix('.json')) in prompts[0])==paired
        assert bool(workers)==approve
        if approve:assert workers[0][2]['overwrite'] is True
        assert target.read_bytes()==b'keep pdf'
    finally:
        if w.controller.pending_job:w.controller.fail_job(w.controller.pending_job)
        w.close()

@pytest.mark.parametrize('paired',[False,True])
def test_gui_replacement_after_yes_is_rejected(project,extraction,tmp_path,monkeypatch,paired):
    qt=QApplication.instance() or QApplication([]);w=Window();w.controller.project=project
    w.controller.source=project.source;w.controller.state=State.REVIEW_READY;w.json_enabled=paired
    target=tmp_path/'output.pdf';target.write_bytes(b'old pdf');target.with_suffix('.json').write_bytes(b'old json')
    monkeypatch.setattr(QFileDialog,'getSaveFileName',lambda *a,**k:(str(target),''))
    def approve(*args):
        changed=tmp_path/'replacement';changed.write_bytes(b'unapproved replacement');os.replace(changed,target)
        return QMessageBox.StandardButton.Yes
    monkeypatch.setattr(QMessageBox,'question',approve);errors=[]
    def start(fn,*args,**kwargs):
        kwargs.pop('_progress_enabled',None)
        try:fn(*args,cancel_token=CancelToken(),**kwargs)
        except Exception as exc:errors.append(exc)
        return 'export-job'
    monkeypatch.setattr(w.jobs,'start',start)
    try:
        w.export_pending();assert len(errors)==1 and isinstance(errors[0],OutputOverwriteRequired)
        assert target.read_bytes()==b'unapproved replacement' and not extraction
    finally:
        if w.controller.pending_job:w.controller.fail_job(w.controller.pending_job)
        w.close()

def test_real_export_worker_requires_overwrite_approval(project,extraction,tmp_path):
    qt=QApplication.instance() or QApplication([]);target=tmp_path/'output.pdf';target.write_bytes(b'old pdf')
    worker=Worker(export_v3.export_project,project,target);results=[]
    worker.outcome.connect(lambda *args:results.append(args),Qt.ConnectionType.DirectConnection);worker.run()
    assert isinstance(results[0][2],OutputOverwriteRequired)
    assert target.read_bytes()==b'old pdf' and not extraction
