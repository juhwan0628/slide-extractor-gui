from pathlib import Path
import pytest
from pypdf import PdfReader
from slide_core.pdf_only_export import export_pdf_only
from slide_core.models import CancelToken, CancelledError
from tests.export_fixtures import make_project, extract_stub

@pytest.fixture
def project(tmp_path,monkeypatch):
    project=make_project(tmp_path)
    monkeypatch.setattr('slide_core.pdf_only_export.extract_selected',extract_stub(project))
    return project

def assert_clean(folder):
    assert not list(folder.glob('*.lock'))
    assert not list(folder.glob('.slide-pdf-*'))

def test_pdf_only_cleans_lock_after_save_and_overwrite(tmp_path,project):
    destination=tmp_path/'slides.pdf'
    for overwrite in (False,True,True):
        assert export_pdf_only(project,destination,overwrite=overwrite)==(destination,)
        assert len(PdfReader(destination).pages)==1
        assert not destination.with_suffix('.json').exists()
        assert_clean(tmp_path)

def test_pdf_only_cleans_lock_when_publication_fails(tmp_path,project,monkeypatch):
    import os
    original=os.replace
    def denied(source,destination,*args,**kwargs):
        if Path(destination)==tmp_path/'slides.pdf':raise PermissionError('injected publish failure')
        return original(source,destination,*args,**kwargs)
    monkeypatch.setattr('slide_core.pdf_only_export.os.replace',denied)
    with pytest.raises(PermissionError,match='injected publish failure'):
        export_pdf_only(project,tmp_path/'slides.pdf')
    assert not (tmp_path/'slides.pdf').exists()
    assert_clean(tmp_path)

def test_pdf_only_cleans_lock_when_cancelled_at_publication(tmp_path,project):
    token=CancelToken()
    def progress(stage,*args):
        if stage=='publishing':token.cancel()
    with pytest.raises(CancelledError):
        export_pdf_only(project,tmp_path/'slides.pdf',cancel_token=token,progress=progress)
    assert not (tmp_path/'slides.pdf').exists()
    assert_clean(tmp_path)
