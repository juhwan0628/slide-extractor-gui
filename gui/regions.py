"""Preview-only region dialog; video source is never reopened."""
from math import floor,ceil
from PySide6.QtCore import QRectF,Qt,QPointF
from PySide6.QtWidgets import QDialog,QVBoxLayout,QLabel,QDialogButtonBox
from PySide6.QtGui import QImage,QPainter,QPen,QColor,QPixmap
from slide_core.models import Rect

def view_to_display(point,canvas_width,canvas_height,image_width,image_height,*,clamp=False):
    scale=min(canvas_width/image_width,canvas_height/image_height)
    pw,ph=image_width*scale,image_height*scale
    ox,oy=(canvas_width-pw)/2,(canvas_height-ph)/2
    x,y=point[0]-ox,point[1]-oy
    if not clamp and (x<0 or y<0 or x>pw or y>ph):return None
    x=max(0,min(pw,x));y=max(0,min(ph,y))
    return x/scale,y/scale

def drag_rect(start,end,w,h,cw,ch):
    a=view_to_display(start,cw,ch,w,h)
    if a is None:return None
    b=view_to_display(end,cw,ch,w,h,clamp=True)
    x0,y0=max(0,floor(min(a[0],b[0]))),max(0,floor(min(a[1],b[1])))
    x1,y1=min(w,ceil(max(a[0],b[0]))),min(h,ceil(max(a[1],b[1])))
    if x1<=x0 or y1<=y0:return None
    return Rect(x0,y0,x1-x0,y1-y0)

class RegionDialog(QDialog):
    def __init__(self,image:QImage,title,parent=None,*,initial=None):
        super().__init__(parent);self.setWindowTitle(title)
        self.image=image.copy();self.selection=None
        layout=QVBoxLayout(self);self.label=QLabel('Move the rectangle or resize with its 8 handles. Drag outside to draw a new rectangle.')
        layout.addWidget(self.label)
        self.view=RegionCanvas(image,initial=initial);layout.addWidget(self.view)
        buttons=QDialogButtonBox(QDialogButtonBox.StandardButton.Ok|QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject);layout.addWidget(buttons)
    def _accept(self):
        if self.view.selection:self.selection=self.view.selection;self.accept()
    def value(self):return self.selection

from PySide6.QtWidgets import QWidget

def adjust_rect(rect,mode,dx,dy,width,height):
    """Move or resize rectangle in image pixels, with clamped image bounds."""
    x0,y0=rect.x,rect.y
    x1,y1=x0+rect.width,y0+rect.height
    dx,dy=round(dx),round(dy)
    if mode=='move':
        nx=max(0,min(width-rect.width,x0+dx))
        ny=max(0,min(height-rect.height,y0+dy))
        return Rect(nx,ny,rect.width,rect.height)
    if 'w' in mode:x0=max(0,min(x1-1,x0+dx))
    if 'e' in mode:x1=max(x0+1,min(width,x1+dx))
    if 'n' in mode:y0=max(0,min(y1-1,y0+dy))
    if 's' in mode:y1=max(y0+1,min(height,y1+dy))
    return Rect(x0,y0,x1-x0,y1-y0)

class RegionCanvas(QWidget):
    HANDLES=('nw','n','ne','e','se','s','sw','w')
    def __init__(self,image,parent=None,*,initial=None):
        super().__init__(parent)
        self.image=image.copy()
        self.selection=initial
        self.anchor=None;self.base=None;self.mode=None
        self.setMinimumSize(560,315)
        self.setMouseTracking(True)
    def _geometry(self):
        w,h=self.image.width(),self.image.height()
        scale=min(self.width()/w,self.height()/h)
        return scale,(self.width()-w*scale)/2,(self.height()-h*scale)/2
    def _handles(self):
        if self.selection is None:return {}
        r=self.selection
        return dict(nw=(r.x,r.y),n=(r.x+r.width/2,r.y),
                    ne=(r.x+r.width,r.y),e=(r.x+r.width,r.y+r.height/2),
                    se=(r.x+r.width,r.y+r.height),s=(r.x+r.width/2,r.y+r.height),
                    sw=(r.x,r.y+r.height),w=(r.x,r.y+r.height/2))
    def _hit(self,pos):
        if self.selection is None:return None
        scale,ox,oy=self._geometry()
        x=(pos[0]-ox)/scale;y=(pos[1]-oy)/scale
        for mode,(hx,hy) in self._handles().items():
            if abs(x-hx)<=7/scale and abs(y-hy)<=7/scale:return mode
        r=self.selection
        if r.x<=x<=r.x+r.width and r.y<=y<=r.y+r.height:return 'move'
        return None
    def mousePressEvent(self,e):
        if e.button()!=Qt.MouseButton.LeftButton:return
        at=(e.position().x(),e.position().y())
        coords=view_to_display(at,self.width(),self.height(),self.image.width(),self.image.height())
        if coords is None:return
        self.anchor=coords
        self.base=self.selection
        self.mode=self._hit(at) or 'draw'
        if self.mode=='draw':self.selection=None
        self.update()
    def mouseMoveEvent(self,e):
        if self.anchor is None:return
        at=(e.position().x(),e.position().y())
        coords=view_to_display(at,self.width(),self.height(),self.image.width(),self.image.height(),clamp=True)
        if self.mode=='draw':
            scale,ox,oy=self._geometry()
            self.selection=drag_rect((self.anchor[0]*scale+ox,self.anchor[1]*scale+oy),at,
                self.image.width(),self.image.height(),self.width(),self.height())
        elif self.base is not None:
            self.selection=adjust_rect(self.base,self.mode,coords[0]-self.anchor[0],
                                       coords[1]-self.anchor[1],self.image.width(),self.image.height())
        self.update()
    def mouseReleaseEvent(self,e):
        if self.anchor is not None:
            self.mouseMoveEvent(e)
            self.anchor=None;self.base=None;self.mode=None
    def paintEvent(self,e):
        p=QPainter(self);p.fillRect(self.rect(),QColor('#20242a'))
        image=QPixmap.fromImage(self.image)
        fitted=image.scaled(self.size(),Qt.AspectRatioMode.KeepAspectRatio,Qt.TransformationMode.SmoothTransformation)
        ox=(self.width()-fitted.width())/2;oy=(self.height()-fitted.height())/2
        p.drawPixmap(round(ox),round(oy),fitted)
        if self.selection:
            scale,ox,oy=self._geometry()
            r=self.selection
            p.setPen(QPen(QColor('#33ccff'),2))
            p.drawRect(QRectF(ox+r.x*scale,oy+r.y*scale,r.width*scale,r.height*scale))
            p.setPen(QPen(QColor('#137a98'),1))
            p.setBrush(QColor('#ffffff'))
            for hx,hy in self._handles().values():
                p.drawRect(QRectF(ox+hx*scale-4,oy+hy*scale-4,8,8))
        p.end()
