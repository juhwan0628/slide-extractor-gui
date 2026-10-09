import time
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer
from gui.workers import JobCoordinator

def app():return QApplication.instance() or QApplication([])

def pump(qt,condition,seconds=3):
    finish=time.monotonic()+seconds
    while time.monotonic()<finish:
        qt.processEvents()
        if condition():return True
        time.sleep(.005)
    return False

def test_worker_result_only_after_thread_finished():
    qt=app();manager=JobCoordinator();results=[]
    manager.done.connect(lambda *args:results.append(args))
    job=manager.start(lambda *,cancel_token:42)
    assert pump(qt,lambda:bool(results))
    assert results[0][:2]==(job,42) and results[0][2] is None
    assert manager.close_ready()

def test_cancelled_worker_has_single_terminal_outcome():
    qt=app();manager=JobCoordinator();results=[]
    manager.done.connect(lambda *args:results.append(args))
    def operation(*,cancel_token):
        while not cancel_token.cancelled:time.sleep(.005)
        return 'late success'
    manager.start(operation);manager.cancel()
    assert pump(qt,lambda:bool(results))
    assert results[0][1] is None and results[0][2] is not None
    assert len(results)==1

def test_heartbeat_during_worker_operation():
    qt=app();manager=JobCoordinator();ticks=[];results=[]
    timer=QTimer();timer.timeout.connect(lambda:ticks.append(time.monotonic()));timer.start(25)
    manager.done.connect(lambda *args:results.append(args))
    manager.start(lambda *,cancel_token:(time.sleep(.2),'done')[1])
    assert pump(qt,lambda:bool(results))
    timer.stop();assert len(ticks)>=3
