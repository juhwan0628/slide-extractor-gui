import json

import pytest

from slide_core.cache import LeaseBusy, acquire_file_lease
from slide_core.export import (
    ExportTransaction, OutputOverwriteRequired, snapshot_export,
)


def pair(path):
    return tuple(p.read_bytes() if p.exists() else None for p in (path, path.with_suffix('.json')))


def test_prepare_and_commit_publishes_pair_and_journal(tmp_path):
    source = tmp_path / 'source.mp4'; source.write_bytes(b'source')
    target = tmp_path / 'out.pdf'
    tx = ExportTransaction(source, snapshot_export(source, target))
    tx.prepare(b'new pdf', b'new json')
    assert pair(target) == (None, None)
    assert tx.journal_path.exists()
    tx.commit()
    assert pair(target) == (b'new pdf', b'new json')
    assert json.loads(tx.journal_path.read_text())['phase'] == 'COMMITTED'


def test_prepare_failure_keeps_old_pair(tmp_path):
    source = tmp_path / 'source'; source.write_bytes(b's')
    target = tmp_path / 'out.pdf'; target.write_bytes(b'old pdf')
    target.with_suffix('.json').write_bytes(b'old json')
    before = pair(target)
    tx = ExportTransaction(source, snapshot_export(source, target, overwrite=True))
    with pytest.raises(OSError):
        tx.prepare(b'new pdf', b'new json', fail_after=1)
    assert before == pair(target)


def test_commit_failure_restores_old_pair(tmp_path, monkeypatch):
    import slide_core.export as exports
    source = tmp_path / 'source'; source.write_bytes(b's')
    target = tmp_path / 'out.pdf'; target.write_bytes(b'old pdf')
    target.with_suffix('.json').write_bytes(b'old json')
    before = pair(target)
    tx = ExportTransaction(source, snapshot_export(source, target, overwrite=True))
    tx.prepare(b'new pdf', b'new json')
    real_link = exports.os.link
    def fail_publish(src, dst, **kwargs):
        if str(dst).endswith('out.json') and str(src).endswith('1.new'):
            raise OSError('injected publish failure')
        return real_link(src, dst, **kwargs)
    monkeypatch.setattr(exports.os, 'link', fail_publish)
    with pytest.raises(OSError):
        tx.commit()
    assert before == pair(target)


def test_lease_rejects_second_owner(tmp_path):
    lock = tmp_path / 'pair.lock'
    with acquire_file_lease(lock):
        with pytest.raises(LeaseBusy):
            with acquire_file_lease(lock):
                pass


@pytest.mark.parametrize('which', ['pdf', 'json'])
def test_prepare_rejects_staged_symlink_without_truncating_source(tmp_path, which):
    source = tmp_path / 'source'; source.write_bytes(b'precious')
    target = tmp_path / 'out.pdf'
    tx = ExportTransaction(source, snapshot_export(source, target))
    (tx.stage / ('0.new' if which == 'pdf' else '1.new')).symlink_to(source)
    with pytest.raises((OSError, ValueError)):
        tx.prepare(b'new pdf', b'new json')
    assert source.read_bytes() == b'precious'


def test_prepare_rejects_journal_temp_symlink_without_truncating_source(tmp_path):
    source = tmp_path / 'source'; source.write_bytes(b'precious')
    tx = ExportTransaction(source, snapshot_export(source, tmp_path / 'out.pdf'))
    tx.journal_path.with_suffix('.tmp').symlink_to(source)
    with pytest.raises((OSError, ValueError)):
        tx.prepare(b'new pdf', b'new json')
    assert source.read_bytes() == b'precious'


@pytest.mark.parametrize('old', [(), (b'old pdf',), (b'old pdf', b'old json')])
def test_initial_committing_journal_failure_preserves_old_pair(tmp_path, monkeypatch, old):
    import slide_core.export as exports
    source = tmp_path / 'source'; source.write_bytes(b'source')
    target = tmp_path / 'out.pdf'
    for path, data in zip((target, target.with_suffix('.json')), old):
        path.write_bytes(data)
    before = pair(target)
    tx = ExportTransaction(source, snapshot_export(source, target, overwrite=True))
    tx.prepare(b'new pdf', b'new json')
    real_fsync = exports.os.fsync
    count = 0
    def fail_journal_fsync(fd):
        nonlocal count
        count += 1
        # Two staged payloads fsync before the first journal fsync.
        if count == 4:
            raise OSError('ENOSPC')
        return real_fsync(fd)
    monkeypatch.setattr(exports.os, 'fsync', fail_journal_fsync)
    with pytest.raises((OSError, ValueError)):
        tx.commit()
    assert before == pair(target)


def test_rollback_preserves_unknown_target_and_backup(tmp_path, monkeypatch):
    source = tmp_path / 'source'; source.write_bytes(b'source')
    target = tmp_path / 'out.pdf'; target.write_bytes(b'old pdf')
    target.with_suffix('.json').write_bytes(b'old json')
    tx = ExportTransaction(source, snapshot_export(source, target, overwrite=True))
    tx.prepare(b'new pdf', b'new json')
    real_validator = tx.validator
    def mutate_then_validate(*paths):
        if paths == tx.paths:
            paths[0].write_bytes(b'external')
        if real_validator:
            real_validator(*paths)
    tx.validator = mutate_then_validate
    with pytest.raises(ValueError):
        tx.commit()
    assert target.read_bytes() == b'external'
    assert (tx.stage / '0.old').read_bytes() == b'old pdf'
    assert tx.journal_path.exists()


def test_directory_sync_io_error_fails_commit_and_rolls_back(tmp_path, monkeypatch):
    source = tmp_path / 'source'; source.write_bytes(b'source')
    target = tmp_path / 'out.pdf'; target.write_bytes(b'old pdf')
    target.with_suffix('.json').write_bytes(b'old json')
    before = pair(target)
    tx = ExportTransaction(source, snapshot_export(source, target, overwrite=True))
    tx.prepare(b'new pdf', b'new json')
    real_sync = tx._sync_dir
    def fail_once(path):
        if Path(path) == tx.stage:
            raise OSError(5, 'I/O error')
        return real_sync(path)
    from pathlib import Path
    monkeypatch.setattr(tx, '_sync_dir', fail_once)
    with pytest.raises(OSError):
        tx.commit()
    assert before == pair(target)


def test_prepare_stage_replacement_preserves_unowned_directory(tmp_path):
    source = tmp_path / 'source'; source.write_bytes(b'source')
    tx = ExportTransaction(source, snapshot_export(source, tmp_path / 'out.pdf'))
    tx.stage.rename(tmp_path / 'owned-stage')
    tx.stage.mkdir(); (tx.stage / 'unowned.txt').write_bytes(b'keep')
    with pytest.raises(ValueError):
        tx.prepare(b'pdf', b'json')
    assert (tx.stage / 'unowned.txt').read_bytes() == b'keep'


def test_close_stage_replacement_preserves_unowned_directory(tmp_path):
    source = tmp_path / 'source'; source.write_bytes(b'source')
    tx = ExportTransaction(source, snapshot_export(source, tmp_path / 'out.pdf'))
    tx.stage.rename(tmp_path / 'owned-stage')
    tx.stage.mkdir(); (tx.stage / 'unowned.txt').write_bytes(b'keep')
    tx.close()
    assert (tx.stage / 'unowned.txt').read_bytes() == b'keep'


def test_prepare_rejects_preexisting_journal_without_overwrite(tmp_path):
    source = tmp_path / 'source'; source.write_bytes(b'source')
    tx = ExportTransaction(source, snapshot_export(source, tmp_path / 'out.pdf'))
    tx.journal_path.write_bytes(b'foreign journal')
    with pytest.raises((OSError, ValueError)):
        tx.prepare(b'pdf', b'json')
    assert tx.journal_path.read_bytes() == b'foreign journal'


def test_journal_update_rejects_modified_journal(tmp_path):
    source = tmp_path / 'source'; source.write_bytes(b'source')
    tx = ExportTransaction(source, snapshot_export(source, tmp_path / 'out.pdf'))
    tx.prepare(b'pdf', b'json')
    tx.journal_path.write_bytes(b'foreign journal')
    with pytest.raises(ValueError):
        tx.commit()
    assert tx.journal_path.read_bytes() == b'foreign journal'
    assert pair(tmp_path / 'out.pdf') == (None, None)


def test_publish_race_preserves_foreign_target_and_backup(tmp_path, monkeypatch):
    import slide_core.export as exports
    source = tmp_path / 'source'; source.write_bytes(b'source')
    target = tmp_path / 'out.pdf'; target.write_bytes(b'old pdf')
    target.with_suffix('.json').write_bytes(b'old json')
    tx = ExportTransaction(source, snapshot_export(source, target, overwrite=True))
    tx.prepare(b'new pdf', b'new json')
    real_link = exports.os.link
    injected = False
    def race(src, dst, **kwargs):
        nonlocal injected
        if str(src).endswith('0.new') and not injected:
            target.write_bytes(b'foreign output'); injected = True
        return real_link(src, dst, **kwargs)
    monkeypatch.setattr(exports.os, 'link', race)
    with pytest.raises(ValueError):
        tx.commit()
    assert target.read_bytes() == b'foreign output'
    assert (tx.stage / '0.old').read_bytes() == b'old pdf'
    assert tx.journal_path.exists()


def test_rollback_prevalidates_all_backups_before_removing_new_outputs(tmp_path):
    source = tmp_path / 'source'; source.write_bytes(b'source')
    target = tmp_path / 'out.pdf'; target.write_bytes(b'old pdf')
    target.with_suffix('.json').write_bytes(b'old json')
    tx = ExportTransaction(source, snapshot_export(source, target, overwrite=True))
    tx.prepare(b'new pdf', b'new json')
    def mutate_then_fail(*paths):
        if paths == tx.paths:
            (tx.stage / '0.old').write_bytes(b'unknown old')
        raise ValueError('validation failed')
    tx.validator = mutate_then_fail
    with pytest.raises(ValueError):
        tx.commit()
    assert pair(target) == (b'new pdf', b'new json')
    assert (tx.stage / '0.old').read_bytes() == b'unknown old'
    assert (tx.stage / '1.old').read_bytes() == b'old json'


def test_backup_destination_collision_does_not_move_source(tmp_path):
    source = tmp_path / 'source'; source.write_bytes(b'source')
    target = tmp_path / 'out.pdf'; target.write_bytes(b'old pdf')
    target.with_suffix('.json').write_bytes(b'old json')
    tx = ExportTransaction(source, snapshot_export(source, target, overwrite=True))
    tx.prepare(b'new pdf', b'new json')
    (tx.stage / '0.old').write_bytes(b'foreign backup')
    with pytest.raises(ValueError):
        tx.commit()
    assert source.read_bytes() == b'source'
    assert (tx.stage / '0.old').read_bytes() == b'foreign backup'

def test_lock_symlink_refused_without_writing_target(tmp_path):
    from slide_core.cache import acquire_file_lease, LeaseBusy
    target=tmp_path/"precious.txt";target.write_bytes(b"precious")
    link=tmp_path/"pair.lock";link.symlink_to(target)
    with pytest.raises(LeaseBusy):
        with acquire_file_lease(link):pass
    assert target.read_bytes()==b"precious"


def test_lock_hardlink_refused_without_writing_target(tmp_path):
    import os
    from slide_core.cache import acquire_file_lease, LeaseBusy
    target=tmp_path/"precious.txt";target.write_bytes(b"precious")
    alias=tmp_path/"pair.lock";os.link(target,alias)
    with pytest.raises(LeaseBusy):
        with acquire_file_lease(alias):pass
    assert target.read_bytes()==b"precious"


def test_lock_regular_reusable_after_release(tmp_path):
    from slide_core.cache import acquire_file_lease
    lock=tmp_path/"normal.lock"
    with acquire_file_lease(lock):
        pass
    with acquire_file_lease(lock):
        pass
