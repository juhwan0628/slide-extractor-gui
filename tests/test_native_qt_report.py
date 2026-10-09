import json,runpy
from pathlib import Path
from PySide6.QtCore import qVersion

def test_smoke_records_loaded_qt_runtime_version(tmp_path):
    entry=runpy.run_path(str(Path(__file__).resolve().parents[1]/'packaging/desktop_entry.py'))
    report=tmp_path/'smoke.json'
    assert entry['smoke'](report)==0
    assert json.loads(report.read_text())['qt_runtime_version']==qVersion()
