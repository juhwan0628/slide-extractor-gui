import time
from pathlib import Path
from PIL import Image
from PySide6.QtWidgets import QApplication
from gui.images import ByteLRU,ImageLoader

def app():return QApplication.instance() or QApplication([])

def test_byte_budget_and_eviction():
    cache=ByteLRU(10)
    assert cache.put(1,'a',6)
    assert cache.put(2,'b',6)
    assert cache.get(1) is None and cache.used==6
    assert not cache.put(3,'too big',11)
    cache.clear();assert cache.used==0

def test_loader_async_cache_and_stale_generation(tmp_path):
    qt=app();path=tmp_path/'frame.jpg'
    Image.new('RGB',(24,16),'red').save(path)
    loader=ImageLoader();results=[]
    loader.ready.connect(lambda key,image,error:(results.append((key,image,error)),loader.ack()))
    try:
        loader.switch('generation')
        assert loader.request(('g',1),path) is None
        for _ in range(150):
            qt.processEvents()
            if results:break
            time.sleep(.01)
        assert results and results[-1][2] is None
        assert loader.cached(('g',1)) is not None
        loader.switch('next')
        assert loader.cached(('g',1)) is None
    finally:loader.stop()

def test_missing_image_error(tmp_path):
    qt=app();loader=ImageLoader();errors=[]
    loader.ready.connect(lambda key,image,error:(errors.append(error),loader.ack()))
    try:
        loader.switch('g');loader.request('bad',tmp_path/'does-not-exist.jpg')
        for _ in range(150):
            qt.processEvents()
            if errors:break
            time.sleep(.01)
        assert errors and 'Missing sample' in errors[0]
    finally:loader.stop()


def test_inflight_qimage_queue_never_exceeds_eight(tmp_path):
    qt=app();loader=ImageLoader()
    path=tmp_path/'frame.jpg';Image.new('RGB',(16,12),'green').save(path)
    try:
        loader.switch('gen')
        for i in range(16):loader.request(('gen',i),path)
        # Don't deliver Qt events: worker is limited to eight pending QImages.
        time.sleep(.15)
        assert loader._awaiting_delivery<=8
        # Shutdown must break the delivery wait without the main loop spinning.
    finally:loader.stop()
