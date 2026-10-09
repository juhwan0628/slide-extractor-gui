import errno
import types
import pytest
from slide_core import export, pts


def test_windows_directory_sync_does_not_open_directory(monkeypatch, tmp_path):
    monkeypatch.setattr(export, 'os', types.SimpleNamespace(name='nt', O_RDONLY=0, open=lambda *a: (_ for _ in ()).throw(PermissionError(errno.EACCES, 'directory open unsupported'))))
    assert export.sync_directory(tmp_path) is False


def test_posix_directory_sync_keeps_permission_errors(monkeypatch, tmp_path):
    monkeypatch.setattr(export.os, 'open', lambda *a: (_ for _ in ()).throw(PermissionError(errno.EACCES, 'access denied')))
    with pytest.raises(PermissionError):
        export.sync_directory(tmp_path)


def test_windows_stream_decoder_creates_no_console(monkeypatch):
    seen={}
    class StopLaunch(Exception): pass
    def launch(*args, **kwargs):
        seen.update(kwargs)
        raise StopLaunch
    monkeypatch.setattr(pts, 'os', types.SimpleNamespace(name='nt'))
    monkeypatch.setattr(pts.subprocess, 'CREATE_NO_WINDOW', 0x08000000, raising=False)
    monkeypatch.setattr(pts.subprocess, 'Popen', launch)
    monkeypatch.setattr(pts, '_ffmpeg', lambda *a, **kw: ['ffmpeg.exe'])
    with pytest.raises(StopLaunch):
        list(pts._decode_stream(None, '', 1, 1))
    assert seen.get('creationflags', 0) & 0x08000000
