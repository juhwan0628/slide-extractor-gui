"""Live GUI-engine transaction behavior using only synthetic media frames."""
import hashlib
import json
import os
from pathlib import Path

import pytest
from PIL import Image
from pypdf import PdfReader

from slide_core import export_v3 as engine
from tests.export_fixtures import make_project,extract_stub
from slide_core.export import ExportTransaction, RecoveryRequired, snapshot_export


@pytest.fixture
def project(tmp_path, monkeypatch):
    value=make_project(tmp_path)
    monkeypatch.setattr(engine,"extract_selected",extract_stub(value))
    return value


def test_live_export_produces_matched_pdf_json_pair_and_cleans_journal(project,tmp_path):
    output=tmp_path/"slides.pdf"
    before=project.source.path.read_bytes()
    pdf,sidecar=engine.export_project(project,output)
    payload=json.loads(sidecar.read_text())
    assert payload["schema_version"]==3
    assert payload["artifact"]["pdf_sha256"]==hashlib.sha256(pdf.read_bytes()).hexdigest()
    assert PdfReader(pdf).metadata.subject=="slide-extractor:export_id="+payload["artifact"]["export_id"]
    assert len(PdfReader(pdf).pages)==payload["artifact"]["pdf_page_count"]
    assert project.source.path.read_bytes()==before
    assert not list(tmp_path.glob(".slide-export-*"))


def test_second_export_changes_pair_together(project,tmp_path):
    output=tmp_path/"slides.pdf"
    engine.export_project(project,output)
    initial=json.loads(output.with_suffix(".json").read_text())["artifact"]["export_id"]
    engine.export_project(project,output,overwrite=True)
    updated=json.loads(output.with_suffix(".json").read_text())["artifact"]["export_id"]
    assert updated!=initial
    assert PdfReader(output).metadata.subject.endswith(updated)
    assert not list(tmp_path.glob(".slide-export-*"))


def test_output_pair_rolls_back_when_json_publication_fails(project,tmp_path,monkeypatch):
    from slide_core import export as export_core
    output=tmp_path/"slides.pdf"
    output.write_bytes(b"original pdf")
    output.with_suffix(".json").write_bytes(b"original json")
    original_link=export_core.os.link
    def fail_json(src,dst,*args,**kwargs):
        if str(dst)==str(output.with_suffix(".json")) and str(src).endswith("1.new"):
            raise OSError("injected JSON publish failure")
        return original_link(src,dst,*args,**kwargs)
    monkeypatch.setattr(export_core.os,"link",fail_json)
    with pytest.raises(OSError):
        engine.export_project(project,output,overwrite=True)
    assert output.read_bytes()==b"original pdf"
    assert output.with_suffix(".json").read_bytes()==b"original json"
    assert project.source.path.read_bytes()==b"original synthetic video"


def test_source_changed_in_extraction_not_published(project,tmp_path,monkeypatch):
    source=project.source.path
    stat=source.stat()
    img=tmp_path/"frame.png"
    def mutate(*args,**kwargs):
        source.write_bytes(b"x"*stat.st_size)
        os.utime(source,ns=(stat.st_atime_ns,stat.st_mtime_ns))
        return [img]
    monkeypatch.setattr(engine,"extract_selected",mutate)
    with pytest.raises(RuntimeError,match="SourceChanged"):
        engine.export_project(project,tmp_path/"slides.pdf")
    assert not (tmp_path/"slides.pdf").exists()
    assert not (tmp_path/"slides.json").exists()
    assert not list(tmp_path.glob(".slide-export-*"))


def test_existing_incomplete_export_requires_explicit_recovery(project,tmp_path):
    output=tmp_path/"slides.pdf"
    output.write_bytes(b"old")
    output.with_suffix(".json").write_bytes(b"old-json")
    pending=ExportTransaction(project.source.path,snapshot_export(project.source.path,output,overwrite=True))
    pending.prepare(b"unfinished-pdf",b"unfinished-json")
    assert pending.journal_path.exists()
    from slide_core.export import recover_export
    with pytest.raises(RecoveryRequired):engine.export_project(project,output,overwrite=True)
    assert output.read_bytes()==b"old"
    recover_export(tmp_path)
    engine.export_project(project,output,overwrite=True)
    obj=json.loads(output.with_suffix(".json").read_text())
    assert PdfReader(output).metadata.subject.endswith(obj["artifact"]["export_id"])
    assert not list(tmp_path.glob(".slide-export-*"))


def test_foreign_recovery_journal_blocks_export_without_mutating_files(project,tmp_path):
    output=tmp_path/"slides.pdf"
    output.write_bytes(b"previous")
    unknown=tmp_path/".slide-export-00000000-0000-4000-8000-000000000001.journal.json"
    unknown.write_bytes(b"not ours")
    with pytest.raises(RecoveryRequired):
        engine.export_project(project,output,overwrite=True)
    assert output.read_bytes()==b"previous"
    assert unknown.read_bytes()==b"not ours"
