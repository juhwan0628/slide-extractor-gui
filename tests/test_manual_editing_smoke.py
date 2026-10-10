"""Packaged smoke verifies actual page gestures, editing and edited exports."""
from pathlib import Path
import json
import runpy

def test_installed_smoke_exercises_manual_editing(tmp_path):
    entry=runpy.run_path(str(Path(__file__).parents[1]/'packaging/desktop_entry.py'))
    target=tmp_path/'smoke.json'
    assert entry['smoke'](target)==0
    report=json.loads(target.read_text())
    assert report['manual_editing_checked'] is True
    assert report['keyboard_editing_checked'] is True
    assert report['edited_export_checked'] is True
