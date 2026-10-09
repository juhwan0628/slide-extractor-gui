"""Desktop entry point for the current PTS-aware editor."""
from PySide6.QtWidgets import QApplication
from gui.window import Window


def main():
    app=QApplication.instance() or QApplication([])
    app.setStyle('Fusion')
    window=Window();window.show()
    return app.exec()


if __name__=='__main__':
    raise SystemExit(main())
