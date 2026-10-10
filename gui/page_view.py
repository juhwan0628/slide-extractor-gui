"""Native extended selection with restorable Shift anchor and right-click state."""
from PySide6.QtCore import Qt,QItemSelectionModel,QItemSelection
from PySide6.QtWidgets import QListView,QAbstractItemView

class PageView(QListView):
    def __init__(self,parent=None):
        super().__init__(parent)
        self.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.range_anchor=None;self.range_base=();self._restored_range=False

    def setCurrentIndex(self,index):
        super().setCurrentIndex(index)
        self._remember_range()
        self._restored_range=True

    def _page_id(self,index):
        return index.data(self.model().PageId) if index.isValid() else None

    def _remember_range(self):
        self.range_anchor=self._page_id(self.currentIndex())
        self.range_base=tuple(self._page_id(i) for i in self.selectionModel().selectedRows()
                              if self._page_id(i)!=self.range_anchor)
        self._restored_range=False

    def restore_range(self,anchor,base=()):
        self.range_anchor=anchor;self.range_base=tuple(base);self._restored_range=True

    def _extend_restored_range(self,index):
        if not index.isValid():return
        model=self.model()
        anchor=next((row for row in range(model.rowCount())
                     if self._page_id(model.index(row))==self.range_anchor),index.row())
        selected=QItemSelection(model.index(min(anchor,index.row())),model.index(max(anchor,index.row())))
        for row in range(model.rowCount()):
            item=model.index(row)
            if self._page_id(item) in self.range_base:selected.select(item,item)
        self.selectionModel().select(selected,QItemSelectionModel.SelectionFlag.ClearAndSelect)
        self.selectionModel().setCurrentIndex(index,QItemSelectionModel.SelectionFlag.NoUpdate)
        self.scrollTo(index)

    def keyPressEvent(self,event):
        moves={Qt.Key.Key_Up:self.CursorAction.MoveUp,Qt.Key.Key_Down:self.CursorAction.MoveDown,
               Qt.Key.Key_Home:self.CursorAction.MoveHome,Qt.Key.Key_End:self.CursorAction.MoveEnd,
               Qt.Key.Key_PageUp:self.CursorAction.MovePageUp,Qt.Key.Key_PageDown:self.CursorAction.MovePageDown}
        if self._restored_range and event.modifiers() & Qt.KeyboardModifier.ShiftModifier and event.key() in moves:
            self._extend_restored_range(self.moveCursor(moves[event.key()],event.modifiers()))
            event.accept();return
        super().keyPressEvent(event)
        if event.key() in moves and not event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
            self._remember_range()

    def mousePressEvent(self,event):
        index=self.indexAt(event.position().toPoint())
        if event.button()==Qt.MouseButton.RightButton:
            if index.isValid():
                if self.selectionModel().isSelected(index):
                    self.selectionModel().setCurrentIndex(index,QItemSelectionModel.SelectionFlag.NoUpdate)
                else:
                    self.setCurrentIndex(index);self._remember_range()
                self.setFocus()
            event.accept();return
        if self._restored_range and event.button()==Qt.MouseButton.LeftButton and event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
            self._extend_restored_range(index);self.setFocus();event.accept();return
        super().mousePressEvent(event)
        if event.button()==Qt.MouseButton.LeftButton and not event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
            self._remember_range()
