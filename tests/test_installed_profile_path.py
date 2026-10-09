from pathlib import Path
import sys
from slide_core import profiling

def test_installed_mac_profiles_live_outside_application_bundle(tmp_path,monkeypatch):
    monkeypatch.setattr(sys,'frozen',True,raising=False)
    monkeypatch.setattr(sys,'platform','darwin')
    monkeypatch.setattr(Path,'home',classmethod(lambda cls:tmp_path))
    root=tmp_path/'Applications/SlideExtractor.app/Contents/Frameworks'
    assert profiling.profile_directory(root)==tmp_path/'Library/Application Support/SlideExtractor/profiles'

def test_source_profiles_stay_beside_project(tmp_path,monkeypatch):
    monkeypatch.delattr(sys,'frozen',raising=False)
    assert profiling.profile_directory(tmp_path)==tmp_path/'profiles'
