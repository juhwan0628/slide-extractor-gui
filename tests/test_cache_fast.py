import json,os,subprocess,sys,time
from pathlib import Path
import pytest
from slide_core.cache import CacheSession,CacheBudgetExceeded,prune_cache
from tests.test_cache import jpeg

def test_temporary_cache_does_not_force_disk_sync(tmp_path,monkeypatch):
    # On POSIX the lease itself needs no fsync. PDF transactions are untouched.
    if os.name=='nt':pytest.skip('Windows lease initialization sync is intentional')
    def forbidden(*args):raise AssertionError('Temporary cache forced disk sync')
    monkeypatch.setattr(os,'fsync',forbidden)
    with CacheSession(tmp_path,min_free_bytes=0) as session:
        path=session.write_jpeg(0,jpeg());session.complete()
        assert path.read_bytes()==jpeg()
        assert json.loads((session.directory/'manifest.json').read_text())['complete']

def test_small_writes_do_not_rescan_root_or_rewrite_every_manifest(tmp_path,monkeypatch):
    original=Path.iterdir;scans=[];updates=[]
    def tracked(path):
        if path==tmp_path:scans.append(path)
        return original(path)
    monkeypatch.setattr(Path,'iterdir',tracked)
    with CacheSession(tmp_path,min_free_bytes=0) as session:
        write=session._write_manifest
        def manifest(done):updates.append(done);return write(done)
        monkeypatch.setattr(session,'_write_manifest',manifest)
        for i in range(100):session.write_jpeg(i,jpeg())
        session.complete()
        assert len(scans)<=3
        assert len(updates)<=5
        assert json.loads((session.directory/'manifest.json').read_text())['bytes']==100*len(jpeg())

def test_reservations_prevent_concurrent_root_overbooking_and_release(tmp_path):
    data=jpeg()
    a=CacheSession(tmp_path,min_free_bytes=0,root_limit=4096)
    b=CacheSession(tmp_path,min_free_bytes=0,root_limit=4096)
    try:
        a.write_jpeg(0,data)
        with pytest.raises(CacheBudgetExceeded):b.write_jpeg(0,data)
        a.close()
        assert b.write_jpeg(0,data).read_bytes()==data
    finally:a.close();b.close()

def test_crashed_session_reservation_is_reclaimed(tmp_path):
    script="from slide_core.cache import CacheSession; from tests.test_cache import jpeg; import os; s=CacheSession(%r,min_free_bytes=0,root_limit=4096); s.write_jpeg(0,jpeg()); os._exit(0)" % str(tmp_path)
    subprocess.run([sys.executable,'-c',script],check=True,timeout=10)
    with CacheSession(tmp_path,min_free_bytes=0,root_limit=4096) as s:
        assert s.write_jpeg(0,jpeg()).is_file()

def test_partial_manifest_is_safe_to_prune_after_close(tmp_path):
    with CacheSession(tmp_path,min_free_bytes=0) as s:
        for i in range(7):s.write_jpeg(i,jpeg())
    assert s.directory in prune_cache(tmp_path,now=time.time()+4000)


def test_two_processes_cannot_reserve_same_root_capacity(tmp_path):
    program="""
import sys,time
from pathlib import Path
from slide_core.cache import CacheSession,CacheBudgetExceeded
from tests.test_cache import jpeg
root=Path(sys.argv[1])
with CacheSession(root,min_free_bytes=0,root_limit=4096) as s:
    try:
        s.write_jpeg(0,jpeg())
        print('reserved',flush=True)
    except CacheBudgetExceeded:
        print('blocked',flush=True)
    deadline=time.monotonic()+5
    while not (root/'release').exists() and time.monotonic()<deadline:time.sleep(.01)
"""
    children=[subprocess.Popen([sys.executable,'-c',program,str(tmp_path)],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True) for _ in range(2)]
    try:
        results=[child.stdout.readline().strip() for child in children]
        assert sorted(results)==['blocked','reserved']
    finally:
        (tmp_path/'release').touch()
        for child in children:
            out,err=child.communicate(timeout=10)
            assert child.returncode==0,err
