from pathlib import Path
import time
import pytest
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer
from gui.window import Window
from gui.state import State

def spin(app,condition,timeout=15):
    started=time.monotonic()
    while time.monotonic()-started<timeout:
        app.processEvents()
        if condition():return
        time.sleep(.005)
    raise AssertionError('Qt operation timeout')
