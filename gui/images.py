"""Bounded asynchronous JPEG loading; never create QPixmap off main thread."""
from collections import OrderedDict,deque
from threading import Thread,Lock,Condition
from pathlib import Path
from PySide6.QtCore import QObject,Signal,QSize,QRect
from PySide6.QtGui import QImage
from slide_core.models import CancelToken

class ImageUnavailable(RuntimeError):pass

class ByteLRU:
    def __init__(self,limit):self.limit=limit;self.used=0;self.values=OrderedDict()
    def get(self,key):
        if key not in self.values:return None
        self.values.move_to_end(key);return self.values[key][0]
    def put(self,key,value,size):
        if size>self.limit:return False
        if key in self.values:
            self.used-=self.values.pop(key)[1]
        self.values[key]=(value,size);self.used+=size
        while self.used>self.limit:
            _,(_,bytes_used)=self.values.popitem(last=False);self.used-=bytes_used
        return True
    def clear(self):self.values.clear();self.used=0

class ImageLoader(QObject):
    ready=Signal(object,object,object) # request key, detached QImage, error
    def __init__(self,parent=None):
        super().__init__(parent)
        self.preview=ByteLRU(64*1024*1024);self.thumbs=ByteLRU(16*1024*1024)
        self._pending=deque();self._pending_keys=set();self._cv=Condition();self._closed=False
        self._generation=None;self._cancel_token=CancelToken()
        self._reading=False
        self._awaiting_delivery=0  # cap queued detached QImages at eight
        self._thread=Thread(target=self._run,name='slide-image-reader',daemon=False)
        self._thread.start()

    def switch(self,generation):
        with self._cv:
            self._cancel_token.cancel();self._cancel_token=CancelToken()
            self._generation=generation;self._pending.clear();self._pending_keys.clear()
            self.preview.clear();self.thumbs.clear()
            self._cv.notify_all()

    def request(self,key,path,kind='preview',size=None,crop=None,*,priority=False,resolver=None):
        with self._cv:
            lru=self.thumbs if kind=='thumb' else self.preview
            image=lru.get(key)
            if image is not None:return image
            if self._closed:return None
            if priority:
                # Promote a prefetched frame, or reserve room for the newest
                # visible frame. Background work remains bounded and retryable.
                if key in self._pending_keys:
                    item=next(item for item in self._pending if item[0]==key)
                    self._pending.remove(item)
                else:
                    if len(self._pending)>=16:
                        dropped=self._pending.pop()
                        self._pending_keys.discard(dropped[0])
                    item=(key,Path(path),kind,size,crop,self._generation,resolver,self._cancel_token)
                self._pending.appendleft(item)
            else:
                if len(self._pending)>=16 or key in self._pending_keys:return None
                self._pending.append((key,Path(path),kind,size,crop,self._generation,resolver,self._cancel_token))
            self._pending_keys.add(key)
            self._cv.notify();return None

    def cached(self,key,kind='preview'):
        return (self.thumbs if kind=='thumb' else self.preview).get(key)

    def _run(self):
        while True:
            with self._cv:
                while not self._closed and not self._pending:self._cv.wait()
                if self._closed:return
                key,path,kind,size,crop,generation,resolver,cancel_token=self._pending.popleft()
                self._pending_keys.discard(key)
                self._reading=True
            try:
                cancel_token.raise_if_cancelled()
                if resolver is not None:resolver(cancel_token)
                if path.is_symlink() or not path.is_file():raise ImageUnavailable(f'Missing sample image: {path}')
                img=QImage(str(path))
                if img.isNull():raise ImageUnavailable(f'Corrupt sample image: {path}')
                img=img.convertToFormat(QImage.Format.Format_RGB888)
                if crop is not None:
                    x,y,w,h=crop
                    if x<0 or y<0 or w<=0 or h<=0 or x+w>img.width() or y+h>img.height():
                        raise ImageUnavailable('Invalid ROI crop')
                    img=img.copy(QRect(x,y,w,h))
                if size:img=img.scaled(size)
                img=img.copy()
                error=None
            except Exception as exc:img=QImage();error=str(exc)
            with self._cv:
                self._reading=False;self._cv.notify_all()
                while generation==self._generation and self._awaiting_delivery >= 8 and not self._closed:
                    self._cv.wait(timeout=.1)
                if self._closed or generation!=self._generation:continue
                if error is None:
                    bytes_used=img.sizeInBytes()
                    (self.thumbs if kind=='thumb' else self.preview).put(key,img,bytes_used)
                self._awaiting_delivery+=1
                self.ready.emit(key,img,error)

    def wait_idle(self):
        """Called off the UI thread after switch(None), before deleting JPEGs."""
        with self._cv:
            while self._reading:self._cv.wait()

    def ack(self):
        """Main-thread consumer acknowledges a delivered QImage."""
        with self._cv:
            self._awaiting_delivery=max(0,self._awaiting_delivery-1)
            self._cv.notify_all()

    def stop(self):
        with self._cv:
            self._cancel_token.cancel()
            self._closed=True;self._pending.clear();self._pending_keys.clear();self._cv.notify_all()
        self._thread.join(timeout=10)
        if self._thread.is_alive():raise RuntimeError('Image loader failed to stop')
        self.preview.clear();self.thumbs.clear()
