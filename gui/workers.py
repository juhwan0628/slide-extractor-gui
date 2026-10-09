"""Single-job QThread wrapper; result adopted only after finished signal."""
from uuid import uuid4
from PySide6.QtCore import QObject,QThread,Signal,Slot
from slide_core.models import CancelToken,CancelledError

class Worker(QThread):
    outcome=Signal(str,object,object)
    progress=Signal(str,object)
    def __init__(self,fn,*args,job_id=None,**kwargs):
        super().__init__();self.fn=fn;self.args=args;self.kwargs=kwargs
        self.job_id=job_id or str(uuid4());self.cancel_token=CancelToken()
        self.progress_enabled=kwargs.pop('_progress_enabled',False)
    def run(self):
        try:
            if self.progress_enabled:
                self.kwargs['progress']=lambda stage,done=None,total=None:self.progress.emit(self.job_id,(stage,done,total))
            result=self.fn(*self.args,cancel_token=self.cancel_token,**self.kwargs)
            if self.cancel_token.cancelled and not self.cancel_token.committed:
                self.outcome.emit(self.job_id,None,CancelledError('Cancelled'))
            else:self.outcome.emit(self.job_id,result,None)
        except BaseException as exc:self.outcome.emit(self.job_id,None,exc)

class JobCoordinator(QObject):
    done=Signal(str,object,object)
    busyChanged=Signal(bool)
    progress=Signal(str,object)
    def __init__(self,parent=None):
        super().__init__(parent);self.worker=None;self.pending=None
    def start(self,fn,*args,**kwargs):
        if self.worker is not None:raise RuntimeError('A job is already running')
        worker=Worker(fn,*args,**kwargs)
        self.worker=worker;self.pending=None
        worker.outcome.connect(self._outcome)
        worker.progress.connect(self._progress)
        worker.finished.connect(self._finished)
        self.busyChanged.emit(True)
        worker.start();return worker.job_id
    @Slot(str,object)
    def _progress(self,job_id,payload):
        if self.worker is not None and job_id==self.worker.job_id:
            self.progress.emit(job_id,payload)
    @Slot(str,object,object)
    def _outcome(self,job_id,result,error):
        if self.worker is not None and job_id==self.worker.job_id:
            self.pending=(job_id,result,error)
    @Slot()
    def _finished(self):
        worker=self.worker
        if worker is None:return
        pending=self.pending
        self.worker=None;self.pending=None
        self.busyChanged.emit(False)
        if pending is None:self.done.emit(worker.job_id,None,RuntimeError('Missing terminal outcome'))
        else:self.done.emit(*pending)
        worker.deleteLater()
    def cancel(self):
        if self.worker is not None:self.worker.cancel_token.cancel()
    def close_ready(self):return self.worker is None
