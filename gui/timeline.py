"""Timeline has independent immutable transition and editable page markers."""
from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Qt,Signal,QRectF
from PySide6.QtGui import QPainter,QColor,QPen

class Timeline(QWidget):
    seekRequested=Signal(float)
    markerClicked=Signal(str)
    def __init__(self,parent=None):
        super().__init__(parent);self.project=None;self.position=0.
        self.setFixedHeight(34)
        self._scrubbing=False
        self.setMouseTracking(True)
    def set_project(self,project):self.project=project;self.position=0.;self.update()
    def set_position(self,seconds):self.position=float(seconds);self.update()
    def _duration(self):
        return float(dict(self.project.source.metadata).get('duration_s',1)) or 1

    def boundary_tooltip(self,x):
        if not self.project:return None
        duration=self._duration()
        for t in self.project.transitions:
            lo=float(t.lower_time)/duration*self.width()
            hi=float(t.upper_time)/duration*self.width()
            if lo-4<=x<=hi+4:
                return f'Change boundary ({float(t.lower_time):.3f}, {float(t.upper_time):.3f}] s · observed {float(t.observed_time):.3f} s'
        return None

    def _seek_at(self,x):
        if self.project is not None:
            duration=self._duration()
            self.seekRequested.emit(max(0,min(duration,x/max(1,self.width())*duration)))

    def mouseMoveEvent(self,event):
        if self._scrubbing:self._seek_at(event.position().x())
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self,event):
        if self._scrubbing:
            self._seek_at(event.position().x())
            self._scrubbing=False
            self.releaseMouse()
        super().mouseReleaseEvent(event)

    def mousePressEvent(self,event):
        if not self.project or event.button()!=Qt.MouseButton.LeftButton:return
        self._scrubbing=True
        duration=self._duration()
        for page in self.project.pages:
            marker=float(self.project.sample_time(page.representative_sample_id))/duration*self.width()
            if abs(marker-event.position().x())<=5:
                self.markerClicked.emit(page.page_id)
                break
        self._seek_at(event.position().x())
    def paintEvent(self,event):
        painter=QPainter(self)
        painter.fillRect(self.rect(),QColor('#20242a'))
        painter.fillRect(QRectF(0,16,self.width(),2),QColor('#687380'))
        if self.project:
            duration=float(dict(self.project.source.metadata).get('duration_s',1)) or 1
            for page in self.project.pages:
                x=float(self.project.sample_time(page.representative_sample_id))/duration*self.width()
                painter.fillRect(QRectF(x,10,2,14),QColor('#57b5de'))
            x=self.position/duration*self.width()
            painter.setPen(QPen(QColor('white'),2));painter.drawLine(int(x),2,int(x),self.height()-2)
        painter.end()
