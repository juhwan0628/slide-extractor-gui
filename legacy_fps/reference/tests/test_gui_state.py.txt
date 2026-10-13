from uuid import uuid4
import pytest
from gui.state import Controller,State
from slide_core.config import AnalysisSettings

def test_empty_probe_and_error_recovery():
    c=Controller()
    assert c.state==State.EMPTY and c.actions()['open'] and not c.actions()['export']
    c.begin_probe();assert c.state==State.PROBING and not c.actions()['open']
    c.fail_probe();assert c.state==State.EMPTY
    c.begin_probe();c.complete_probe('source')
    assert c.state==State.SOURCE_READY and c.actions()['analyze']

def test_busy_cancel_and_stale_results():
    c=Controller(source='source',state=State.SOURCE_READY)
    c.begin_analysis('new')
    assert not c.actions()['open'] and c.actions()['cancel']
    assert not c.finish_analysis('old',None)
    assert c.cancel() and c.state==State.CANCELLING
    assert c.fail_job('new') and c.state==State.SOURCE_READY
    assert not c.fail_job('old')

def test_ready_dirty_revert_and_export_states():
    from types import SimpleNamespace
    from slide_core.analysis import requires_reanalysis
    settings=AnalysisSettings(roi_mode='full')
    project=SimpleNamespace(source='source',pages=[SimpleNamespace(page_id='p1')],samples=[object()],settings=settings)
    c=Controller(source='source',state=State.ANALYZING,pending_job='x')
    assert c.finish_analysis('x',project)
    assert c.actions()['export']
    assert c.settings_changed(AnalysisSettings(roi_mode='full',fps=.5))
    assert c.state==State.REVIEW_DIRTY and not c.actions()['export']
    assert not c.settings_changed(settings)
    assert c.state==State.REVIEW_READY
    c.begin_export('e');assert c.actions()['cancel']
    assert c.committing('e') and c.state==State.COMMITTING
    assert not c.cancel() and not c.close()
    assert c.finish_export('e') and c.close()
