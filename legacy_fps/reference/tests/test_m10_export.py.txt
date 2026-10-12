"""M10 PDF-only default, selectable JSON formats and true transition metrics."""
import json
import time
from pathlib import Path
from PySide6.QtWidgets import QApplication
from gui.window import Window
from gui.state import State
from slide_core.simple_json import simple_timeline
from slide_core.pdf_only_export import export_pdf_only
from slide_core.export_v3 import export_project
from slide_core.timeline_json import loads
from pypdf import PdfReader

VIDEO=Path('/tmp/slide-m1-fixtures/scene-change.mp4')
def wait(app,condition,timeout=20):
    start=time.monotonic()
    while time.monotonic()-start<timeout:
        app.processEvents()
        if condition():return
        time.sleep(.005)
    raise AssertionError('GUI job timeout')

def test_pdf_only_and_simple_json(tmp_path):
    if not VIDEO.exists():return
    app=QApplication.instance() or QApplication([])
    w=Window();w.show()
    try:
        assert not w.json_enabled and w.json_format=='simple'
        w.open_source(VIDEO);wait(app,lambda:w.controller.state==State.SOURCE_READY)
        w.analyze();wait(app,lambda:w.controller.state==State.REVIEW_READY)
        p=w.controller.project
        target=tmp_path/'slides.pdf'
        result=export_pdf_only(p,target)
        assert result==(target,)
        assert len(PdfReader(target).pages)==len(p.pages)
        assert not target.with_suffix('.json').exists()
        rows=simple_timeline(p)['slides']
        assert len(rows)==len(p.pages)
        assert all(row['end']>row['start'] for row in rows)
        assert all(set(row)=={'page','start','end'} for row in rows)
        # Existing JSON must survive subsequent PDF-only overwrite.
        sidecar=target.with_suffix('.json')
        sidecar.write_text('preserve me')
        export_pdf_only(p,target,overwrite=True)
        assert sidecar.read_text()=='preserve me'
        sidecar.unlink()
        pdf,json_path=export_project(p,target,overwrite=True,sidecar_format='simple')
        data=json.loads(json_path.read_text())
        assert data==simple_timeline(p)
        assert len(PdfReader(pdf).pages)==len(p.pages)
        pdf,json_path=export_project(p,target,overwrite=True,sidecar_format='detailed')
        detailed=loads(json_path.read_bytes(),pdf_bytes=pdf.read_bytes())
        assert detailed['schema_version']==3
        for x in detailed['detected_boundaries']:
            assert any(v>0 for v in x['anchor_metrics'].values())
    finally:
        w.close();wait(app,lambda:not w.isVisible())
