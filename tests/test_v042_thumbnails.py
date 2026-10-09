"""Every page eventually gets a bounded-size thumbnail, not only nearby pages."""
import time
from dataclasses import replace
from pathlib import Path
from uuid import uuid4

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication
from slide_core.models import Project,Page
from gui.window import Window
from gui.state import State

VIDEO=Path('/tmp/slide-m1-fixtures/scene-change.mp4')

def wait(app,condition,timeout=15):
    deadline=time.monotonic()+timeout
    while time.monotonic()<deadline:
        app.processEvents()
        if condition():return
        time.sleep(.005)
    raise AssertionError('thumbnail load timed out')

def test_background_loads_all_pages_with_stable_row_heights():
    if not VIDEO.is_file():pytest.skip('Synthetic video fixture missing')
    app=QApplication.instance() or QApplication([])
    w=Window();w.show()
    try:
        w.open_source(VIDEO);wait(app,lambda:w.controller.state==State.SOURCE_READY)
        w.analyze();wait(app,lambda:w.controller.state==State.REVIEW_READY)
        old=w.controller.project
        template=old.samples[0]
        # More pages than the loader's bounded 16-item pending queue.
        samples=tuple(replace(template,sample_id=f's{i}',grid_index=i,
                              source_pts=template.source_pts+i*1000000,
                              nominal_time=template.nominal_time+i) for i in range(24))
        pages=[Page(str(uuid4()),s.sample_id,'manual',None,None,'add') for s in samples]
        project=Project(old.source,old.settings,samples,(),(),pages,
                        0,str(uuid4()),str(uuid4()))
        w.controller.project=project
        w.controller.focus_page_id=pages[0].page_id
        w.page_model.set_project(project)
        w.images.switch(project.analysis_generation)
        w._thumb_cursor=0
        w._pump_all_thumbs()
        wait(app,lambda:len(w.page_model._thumbs)==len(pages))
        assert w._thumb_cursor==24
        heights={w.page_model.data(w.page_model.index(i),Qt.ItemDataRole.SizeHintRole).height()
                 for i in range(len(pages))}
        assert heights=={92}
        assert all(w.page_model.data(w.page_model.index(i),Qt.ItemDataRole.DecorationRole)
                   is not None for i in range(len(pages)))
        assert w.images.thumbs.used <= 16*1024*1024
    finally:
        w.close();wait(app,lambda:not w.isVisible())
