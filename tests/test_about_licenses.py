from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication,QMessageBox
from gui.window import Window

def test_about_dialog_exposes_runtime_license_and_source_notice():
    app=QApplication.instance() or QApplication([])
    window=Window();window.show();app.processEvents()
    seen=[]
    def inspect():
        dialog=app.activeModalWidget()
        assert isinstance(dialog,QMessageBox)
        seen.append(dialog.text());dialog.accept()
    try:
        assert hasattr(window,'show_about'),'No accessible application license dialog'
        QTimer.singleShot(20,inspect)
        window.show_about()
        assert all(text in seen[0] for text in ('MIT','Qt','LGPL','FFmpeg','github.com/juhwan0628/slide-extractor-gui'))
    finally:window.close();app.processEvents()
