"""Crash/restart recovery tests using only synthetic scratch outputs."""
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from slide_core.export import ExportTransaction, RecoveryRequired, recover_export, snapshot_export


def seed_pair(root, *, old_pdf=b"old-pdf", old_json=b"old-json"):
    src=root/"source.mp4";src.write_bytes(b"pretend-video")
    pdf=root/"out.pdf"
    if old_pdf is not None:pdf.write_bytes(old_pdf)
    if old_json is not None:pdf.with_suffix(".json").write_bytes(old_json)
    return src,pdf


def pair(pdf):
    return (pdf.read_bytes() if pdf.exists() else None,
            pdf.with_suffix(".json").read_bytes() if pdf.with_suffix(".json").exists() else None)


@pytest.mark.parametrize("old",[
    (None,None),(b"old-pdf",None),(None,b"old-json"),(b"old-pdf",b"old-json")])
def test_prepared_recovers_original_pair(tmp_path,old):
    src,pdf=seed_pair(tmp_path,old_pdf=old[0],old_json=old[1])
    tx=ExportTransaction(src,snapshot_export(src,pdf,overwrite=True))
    tx.prepare(b"new-pdf",b"new-json")
    assert pair(pdf)==old
    assert recover_export(tmp_path)[0][1]=="rolled_back"
    assert pair(pdf)==old
    assert recover_export(tmp_path)==()
    assert not list(tmp_path.glob(".slide-export-*"))


def test_committed_keeps_new_pair_and_removes_known_artifacts(tmp_path):
    src,pdf=seed_pair(tmp_path)
    tx=ExportTransaction(src,snapshot_export(src,pdf,overwrite=True))
    tx.prepare(b"new-pdf",b"new-json")
    tx.commit()
    assert pair(pdf)==(b"new-pdf",b"new-json")
    assert recover_export(tmp_path)==((tx.export_id,"committed"),)
    assert pair(pdf)==(b"new-pdf",b"new-json")
    assert recover_export(tmp_path)==()


@pytest.mark.parametrize("after",range(1,9))
def test_recovery_from_process_exit_after_each_rename(tmp_path,after):
    src,pdf=seed_pair(tmp_path)
    program = """
from pathlib import Path
from slide_core import export
import os
src=Path({source!r});pdf=Path({destination!r})
tx=export.ExportTransaction(src,export.snapshot_export(src,pdf,overwrite=True))
tx.prepare(b"new-pdf",b"new-json")
original=export.os.replace
number=[0]
def crash_after_replace(src,dst,*args,**kwargs):
    result=original(src,dst,*args,**kwargs)
    number[0]+=1
    if number[0]=={after}:
        os._exit(77)
    return result
export.os.replace=crash_after_replace
tx.commit()
os._exit(0)
""".format(source=str(src),destination=str(pdf),after=after)
    child=subprocess.run([sys.executable,"-c",program],cwd=Path(__file__).resolve().parents[1],
                         capture_output=True,timeout=10)
    assert child.returncode==77,(after,child.stderr.decode())
    assert recover_export(tmp_path)[0][1] in ("rolled_back","committed")
    # COMMITTED journal is the only circumstance under which new pair survives.
    assert pair(pdf) in ((b"old-pdf",b"old-json"),(b"new-pdf",b"new-json"))
    assert pair(pdf)==((b"new-pdf",b"new-json") if after==8 else (b"old-pdf",b"old-json"))
    assert recover_export(tmp_path)==()


@pytest.mark.parametrize("after", (1,2))
def test_recovery_after_crash_during_publish_link(tmp_path,after):
    src,pdf=seed_pair(tmp_path)
    program="""
from pathlib import Path
from slide_core import export
import os
src=Path({source!r});pdf=Path({destination!r})
tx=export.ExportTransaction(src,export.snapshot_export(src,pdf,overwrite=True))
tx.prepare(b"new-pdf",b"new-json")
original=export.os.link
number=[0]
def crash_after_link(src,dst,*args,**kwargs):
    result=original(src,dst,*args,**kwargs)
    number[0]+=1
    if number[0]=={after}:os._exit(77)
    return result
export.os.link=crash_after_link
tx.commit()
os._exit(0)
""".format(source=str(src),destination=str(pdf),after=after)
    child=subprocess.run([sys.executable,"-c",program],cwd=Path(__file__).resolve().parents[1],
                         capture_output=True,timeout=10)
    assert child.returncode==77,child.stderr.decode()
    assert recover_export(tmp_path)[0][1]=="rolled_back"
    assert pair(pdf)==(b"old-pdf",b"old-json")


def test_recovery_is_fail_closed_for_changed_target(tmp_path):
    src,pdf=seed_pair(tmp_path)
    tx=ExportTransaction(src,snapshot_export(src,pdf,overwrite=True))
    tx.prepare(b"new-pdf",b"new-json")
    journal=json.loads(tx.journal_path.read_text())
    journal["phase"]="COMMITTING"
    tx.journal_path.write_text(json.dumps(journal))
    pdf.write_bytes(b"external-content")
    before=pair(pdf)
    with pytest.raises(RecoveryRequired):
        recover_export(tmp_path)
    assert pair(pdf)==before
    assert tx.journal_path.exists()


def test_corrupt_journal_does_not_remove_unknown_files(tmp_path):
    src,pdf=seed_pair(tmp_path)
    tx=ExportTransaction(src,snapshot_export(src,pdf,overwrite=True))
    tx.prepare(b"new-pdf",b"new-json")
    tx.journal_path.write_bytes(b"not-json")
    other=tx.stage/"unknown.txt";other.write_bytes(b"do-not-delete")
    with pytest.raises(RecoveryRequired):
        recover_export(tmp_path)
    assert other.read_bytes()==b"do-not-delete"
    assert pair(pdf)==(b"old-pdf",b"old-json")


def test_recovery_rejects_symlink_stage_and_path_traversal(tmp_path):
    src,pdf=seed_pair(tmp_path)
    tx=ExportTransaction(src,snapshot_export(src,pdf,overwrite=True))
    tx.prepare(b"new-pdf",b"new-json")
    record=json.loads(tx.journal_path.read_text())
    record["targets"]=["../../unsafe.pdf","out.json"]
    tx.journal_path.write_text(json.dumps(record))
    with pytest.raises(RecoveryRequired):recover_export(tmp_path)
    assert pair(pdf)==(b"old-pdf",b"old-json")


def test_recovery_validator_rejects_mismatched_new_pair(tmp_path):
    src,pdf=seed_pair(tmp_path)
    tx=ExportTransaction(src,snapshot_export(src,pdf,overwrite=True))
    tx.prepare(b"new-pdf",b"new-json");tx.commit()
    with pytest.raises(RecoveryRequired):
        recover_export(tmp_path, validator=lambda *args: (_ for _ in ()).throw(ValueError("bad UUID")))
    assert pair(pdf)==(b"new-pdf",b"new-json")
    assert tx.journal_path.exists()


@pytest.mark.parametrize("after",range(1,15))
def test_recovery_after_process_exit_post_fsync(tmp_path,after):
    src,pdf=seed_pair(tmp_path)
    program="""
from pathlib import Path
from slide_core import export
import os
src=Path({source!r});pdf=Path({destination!r})
tx=export.ExportTransaction(src,export.snapshot_export(src,pdf,overwrite=True))
tx.prepare(b"new-pdf",b"new-json")
original=export.os.fsync
number=[0]
def crash_after_fsync(fd):
    result=original(fd)
    number[0]+=1
    if number[0]=={after}:os._exit(77)
    return result
export.os.fsync=crash_after_fsync
tx.commit()
os._exit(0)
""".format(source=str(src),destination=str(pdf),after=after)
    child=subprocess.run([sys.executable,"-c",program],
                         cwd=Path(__file__).resolve().parents[1],
                         capture_output=True,timeout=10)
    assert child.returncode in (0,77),(after,child.stderr.decode())
    result=recover_export(tmp_path)
    assert len(result)==1
    expected=((b"new-pdf",b"new-json") if result[0][1]=="committed"
              else (b"old-pdf",b"old-json"))
    assert pair(pdf)==expected
    assert recover_export(tmp_path)==()
