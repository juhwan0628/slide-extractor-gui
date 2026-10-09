"""Stable ID Qt list model whose rows are independent of in-place core edits."""
from PySide6.QtCore import QAbstractListModel,QModelIndex,Qt,QSize
from PySide6.QtGui import QIcon

class PageModel(QAbstractListModel):
    PageId=int(Qt.ItemDataRole.UserRole)+1
    SampleId=int(Qt.ItemDataRole.UserRole)+2
    def __init__(self,parent=None):
        super().__init__(parent)
        self.project=None;self._ids=[];self._thumbs={};self._pages={};self._rows_for_sample={}

    def rowCount(self,parent=QModelIndex()):
        return 0 if parent.isValid() else len(self._ids)

    def _page(self,pid):
        return self._pages.get(pid)

    def _reindex(self):
        self._pages={p.page_id:p for p in self.project.pages} if self.project else {}
        self._rows_for_sample={}
        for row,pid in enumerate(self._ids):
            page=self._pages.get(pid)
            if page is not None:
                self._rows_for_sample.setdefault(page.representative_sample_id,[]).append(row)

    def data(self,index,role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid() or index.row()<0 or index.row()>=len(self._ids):return None
        pid=self._ids[index.row()];page=self._page(pid)
        if role==Qt.ItemDataRole.SizeHintRole:return QSize(175,92)
        if role==self.PageId:return pid
        if page is None:return None
        if role==Qt.ItemDataRole.DisplayRole:
            seconds=float(self.project.sample_time(page.representative_sample_id))
            return f'Page {index.row()+1} · {int(seconds//60):02d}:{int(seconds%60):02d}'
        if role==self.SampleId:return page.representative_sample_id
        if role==Qt.ItemDataRole.DecorationRole:return self._thumbs.get(page.representative_sample_id)
        if role==Qt.ItemDataRole.ToolTipRole:return f'{page.origin} | {page.last_edit_kind}'
        return None

    def set_project(self,project):
        self.beginResetModel()
        self.project=project;self._ids=[p.page_id for p in project.pages] if project else []
        self._thumbs.clear();self._reindex()
        self.endResetModel()

    def set_thumbnail(self,sample_id,icon:QIcon):
        rows=self._rows_for_sample.get(sample_id,())
        if not rows:return
        self._thumbs[sample_id]=icon
        for row in rows:
            idx=self.index(row)
            self.dataChanged.emit(idx,idx,[Qt.ItemDataRole.DecorationRole])

    def sync(self,old_ids=None):
        if self.project is None:return
        self._pages={p.page_id:p for p in self.project.pages}
        new_ids=list(self._pages)
        for i in range(len(self._ids)-1,-1,-1):
            if self._ids[i] not in new_ids:
                self.beginRemoveRows(QModelIndex(),i,i)
                self._ids.pop(i)
                self.endRemoveRows()
        for i,pid in enumerate(new_ids):
            if pid not in self._ids:
                self.beginInsertRows(QModelIndex(),i,i)
                self._ids.insert(i,pid)
                self.endInsertRows()
            elif self._ids.index(pid)!=i:
                old=self._ids.index(pid)
                destination=i if old>i else i+1
                self.beginMoveRows(QModelIndex(),old,old,QModelIndex(),destination)
                self._ids.insert(i,self._ids.pop(old))
                self.endMoveRows()
        self._reindex()
        self._thumbs={sid:icon for sid,icon in self._thumbs.items() if sid in self._rows_for_sample}
        if self.rowCount():
            self.dataChanged.emit(self.index(0),self.index(self.rowCount()-1))
