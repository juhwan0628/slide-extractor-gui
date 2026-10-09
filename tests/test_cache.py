import json
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest
from slide_core.cache import (CacheBudgetExceeded, CacheSession, UnsafeCache,
                              prune_cache, acquire_file_lease, LeaseBusy)

# Tiny valid JPEG fixture generated in memory; no copyrighted media.
def jpeg():
    from PIL import Image
    from io import BytesIO
    stream=BytesIO();Image.new('RGB',(8,8),'blue').save(stream,format='JPEG');return stream.getvalue()


def test_owned_session_writes_jpegs_and_completes(tmp_path):
    with CacheSession(tmp_path,min_free_bytes=0) as session:
        data=jpeg();file=session.write_jpeg(0,data)
        assert file.read_bytes()==data
        with pytest.raises(UnsafeCache):session.write_jpeg(0,data)
        session.complete()
        record=json.loads((session.directory/'manifest.json').read_text())
        assert record['complete'] and record['bytes']==len(data)
        assert prune_cache(tmp_path,now=time.time()+100000)==()
    assert prune_cache(tmp_path,now=time.time()+100000)==(session.directory,)
    assert not session.directory.exists()


def test_budget_limits_are_fail_closed(tmp_path):
    data=jpeg()
    with CacheSession(tmp_path,min_free_bytes=0,session_limit=len(data)-1) as session:
        with pytest.raises(CacheBudgetExceeded):session.write_jpeg(0,data)
        assert not (session.directory/'00000000.jpg').exists()
    with CacheSession(tmp_path,min_free_bytes=10**20) as session:
        with pytest.raises(CacheBudgetExceeded):session.write_jpeg(0,data)


def test_session_manifest_not_owned_is_not_removed(tmp_path):
    foreign=tmp_path/'session-foreign';foreign.mkdir()
    (foreign/'manifest.json').write_text('{}')
    assert prune_cache(tmp_path,now=time.time()+100000)==()
    assert foreign.exists()


def test_symlink_sample_is_never_removed(tmp_path):
    precious=tmp_path/'precious';precious.write_bytes(b'keep')
    with CacheSession(tmp_path,min_free_bytes=0) as session:
        (session.directory/'00000000.jpg').symlink_to(precious)
    assert prune_cache(tmp_path,now=time.time()+100000)==()
    assert precious.read_bytes()==b'keep'


def test_ttl_complete_vs_incomplete(tmp_path):
    incomplete=CacheSession(tmp_path,min_free_bytes=0)
    completed=CacheSession(tmp_path,min_free_bytes=0)
    completed.complete()
    names=(incomplete.directory,completed.directory)
    incomplete.close();completed.close()
    # TTL from a stable simulated current time; no OS mtime rewriting needed.
    now=time.time()
    removed=prune_cache(tmp_path,now=now+3700)
    assert removed==(names[0],)
    assert names[1].exists()
    assert prune_cache(tmp_path,now=now+90000)==(names[1],)


def test_two_process_lock_contention(tmp_path):
    lock=tmp_path/'lock'
    with acquire_file_lease(lock):
        child=subprocess.run([sys.executable,'-c',
            "from slide_core.cache import acquire_file_lease,LeaseBusy;from pathlib import Path\n"
            f"\ntry:\n with acquire_file_lease(Path({str(lock)!r})): exit(3)\n"
            "except LeaseBusy:exit(0)\n"],
            cwd=Path(__file__).resolve().parents[1],timeout=10)
        assert child.returncode==0
    with acquire_file_lease(lock):pass


def test_crash_releases_os_lock(tmp_path):
    lock=tmp_path/'lock'
    program=("import os\nfrom slide_core.cache import acquire_file_lease\n"
             f"with acquire_file_lease({str(lock)!r}):\n os._exit(0)\n")
    child=subprocess.run([sys.executable,'-c',program],
                         cwd=Path(__file__).resolve().parents[1],timeout=10)
    assert child.returncode==0
    with acquire_file_lease(lock):pass
