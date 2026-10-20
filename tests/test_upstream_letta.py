"""Fault checks for the Letta Code snapshot-write adaptation, without API IO."""
import os
from pathlib import Path
from types import SimpleNamespace

import pytest

from myatri._vendor import letta
from myatri.contracts import Record
from myatri.memory.index import MemoryIndex
from myatri.storage.archive import ArchiveStore, _atomic_write


def test_publishes_exact_binary_snapshot_and_removes_temporary_file(tmp_path):
    target = tmp_path / "nested" / "snapshot.json"
    before = b"old snapshot"
    target.parent.mkdir()
    target.write_bytes(before)
    after = "中文\x00\r\n😀".encode("utf-8") + bytes(range(256))
    _atomic_write(target, after)
    assert target.read_bytes() == after
    assert list(target.parent.iterdir()) == [target]
    if os.name != "nt":
        assert target.stat().st_mode & 0o777 == 0o600


@pytest.mark.parametrize("failure", ["write", "fsync", "rename"])
def test_before_publication_failures_preserve_old_snapshot_and_remove_temp(tmp_path, monkeypatch, failure):
    target = tmp_path / "snapshot.json"
    before = b"previous complete snapshot"
    target.write_bytes(before)
    injected = OSError(f"injected {failure} failure")
    original_fdopen = letta.os.fdopen

    class PartialWriteFailure:
        def __init__(self, stream):
            self.stream = stream

        def __enter__(self):
            self.stream.__enter__()
            return self

        def __exit__(self, *args):
            return self.stream.__exit__(*args)

        def write(self, data):
            self.stream.write(data[:3])
            self.stream.flush()
            raise injected

        def close(self):
            self.stream.close()

    def fail(*args, **kwargs):
        raise injected

    if failure == "write":
        monkeypatch.setattr(letta.os, "fdopen", lambda *a, **kw: PartialWriteFailure(original_fdopen(*a, **kw)))
    elif failure == "fsync":
        monkeypatch.setattr(letta.os, "fsync", fail)
    else:
        monkeypatch.setattr(letta.os, "replace", fail)
    with pytest.raises(OSError) as caught:
        _atomic_write(target, b"new complete snapshot")
    assert caught.value is injected
    assert target.read_bytes() == before
    assert list(tmp_path.iterdir()) == [target]


def test_exclusive_temp_collision_never_deletes_another_writers_file(tmp_path, monkeypatch):
    target = tmp_path / "snapshot.json"
    target.write_bytes(b"old snapshot")
    temporary = tmp_path / ".snapshot.json.collision.tmp"
    temporary.write_bytes(b"another writer owns this")
    monkeypatch.setattr(letta.uuid, "uuid4", lambda: SimpleNamespace(hex="collision"))
    with pytest.raises(FileExistsError):
        _atomic_write(target, b"new snapshot")
    assert target.read_bytes() == b"old snapshot"
    assert temporary.read_bytes() == b"another writer owns this"


def test_cleanup_error_does_not_hide_the_primary_rename_error(tmp_path, monkeypatch):
    target = tmp_path / "snapshot.json"
    target.write_bytes(b"old snapshot")
    primary = OSError("rename failed")
    original_unlink = Path.unlink

    def fail_replace(*args):
        raise primary

    def fail_cleanup(path, *args, **kwargs):
        if path.suffix == ".tmp":
            raise PermissionError("temporary file still locked")
        return original_unlink(path, *args, **kwargs)

    monkeypatch.setattr(letta.os, "replace", fail_replace)
    with monkeypatch.context() as cleanup_patch:
        cleanup_patch.setattr(Path, "unlink", fail_cleanup)
        with pytest.raises(OSError) as caught:
            _atomic_write(target, b"new snapshot")
    assert caught.value is primary
    assert target.read_bytes() == b"old snapshot"
    # A filesystem refusal makes immediate cleanup impossible; it must not
    # disguise the publication error. Remove this synthetic residue now.
    for temporary in tmp_path.glob("*.tmp"):
        temporary.unlink()


def test_descriptor_close_error_does_not_replace_a_primary_fsync_error(tmp_path, monkeypatch):
    target = tmp_path / "snapshot.json"
    target.write_bytes(b"old snapshot")
    primary = OSError("file fsync failed")
    real_close = os.close

    def failed_fsync(fd):
        raise primary

    def failed_close(fd):
        real_close(fd)
        raise OSError("descriptor close failed too")

    proxy = SimpleNamespace(**vars(os))
    proxy.fsync, proxy.close = failed_fsync, failed_close
    monkeypatch.setattr(letta, "os", proxy)
    with pytest.raises(OSError) as caught:
        _atomic_write(target, b"new snapshot")
    assert caught.value is primary
    assert target.read_bytes() == b"old snapshot"
    assert list(tmp_path.iterdir()) == [target]


@pytest.mark.parametrize("directory_sync_fails", [False, True])
def test_posix_directory_sync_occurs_after_rename_and_reports_failure(tmp_path, monkeypatch, directory_sync_fails):
    target = tmp_path / "snapshot.json"
    target.write_bytes(b"old snapshot")
    proxy = SimpleNamespace(**vars(os))
    proxy.name = "posix"
    real_open, real_fsync, real_close = os.open, os.fsync, os.close
    directory_fd = -99
    operations = []
    primary = OSError("directory fsync failed")

    def observed_open(path, flags, mode=0o777):
        if Path(path) == target.parent:
            assert target.read_bytes() == b"new snapshot"
            operations.append("directory_open")
            return directory_fd
        assert mode == 0o600
        assert flags & os.O_CREAT and flags & os.O_EXCL
        if os.name == "nt":
            assert flags & os.O_BINARY
        return real_open(path, flags, mode)

    def observed_fsync(fd):
        if fd == directory_fd:
            operations.append("directory_fsync")
            if directory_sync_fails:
                raise primary
        else:
            operations.append("file_fsync")
            real_fsync(fd)

    def observed_close(fd):
        if fd == directory_fd:
            operations.append("directory_close")
        else:
            real_close(fd)

    proxy.open, proxy.fsync, proxy.close = observed_open, observed_fsync, observed_close
    monkeypatch.setattr(letta, "os", proxy)
    if directory_sync_fails:
        with pytest.raises(OSError) as caught:
            _atomic_write(target, b"new snapshot")
        assert caught.value is primary
    else:
        _atomic_write(target, b"new snapshot")
    assert operations == ["file_fsync", "directory_open", "directory_fsync", "directory_close"]
    assert target.read_bytes() == b"new snapshot"
    assert list(tmp_path.iterdir()) == [target]


@pytest.mark.asyncio
async def test_archive_and_memory_index_use_the_adapted_writer(tmp_path, monkeypatch):
    import myatri.storage.archive as archive

    actual_write = letta.atomic_write
    destinations = []

    def observed_write(path, data):
        destinations.append(path)
        actual_write(path, data)

    monkeypatch.setattr(archive, "atomic_write", observed_write)
    store = ArchiveStore(tmp_path / "archive")
    store.commit([Record(record_id="raw", record_kind="raw_message", body_markdown="原始材料")], "raw")
    index = MemoryIndex(store)
    await index.rebuild()
    assert any(path.parent.name == "commits" for path in destinations)
    assert any("records" in path.parts for path in destinations)
    assert any(path.parent.name == "generations" for path in destinations)
    assert any(path.name == "current.json" for path in destinations)
    assert store.verify_archive() == []
