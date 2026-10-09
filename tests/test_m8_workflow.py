"""M8 staged UI and true ROI-cropped cached previews."""
import time
from pathlib import Path
from PIL import Image
from PySide6.QtWidgets import QApplication
from gui.window import Window
from gui.state import State
from gui.images import ImageLoader

VIDEO=Path('/tmp/slide-m1-fixtures/scene-change.mp4')
def spin(app,predicate,timeout=15):
    started=time.monotonic()
    while time.monotonic()-started<timeout:
        app.processEvents()
        if predicate():return
        time.sleep(.005)
    raise AssertionError('Qt timeout')

def test_stages_auto_review_first_selection():
    if not VIDEO.exists():return
    app=QApplication.instance() or QApplication([])
    w=Window();w.show()
    try:
        assert w.stage=='empty'
        w.open_source(VIDEO)
        spin(app,lambda:w.controller.state==State.SOURCE_READY)
        assert w.stage=='preparation'
        assert not w.page_panel.isVisible()
        w.analyze()
        assert w.stage=='analyzing'
        assert w.work_area.currentIndex()==1
        assert w.analysis_progress.isVisible()
        spin(app,lambda:w.controller.state==State.REVIEW_READY)
        assert w.stage=='review'
        assert w.work_area.currentIndex()==0
        assert w.page_panel.isVisible()
        assert not w.progress.isVisible()
        assert w.controller.focus_page_id==w.controller.project.pages[0].page_id
        assert w.page_view.currentIndex().row()==0
        first=w.controller.project.pages[0]
        first_index=next(i for i,s in enumerate(w.controller.project.samples)
                         if s.sample_id==first.representative_sample_id)
        assert w.current_index==first_index
        key=w._image_key(first_index)
        spin(app,lambda:w.images.cached(key) is not None)
        expected=w._cache_roi(w.controller.project,w.controller.project.samples[first_index])
        img=w.images.cached(key)
        assert (img.width(),img.height())==expected[2:]
        assert w._current_image.size()==img.size()
    finally:
        w.close()
        spin(app,lambda:not w.isVisible())

def test_loader_crops_before_thumb_resize(tmp_path):
    app=QApplication.instance() or QApplication([])
    path=tmp_path/'sample.jpg'
    Image.new('RGB',(100,50),'white').save(path)
    loader=ImageLoader()
    delivered=[]
    loader.ready.connect(lambda key,image,error:(delivered.append((image,error)),loader.ack()))
    try:
        loader.switch('g')
        from PySide6.QtCore import QSize
        loader.request(('g','crop'),path,kind='thumb',size=QSize(30,30),crop=(20,0,50,50))
        spin(app,lambda:bool(delivered))
        assert delivered[0][1] is None
        assert delivered[0][0].width()==30
        assert delivered[0][0].height()==30
    finally:
        loader.stop()
