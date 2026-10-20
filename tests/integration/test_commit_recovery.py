import pytest
import subprocess
import sys

from myatri.contracts import Record
from myatri.storage import ArchiveStore


@pytest.mark.parametrize("fail_at,visible", [("after_files", 0), ("after_manifest", 2), ("after_projection", 2)])
def test_manifest_last_atomic_recovery(tmp_path, fail_at, visible):
    store = ArchiveStore(tmp_path)
    records = [Record(record_id="card", record_kind="persona_version", body_markdown="card"),
               Record(record_id="audit", record_kind="persona_change", body_markdown="audit", source_refs=["card@1"])]
    with pytest.raises(RuntimeError, match="Injected crash"):
        store.commit(records, "atomic", fail_at=fail_at)
    restarted = ArchiveStore(tmp_path)
    assert len(restarted.list_records()) == visible
    commit_id = restarted.commit(records, "atomic")
    assert len(restarted.list_records()) == 2
    assert restarted.commit(records, "atomic") == commit_id
    assert restarted.verify_archive() == []


@pytest.mark.parametrize("point,visible", [("files", 0), ("manifest", 2), ("projection", 2)])
def test_process_death_releases_writer_and_recovers(tmp_path, point, visible):
    script = r'''
import json, os, sys
from pathlib import Path
from myatri.contracts import Record
from myatri.storage import ArchiveStore
import myatri.storage.archive as module
store = ArchiveStore(Path(sys.argv[1]))
point = sys.argv[2]
original = module._atomic_write
written = 0
def interrupted(path, data):
    global written
    original(path, data)
    if path.parent.name == "commits" and point == "manifest":
        os._exit(79)
    if "records" in path.parts and point == "files":
        written += 1
        if written == 2:
            os._exit(79)
module._atomic_write = interrupted
original_rebuild = store._sync_projection
def interrupted_projection(*args):
    original_rebuild(*args)
    if point == "projection":
        os._exit(79)
store._sync_projection = interrupted_projection
records = [Record(record_id="card", record_kind="persona_version"),
           Record(record_id="audit", record_kind="persona_change", source_refs=["card@1"])]
store.commit(records, "atomic")
'''
    process = subprocess.run([sys.executable, "-c", script, str(tmp_path), point], capture_output=True, text=True, timeout=30)
    assert process.returncode == 79, process.stderr
    recovered = ArchiveStore(tmp_path)
    assert len(recovered.list_records()) == visible
    assert recovered.verify_archive() == []


def test_cross_process_cas_only_one_wins(tmp_path):
    store = ArchiveStore(tmp_path)
    store.commit([Record(record_id="card", record_kind="persona_version")], "initial")
    script = r'''
import sys
from pathlib import Path
from myatri.contracts import Record
from myatri.storage import ArchiveStore, ConflictError
store = ArchiveStore(Path(sys.argv[1]))
record = Record(record_id="card", record_kind="persona_version", revision=2, supersedes_revision=1)
try:
    store.commit([record], sys.argv[2], expected={"card": 1})
    print("committed")
except ConflictError:
    print("conflict")
'''
    processes = [subprocess.Popen([sys.executable, "-c", script, str(tmp_path), f"process_{i}"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True) for i in range(2)]
    outputs = []
    for process in processes:
        stdout, stderr = process.communicate(timeout=30)
        assert process.returncode == 0, stderr
        outputs.append(stdout.strip())
    assert sorted(outputs) == ["committed", "conflict"]
    assert store.get_record("card").revision == 2
