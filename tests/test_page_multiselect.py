"""Real Qt selection gestures; fixtures do not require external lecture files."""
from fractions import Fraction
from uuid import uuid4
import pytest
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication
from gui.window import Window
from gui.state import State
from slide_core.models import Project, SourceRef, DisplayTransform, Sample, Page

@pytest.fixture
def editor(tmp_path):
    app=QApplication.instance() or QApplication([])
    samples=tuple(Sample(str(uuid4()),i,i,Fraction(1),Fraction(i),str(i),80,60) for i in range(6))
    source=SourceRef(tmp_path/'video.mp4',100,1,0,80,60,DisplayTransform(80,60))
    pages=[Page(str(uuid4()),s.sample_id,'manual',None,None,'add') for s in samples]
    project=Project(source,samples=samples,pages=pages)
    w=Window()
    w.controller.project=project;w.controller.source=source;w.controller.state=State.REVIEW_READY
    w.page_model.set_project(project);w.timeline.set_project(project)
    w._prefetch_thumbs=lambda:None;w._pump_all_thumbs=lambda:None
    w.seek_seconds=lambda seconds:None
    w._set_stage('review');w.show();app.processEvents()
    yield app,w,project
    w.controller.state=State.REVIEW_READY
    w.close();app.processEvents()

def click(app,w,row,modifier=Qt.KeyboardModifier.NoModifier):
    index=w.page_model.index(row);w.page_view.scrollTo(index);app.processEvents()
    QTest.mouseClick(w.page_view.viewport(),Qt.MouseButton.LeftButton,modifier,w.page_view.visualRect(index).center())
    app.processEvents()

def test_shift_selects_inclusive_range_and_shows_count(editor):
    app,w,p=editor
    click(app,w,1);click(app,w,4,Qt.KeyboardModifier.ShiftModifier)
    assert w.selected_page_ids()==tuple(page.page_id for page in p.pages[1:5])
    assert '4 selected' in w.selection_label.text()

def test_control_selection_keeps_unselected_middle_pages(editor):
    app,w,p=editor
    click(app,w,1);click(app,w,4,Qt.KeyboardModifier.ControlModifier)
    assert w.selected_page_ids()==(p.pages[1].page_id,p.pages[4].page_id)

def test_right_click_on_selection_keeps_range(editor):
    app,w,p=editor
    click(app,w,1);click(app,w,3,Qt.KeyboardModifier.ShiftModifier)
    w._show_page_menu=lambda *a:None
    index=w.page_model.index(2);pos=w.page_view.visualRect(index).center()
    QTest.mouseClick(w.page_view.viewport(),Qt.MouseButton.RightButton,Qt.KeyboardModifier.NoModifier,pos)
    w._page_context_menu(pos)
    assert w.selected_page_ids()==tuple(page.page_id for page in p.pages[1:4])

def test_right_click_outside_selects_only_target(editor):
    app,w,p=editor
    click(app,w,1);click(app,w,3,Qt.KeyboardModifier.ShiftModifier)
    w._show_page_menu=lambda *a:None
    index=w.page_model.index(5);w.page_view.scrollTo(index);app.processEvents()
    pos=w.page_view.visualRect(index).center()
    QTest.mouseClick(w.page_view.viewport(),Qt.MouseButton.RightButton,Qt.KeyboardModifier.NoModifier,pos)
    w._page_context_menu(pos)
    assert w.selected_page_ids()==(p.pages[5].page_id,)

def test_merge_selected_range_then_undo_restores_selection_and_preview(editor):
    app,w,p=editor
    originals=tuple(p.pages)
    click(app,w,1);click(app,w,4,Qt.KeyboardModifier.ShiftModifier)
    w.current_index=2
    w.merge_selected_pages()
    assert tuple(page.page_id for page in p.pages)==tuple(originals[i].page_id for i in (0,4,5))
    assert w.selected_page_ids()==(originals[4].page_id,)
    assert w.current_index==4
    w.undo_edit()
    assert tuple(p.pages)==originals
    assert w.selected_page_ids()==tuple(page.page_id for page in originals[1:5])
    assert w.current_index==2
    w.redo_edit()
    assert len(p.pages)==3 and w.selected_page_ids()==(originals[4].page_id,) and w.current_index==4

def test_bulk_delete_all_undo_and_new_edit_clears_redo(editor):
    app,w,p=editor
    originals=tuple(p.pages)
    w.page_view.selectAll()
    w.delete_selected_pages()
    assert not p.pages and not w.export_button.isEnabled()
    assert not w.merge_action.isEnabled() and not w.delete_action.isEnabled()
    w.undo_edit()
    assert tuple(p.pages)==originals and len(w.selected_page_ids())==6
    assert w.export_button.isEnabled()
    w.merge_selected_pages()
    assert len(p.pages)==1 and not w.history.redo_stack

def test_merge_during_busy_state_is_noop(editor):
    app,w,p=editor
    w.page_view.selectAll();old=tuple(p.pages)
    w.controller.state=State.EXPORTING
    w.merge_selected_pages();w.delete_selected_pages()
    assert tuple(p.pages)==old and p.revision==0

def test_keyboard_merge_delete_undo_and_redo(editor):
    app,w,p=editor
    old=tuple(p.pages)
    click(app,w,1);click(app,w,3,Qt.KeyboardModifier.ShiftModifier)
    w.page_view.setFocus();app.processEvents()
    QTest.keyClick(w.page_view,Qt.Key.Key_M,Qt.KeyboardModifier.ControlModifier);app.processEvents()
    assert len(p.pages)==4 and w.selected_page_ids()==(old[3].page_id,)
    QTest.keyClick(w.page_view,Qt.Key.Key_Z,Qt.KeyboardModifier.ControlModifier);app.processEvents()
    assert tuple(p.pages)==old and len(w.selected_page_ids())==3
    QTest.keyClick(w.page_view,Qt.Key.Key_Z,Qt.KeyboardModifier.ControlModifier|Qt.KeyboardModifier.ShiftModifier);app.processEvents()
    assert len(p.pages)==4
    QTest.keyClick(w.page_view,Qt.Key.Key_Backspace);app.processEvents()
    assert len(p.pages)==3
    QTest.keyClick(w.page_view,Qt.Key.Key_Z,Qt.KeyboardModifier.ControlModifier);app.processEvents()
    assert len(p.pages)==4

def test_edit_shortcuts_do_not_act_on_text_input(editor):
    from PySide6.QtWidgets import QLineEdit
    app,w,p=editor
    click(app,w,1);click(app,w,3,Qt.KeyboardModifier.ShiftModifier)
    w.merge_selected_pages();old=tuple(p.pages)
    edit=QLineEdit(w.centralWidget());edit.setText('abc');edit.show();edit.setFocus();app.processEvents()
    QTest.keyClick(edit,Qt.Key.Key_Backspace);app.processEvents()
    assert edit.text()=='ab' and tuple(p.pages)==old
    QTest.keyClick(edit,Qt.Key.Key_Z,Qt.KeyboardModifier.ControlModifier);app.processEvents()
    assert tuple(p.pages)==old
    QTest.keyClick(edit,Qt.Key.Key_M,Qt.KeyboardModifier.ControlModifier);app.processEvents()
    assert tuple(p.pages)==old

def test_shift_arrow_updates_range_and_current_page(editor):
    app,w,p=editor
    click(app,w,1);w.page_view.setFocus()
    QTest.keyClick(w.page_view,Qt.Key.Key_Down,Qt.KeyboardModifier.ShiftModifier);app.processEvents()
    assert w.selected_page_ids()==tuple(page.page_id for page in p.pages[1:3])
    assert w.controller.focus_page_id==p.pages[2].page_id

def test_undo_restores_explicit_empty_selection(editor):
    app,w,p=editor
    click(app,w,1)
    w.page_view.clearSelection()
    before=w._snapshot()
    click(app,w,2);click(app,w,3,Qt.KeyboardModifier.ShiftModifier)
    w.merge_selected_pages()
    w._restore_snapshot(before)
    assert w.selected_page_ids()==()

def test_select_all_and_delete_key(editor):
    app,w,p=editor
    w.page_view.setFocus();app.processEvents()
    QTest.keyClick(w.page_view,Qt.Key.Key_A,Qt.KeyboardModifier.ControlModifier);app.processEvents()
    assert len(w.selected_page_ids())==6
    QTest.keyClick(w.page_view,Qt.Key.Key_Delete);app.processEvents()
    assert not p.pages

def test_model_updates_do_not_deliver_stale_rows_to_preview(editor,monkeypatch):
    import sys
    app,w,p=editor
    errors=[]
    monkeypatch.setattr(sys,'excepthook',lambda *error:errors.append(error))
    click(app,w,3);click(app,w,5,Qt.KeyboardModifier.ShiftModifier)
    w.delete_selected_pages();app.processEvents()
    w.undo_edit();app.processEvents()
    w.page_view.selectAll();w.delete_selected_pages();app.processEvents()
    w.undo_edit();w.redo_edit();app.processEvents()
    assert errors==[]

def test_undo_restores_native_shift_range_anchor(editor):
    app,w,p=editor
    click(app,w,1);click(app,w,4,Qt.KeyboardModifier.ShiftModifier)
    w.merge_selected_pages();w.undo_edit()
    w.page_view.setFocus()
    for last in (3,2):
        QTest.keyClick(w.page_view,Qt.Key.Key_Up,Qt.KeyboardModifier.ShiftModifier);app.processEvents()
        assert w.selected_page_ids()==tuple(page.page_id for page in p.pages[1:last+1])

def test_undo_restores_reverse_and_disjoint_shift_anchor(editor):
    app,w,p=editor
    click(app,w,0);click(app,w,4,Qt.KeyboardModifier.ControlModifier)
    click(app,w,2,Qt.KeyboardModifier.ShiftModifier)
    w.merge_selected_pages();w.undo_edit()
    QTest.keyClick(w.page_view,Qt.Key.Key_Down,Qt.KeyboardModifier.ShiftModifier);app.processEvents()
    assert w.selected_page_ids()==tuple(p.pages[i].page_id for i in (0,3,4))
    click(app,w,5,Qt.KeyboardModifier.ShiftModifier)
    assert w.selected_page_ids()==tuple(p.pages[i].page_id for i in (0,4,5))

def test_plain_navigation_after_undo_starts_a_new_shift_range(editor):
    app,w,p=editor
    click(app,w,1);click(app,w,4,Qt.KeyboardModifier.ShiftModifier)
    w.merge_selected_pages();w.undo_edit()
    QTest.keyClick(w.page_view,Qt.Key.Key_Up);app.processEvents()
    QTest.keyClick(w.page_view,Qt.Key.Key_Down,Qt.KeyboardModifier.ShiftModifier);app.processEvents()
    assert w.selected_page_ids()==tuple(page.page_id for page in p.pages[3:5])
