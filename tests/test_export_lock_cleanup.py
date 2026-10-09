import os
import pytest
from slide_core.cache import LeaseBusy
from slide_core.export import ExportTransaction, snapshot_export, recover_export

def transaction(tmp_path):
    source=tmp_path/'source.mp4';source.write_bytes(b'source')
    return ExportTransaction(source,snapshot_export(source,tmp_path/'out.pdf'))

def test_completed_export_removes_lock(tmp_path):
    tx=transaction(tmp_path)
    tx.prepare(b'pdf',b'json');tx.commit();recover_export(tmp_path)
    assert not tx.lock_path.exists()
    assert sorted(p.name for p in tmp_path.iterdir())==['out.json','out.pdf','source.mp4']

def test_export_lease_removes_lock_on_failure(tmp_path):
    from slide_core.export import export_file_lease
    path=tmp_path/'test.lock'
    with pytest.raises(ValueError):
        with export_file_lease(path):
            raise ValueError('failed export')
    assert not path.exists()

def test_export_lease_excludes_competing_owner_and_can_be_reused(tmp_path):
    from slide_core.export import export_file_lease
    path=tmp_path/'test.lock'
    with export_file_lease(path):
        with pytest.raises(LeaseBusy):
            with export_file_lease(path):
                pytest.fail('competing owner acquired lock')
        assert path.exists()
    assert not path.exists()
    with export_file_lease(path):
        assert path.exists()
    assert not path.exists()


@pytest.mark.skipif(os.name == 'nt', reason='Windows denies renaming an open lock handle')
def test_export_lease_never_deletes_replaced_file(tmp_path):
    from slide_core.export import export_file_lease
    path=tmp_path/'test.lock'
    with export_file_lease(path):
        path.rename(tmp_path/'original.lock')
        path.write_bytes(b'unrelated')
    assert path.read_bytes()==b'unrelated'


def test_processes_never_overlap_while_recreating_export_lock(tmp_path):
    import subprocess, sys
    script = """
import os, sys, time
from pathlib import Path
from slide_core.export import export_file_lease
from slide_core.cache import LeaseBusy
root=Path(sys.argv[1])
for i in range(20):
    deadline=time.monotonic()+10
    while True:
        try:
            with export_file_lease(root/'shared.lock'):
                fd=os.open(root/'owner',os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
                os.close(fd)
                time.sleep(.002)
                (root/'owner').unlink()
            break
        except LeaseBusy:
            if time.monotonic()>deadline: raise
            time.sleep(.002)
"""
    processes=[subprocess.Popen([sys.executable,'-c',script,str(tmp_path)],stdout=subprocess.PIPE,stderr=subprocess.PIPE) for _ in range(4)]
    for process in processes:
        stdout,stderr=process.communicate(timeout=20)
        assert process.returncode==0,stderr.decode()
    assert not list(tmp_path.iterdir())
