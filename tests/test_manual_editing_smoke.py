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

def test_smoke_releases_cache_pin_before_temp_cleanup(tmp_path,monkeypatch):
    import tempfile
    from slide_core.cache import acquire_file_lease
    original=tempfile.TemporaryDirectory
    class CheckedTemporaryDirectory(original):
        def __exit__(self,*args):
            for path in Path(self.name).glob('cache/session-*/lease.lock'):
                with acquire_file_lease(path):
                    pass  # Windows cannot delete this file while a Project pin owns it.
            return super().__exit__(*args)
    monkeypatch.setattr(tempfile,'TemporaryDirectory',CheckedTemporaryDirectory)
    entry=runpy.run_path(str(Path(__file__).parents[1]/'packaging/desktop_entry.py'))
    assert entry['smoke'](tmp_path/'smoke.json')==0

def test_failed_smoke_releases_cache_pin_before_temp_cleanup(tmp_path,monkeypatch):
    import tempfile,pytest
    from slide_core.cache import acquire_file_lease
    original=tempfile.TemporaryDirectory
    class CheckedTemporaryDirectory(original):
        def __exit__(self,*args):
            for path in Path(self.name).glob('cache/session-*/lease.lock'):
                with acquire_file_lease(path):pass
            return super().__exit__(*args)
    monkeypatch.setattr(tempfile,'TemporaryDirectory',CheckedTemporaryDirectory)
    entry=runpy.run_path(str(Path(__file__).parents[1]/'packaging/desktop_entry.py'))
    def failed(*args):raise ValueError('original smoke failure')
    entry['smoke'].__globals__['verify_manual_editing']=failed
    with pytest.raises(ValueError,match='original smoke failure'):
        entry['smoke'](tmp_path/'smoke.json')
