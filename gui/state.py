"""Finite-state GUI controller independent of Qt widgets."""
from dataclasses import dataclass
from enum import Enum
from slide_core.analysis import requires_reanalysis

class State(str,Enum):
    EMPTY='EMPTY';PROBING='PROBING';SOURCE_READY='SOURCE_READY'
    ANALYZING='ANALYZING';REVIEW_READY='REVIEW_READY';REVIEW_DIRTY='REVIEW_DIRTY'
    EXPORTING='EXPORTING';COMMITTING='COMMITTING';CANCELLING='CANCELLING';CLOSED='CLOSED'

@dataclass
class Controller:
    state:State=State.EMPTY
    project:object=None
    source:object=None
    pending_job:str|None=None
    focus_page_id:str|None=None
    active_page_id:str|None=None
    close_pending:bool=False
    playback:bool=False

    def actions(self):
        idle=self.state in {State.EMPTY,State.SOURCE_READY,State.REVIEW_READY,State.REVIEW_DIRTY}
        review=self.state in {State.REVIEW_READY,State.REVIEW_DIRTY}
        pages=bool(self.project and self.project.pages)
        return dict(open=idle,region=idle and self.source is not None,
            analyze=idle and self.source is not None,
            edit=review and bool(self.project and self.project.samples),
            export=self.state==State.REVIEW_READY and pages,
            playback=review and bool(self.project and self.project.samples),
            cancel=self.state in {State.PROBING,State.ANALYZING,State.EXPORTING},
            close=self.state not in {State.COMMITTING,State.CLOSED})

    def begin_probe(self):
        if not self.actions()['open']:raise RuntimeError('Not idle')
        self._previous=self.state
        self.state=State.PROBING;self.playback=False

    def complete_probe(self,source):
        if self.state!=State.PROBING:raise RuntimeError('No probe')
        self.source=source;self.project=None
        self.state=State.SOURCE_READY
        self.focus_page_id=self.active_page_id=None

    def fail_probe(self):
        if self.state!=State.PROBING:raise RuntimeError('No probe')
        self.state=self._previous

    def begin_analysis(self,job_id):
        if not self.actions()['analyze']:raise RuntimeError('Cannot analyze')
        self._previous=self.state;self.state=State.ANALYZING
        self.pending_job=job_id;self.playback=False

    def finish_analysis(self,job_id,result):
        if self.pending_job!=job_id or self.state!=State.ANALYZING:return False
        self.project=result;self.source=result.source
        self.focus_page_id=result.pages[0].page_id if result.pages else None
        self.active_page_id=self.focus_page_id
        self.pending_job=None;self.state=State.REVIEW_READY
        return True

    def begin_export(self,job_id):
        if not self.actions()['export']:raise RuntimeError('Cannot export')
        self.pending_job=job_id;self.state=State.EXPORTING;self.playback=False
        self._cancel_origin=None

    def committing(self,job_id):
        if self.pending_job==job_id and self.state==State.EXPORTING:
            self.state=State.COMMITTING
            return True
        return False

    def finish_export(self,job_id):
        if self.pending_job!=job_id:return False
        self.pending_job=None;self.state=State.REVIEW_READY
        return True

    def fail_job(self,job_id):
        if self.pending_job!=job_id:return False
        was_export=self.state in {State.EXPORTING,State.COMMITTING} or (
            self.state==State.CANCELLING and getattr(self,'_cancel_origin',None)==State.EXPORTING)
        self.pending_job=None
        self.state=(State.REVIEW_READY if was_export else self._previous)
        self._cancel_origin=None
        return True

    def cancel(self):
        if not self.actions()['cancel']:return False
        if self.state == State.PROBING:
            # Preserve PROBING until the worker terminates so failed_probe
            # can restore the previous source/project state unambiguously.
            return True
        self._cancel_origin=self.state
        self.state=State.CANCELLING;return True

    def settings_changed(self,settings):
        if self.project is None:return False
        dirty=requires_reanalysis(self.project,settings)
        if self.state in {State.REVIEW_READY,State.REVIEW_DIRTY}:
            self.state=State.REVIEW_DIRTY if dirty else State.REVIEW_READY
        return dirty

    def adopted_edit(self,focus_id):
        self.focus_page_id=focus_id
        if not (self.project and self.project.pages):self.active_page_id=None

    def close(self):
        if self.state==State.COMMITTING:return False
        if self.state in {State.PROBING,State.ANALYZING,State.EXPORTING,State.CANCELLING}:
            self.close_pending=True;return False
        self.state=State.CLOSED;return True
