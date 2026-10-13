"""M4 timing, archive completeness, component-bound license and recovery diagnostics."""
import json,runpy,zipfile,time
from pathlib import Path
from threading import Event
import pytest
ROOT=Path(__file__).resolve().parents[1]

@pytest.mark.parametrize('kit',[False,True])
def test_legacy_archive_satisfies_real_spec_data_inputs(tmp_path,monkeypatch,kit):
    script='build_windows_kit.py' if kit else 'build_source_zip.py'
    output=tmp_path/'source.zip'
    runpy.run_path(str(ROOT/'packaging'/script))['build'](output)
    unpack=tmp_path/'unpack'
    with zipfile.ZipFile(output) as z:z.extractall(unpack)
    source=unpack/('SlideExtractor-Windows/_app' if kit else 'SlideExtractor')
    monkeypatch.setattr(__import__('sys'),'platform','win32')
    monkeypatch.setenv('SLIDE_BUILD_MODE','personal')
    vendor=tmp_path/'vendor';vendor.mkdir()
    for name in ('ffmpeg.exe','ffprobe.exe'):(vendor/name).write_bytes(b'tool')
    monkeypatch.setenv('PERSONAL_FFMPEG_DIR',str(vendor))
    def analysis(scripts,**kw):
        for path in [*scripts,*[p for p,_ in kw['datas']],*[p for p,_ in kw['binaries']]]:
            assert Path(path).exists(),path
        return type('A',(),dict(pure=[],scripts=[],binaries=[],datas=[]))()
    runpy.run_path(str(source/'packaging/SlideExtractor.spec'),init_globals={
        'SPECPATH':str(source/'packaging'),'Analysis':analysis,
        'PYZ':lambda *a,**k:None,'EXE':lambda *a,**k:None,'COLLECT':lambda *a,**k:None})

@pytest.mark.parametrize('foreign',['numpy','Python-LICENSE.txt'])
def test_openssl_evidence_rejects_unrelated_apache_files(tmp_path,foreign):
    review=runpy.run_path(str(ROOT/'packaging/review_candidate.py'))
    target=tmp_path/'licenses'/foreign;target.parent.mkdir();target.write_text((ROOT/'packaging/third-party/OpenSSL-LICENSE.txt').read_text())
    with pytest.raises(ValueError,match='OpenSSL'):
        review['openssl_license_evidence'](tmp_path)

def test_openssl_evidence_is_exact_dedicated_material(tmp_path):
    review=runpy.run_path(str(ROOT/'packaging/review_candidate.py'))
    licenses=tmp_path/'licenses';licenses.mkdir()
    for name in ('OpenSSL-LICENSE.txt','RUNTIME-NOTICES.md'):
        (licenses/name).write_bytes((ROOT/'packaging/third-party'/name).read_bytes())
    result=review['openssl_license_evidence'](tmp_path)
    assert result['installed_license']=='licenses/OpenSSL-LICENSE.txt'
    assert len(result['installed_license_sha256'])==64
    (licenses/'OpenSSL-LICENSE.txt').write_text('Apache License Version 2.0 changed')
    with pytest.raises(ValueError,match='OpenSSL'):review['openssl_license_evidence'](tmp_path)

def test_recovery_reports_unsafe_activity_lease_and_preserves_files(tmp_path):
    from slide_core import export
    source=tmp_path/'source';source.write_bytes(b'source')
    tx=export.ExportTransaction(source,export.snapshot_export(source,tmp_path/'out.pdf'))
    tx.prepare(b'pdf',b'json');tx.close()
    journal=tx.journal_path.read_bytes()
    precious=tmp_path/'precious';precious.write_bytes(b'keep')
    tx.activity_path.symlink_to(precious)
    with pytest.raises(export.RecoveryRequired,match='activity'):
        export.recover_export(tmp_path)
    assert precious.read_bytes()==b'keep' and tx.journal_path.read_bytes()==journal
    tx.activity_path.unlink()
    assert export.recover_export(tmp_path)

@pytest.mark.parametrize('early',[False,True])
def test_gui_profile_includes_preparation_and_click_wait(tmp_path,monkeypatch,early):
    from PySide6.QtWidgets import QApplication
    from gui import window as wm,sample_preparation as bg
    from gui.state import State
    from tests.media_fixtures import make_video
    from tests.qt_fixtures import spin
    app=QApplication.instance() or QApplication([])
    monkeypatch.setattr(wm,'gettempdir',lambda:str(tmp_path))
    monkeypatch.setattr(wm,'profile_directory',lambda *a:tmp_path/'profiles')
    source=make_video(tmp_path/'private.mp4',duration=2,fps=4)
    entered=Event();release=Event();real=bg.prepare_samples
    def delayed(*a,**k):
        entered.set()
        while not release.wait(.005):k['cancel_token'].raise_if_cancelled()
        return real(*a,**k)
    monkeypatch.setattr(bg,'prepare_samples',delayed)
    w=wm.Window();w.show()
    try:
        w.open_source(source.path)
        spin(app,lambda:w.controller.state==State.SOURCE_READY and entered.is_set())
        if not early:
            release.set();spin(app,lambda:w._sample_preparation.ready.is_set())
        w.analyze()
        if early:
            # A deterministic gate ensures Analyze contains actual waiting.
            time.sleep(.05);release.set()
        spin(app,lambda:w.controller.state==State.REVIEW_READY)
        report=json.loads(next((tmp_path/'profiles').glob('analysis-*.json')).read_text())
        sec=report['seconds']
        assert sec['preparation_total']>0
        assert sec['click_to_result_total']>=sec['preparation_wait']+sec['total']
        assert report['preparation_status']=='success'
        if early:assert sec['preparation_wait']>=.04
        assert str(source.path) not in json.dumps(report)
    finally:release.set();w.close();spin(app,lambda:not w.isVisible())

def test_preparation_failure_still_writes_profile(tmp_path):
    from gui.window import Window
    from slide_core.media import MediaError
    class Failed:
        def wait(self,token):raise MediaError('private source filename',code='DecodeFailed')
    target=tmp_path/'failure.json'
    with pytest.raises(MediaError):Window._analyze_prepared(None,None,tmp_path,preparation=Failed(),profile_path=target)
    report=json.loads(target.read_text())
    assert report['status']=='failed' and report['error_type']=='MediaError'
    assert report['seconds']['preparation_wait']>=0
    assert 'private source' not in target.read_text()


def test_silent_preparation_failure_has_own_diagnostic(tmp_path,monkeypatch):
    from PySide6.QtWidgets import QApplication
    from gui import window as wm,sample_preparation as bg
    from gui.state import State
    from slide_core.media import MediaError
    from tests.media_fixtures import make_video
    from tests.qt_fixtures import spin
    app=QApplication.instance() or QApplication([])
    monkeypatch.setattr(wm,'gettempdir',lambda:str(tmp_path))
    monkeypatch.setattr(wm,'profile_directory',lambda *a:tmp_path/'profiles')
    def failed(*a,**k):raise MediaError('private-name.mp4 failed',code='DecodeFailed')
    monkeypatch.setattr(bg,'prepare_samples',failed)
    source=make_video(tmp_path/'private-name.mp4',duration=2,fps=4)
    w=wm.Window();w.show()
    try:
        w.open_source(source.path)
        spin(app,lambda:w.controller.state==State.SOURCE_READY and w._sample_preparation.ready.is_set())
        target=next((tmp_path/'profiles').glob('preparation-*.json'))
        report=json.loads(target.read_text())
        assert report['status']=='failed' and report['error_type']=='MediaError'
        assert report['seconds']['preparation_total']>=0
        assert source.path.name not in target.read_text()
    finally:w.close();spin(app,lambda:not w.isVisible())


@pytest.mark.parametrize('layout',['_internal/licenses','Contents/Resources/licenses'])
def test_openssl_evidence_uses_real_installed_layout(tmp_path,layout):
    review=runpy.run_path(str(ROOT/'packaging/review_candidate.py'))
    licenses=tmp_path/layout;licenses.mkdir(parents=True)
    for name in ('OpenSSL-LICENSE.txt','RUNTIME-NOTICES.md'):
        (licenses/name).write_bytes((ROOT/'packaging/third-party'/name).read_bytes())
    evidence=review['openssl_license_evidence'](tmp_path)
    assert evidence['installed_license']==layout+'/OpenSSL-LICENSE.txt'

@pytest.mark.skipif(__import__('os').name!='posix',reason='POSIX flock fault injection; native Windows uses locking')
@pytest.mark.parametrize('error',[__import__('errno').ENOLCK,__import__('errno').EIO])
def test_recovery_reports_lock_system_failure(tmp_path,monkeypatch,error):
    import fcntl,contextlib
    from slide_core import export
    source=tmp_path/'source';source.write_bytes(b'source')
    tx=export.ExportTransaction(source,export.snapshot_export(source,tmp_path/'out.pdf'))
    tx.prepare(b'pdf',b'json');tx.close()
    journal=tx.journal_path.read_bytes()
    def failed(*args):raise OSError(error,'lock system unavailable')
    with monkeypatch.context() as m:
        m.setattr(fcntl,'flock',failed)
        m.setattr(export,'_export_lock_coordinator',contextlib.nullcontext)
        with pytest.raises(export.RecoveryRequired,match='activity'):
            export.recover_export(tmp_path)
    assert tx.journal_path.read_bytes()==journal
    assert export.recover_export(tmp_path)


@pytest.mark.parametrize('unsafe',['ambiguous','symlink'])
def test_openssl_evidence_rejects_unsafe_layout(tmp_path,unsafe):
    review=runpy.run_path(str(ROOT/'packaging/review_candidate.py'))
    data=tmp_path/'_internal/licenses';data.mkdir(parents=True)
    for name in ('OpenSSL-LICENSE.txt','RUNTIME-NOTICES.md'):
        (data/name).write_bytes((ROOT/'packaging/third-party'/name).read_bytes())
    if unsafe=='ambiguous':(tmp_path/'licenses').mkdir()
    else:(tmp_path/'licenses').symlink_to(data,target_is_directory=True)
    with pytest.raises(ValueError,match='OpenSSL'):
        review['openssl_license_evidence'](tmp_path)
