"""Bounded immutable-page edit history, never records navigation."""
from dataclasses import dataclass

@dataclass(frozen=True)
class Snapshot:
    pages: tuple
    focus: str | None

class EditHistory:
    def __init__(self,limit=100):
        self.limit=limit
        self.project=None
        self.undo_stack=[]
        self.redo_stack=[]
    def reset(self,project=None):
        self.project=project
        self.undo_stack.clear()
        self.redo_stack.clear()
    def record(self,project,before,after):
        if project is not self.project:
            self.reset(project)
        if before.pages==after.pages:return False
        self.undo_stack.append((before,after))
        del self.undo_stack[:-self.limit]
        self.redo_stack.clear()
        return True
    def undo(self,project):
        if project is not self.project or not self.undo_stack:return None
        pair=self.undo_stack.pop()
        self.redo_stack.append(pair)
        return pair[0]
    def redo(self,project):
        if project is not self.project or not self.redo_stack:return None
        pair=self.redo_stack.pop()
        self.undo_stack.append(pair)
        return pair[1]
