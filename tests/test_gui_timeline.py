from types import SimpleNamespace
from fractions import Fraction
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QPointF,Qt,QEvent
from PySide6.QtGui import QMouseEvent
from gui.timeline import Timeline

class ProjectStub:
    source=SimpleNamespace(metadata=(('duration_s',10),))
    transitions=[SimpleNamespace(lower_time=Fraction(2),upper_time=Fraction(3),observed_time=Fraction(3))]
    pages=[SimpleNamespace(page_id='p1',representative_sample_id='sample1')]
    def sample_time(self,id):return Fraction(5)

def test_timeline_two_tracks_and_boundary_tooltip():
    app=QApplication.instance() or QApplication([])
    timeline=Timeline();timeline.resize(1000,60);timeline.set_project(ProjectStub())
    assert '2.000' in timeline.boundary_tooltip(250)
    assert timeline.boundary_tooltip(700) is None
    hit=[];seek=[]
    timeline.markerClicked.connect(hit.append);timeline.seekRequested.connect(seek.append)
    event=QMouseEvent(QEvent.Type.MouseButtonPress,QPointF(500,42),QPointF(500,42),
        Qt.MouseButton.LeftButton,Qt.MouseButton.LeftButton,Qt.KeyboardModifier.NoModifier)
    timeline.mousePressEvent(event)
    assert hit==['p1']
    assert seek==[5.]
