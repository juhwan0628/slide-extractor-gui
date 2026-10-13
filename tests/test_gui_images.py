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


def test_visible_request_promotes_prefetch_and_survives_full_queue(tmp_path,monkeypatch):
    from threading import Event
    from gui import images
    from tests.qt_fixtures import spin
    qt=app();real=images.QImage;entered=Event();release=Event()
    def delayed(*args,**kwargs):
        if args and isinstance(args[0],str):
            entered.set();assert release.wait(5)
        return real(*args,**kwargs)
    delayed.Format=real.Format
    monkeypatch.setattr(images,'QImage',delayed)
    path=tmp_path/'frame.png';Image.new('RGB',(16,12),'blue').save(path)
    loader=ImageLoader();results=[]
    loader.ready.connect(lambda key,image,error:(results.append(key),loader.ack()))
    try:
        loader.switch('g');loader.request('reading',path)
        assert entered.wait(2)
        for i in range(16):loader.request(i,path)
        loader.request(10,path,priority=True)
        with loader._cv:
            assert len(loader._pending)==16
            assert loader._pending[0][0]==10
            assert sum(item[0]==10 for item in loader._pending)==1
        loader.request('latest',path,priority=True)
        with loader._cv:
            assert len(loader._pending)==16
            assert loader._pending[0][0]=='latest'
            assert loader._pending_keys=={item[0] for item in loader._pending}
        release.set()
        spin(qt,lambda:len(results)==17)
        assert results[:3]==['reading','latest',10]
    finally:release.set();loader.stop()

def test_switch_discards_inflight_visible_request(tmp_path,monkeypatch):
    from threading import Event
    from gui import images
    from tests.qt_fixtures import spin
    qt=app();real=images.QImage;entered=Event();release=Event()
    def delayed(*args,**kwargs):
        if args and isinstance(args[0],str):
            entered.set();assert release.wait(5)
        return real(*args,**kwargs)
    delayed.Format=real.Format
    monkeypatch.setattr(images,'QImage',delayed)
    path=tmp_path/'frame.png';Image.new('RGB',(16,12),'blue').save(path)
    loader=ImageLoader();results=[]
    loader.ready.connect(lambda key,image,error:(results.append(key),loader.ack()))
    try:
        loader.switch('old');loader.request('old-visible',path,priority=True)
        assert entered.wait(2)
        loader.switch('new');loader.request('new-visible',path,priority=True)
        release.set();spin(qt,lambda:bool(results))
        assert results==['new-visible']
        assert loader.cached('old-visible') is None
    finally:release.set();loader.stop()


def test_lazy_resolver_is_cancelled_when_loader_stops(tmp_path):
    from threading import Event
    from PySide6.QtWidgets import QApplication
    from gui.images import ImageLoader
    app=QApplication.instance() or QApplication([])
    entered=Event();cancelled=Event();loader=ImageLoader()
    def resolve(token):
        entered.set()
        while not token.cancelled:cancelled.wait(.01)
        cancelled.set();token.raise_if_cancelled()
    loader.request('lazy',tmp_path/'missing.jpg',resolver=resolve)
    assert entered.wait(2)
    loader.stop()
    assert cancelled.is_set() and not loader._thread.is_alive()
