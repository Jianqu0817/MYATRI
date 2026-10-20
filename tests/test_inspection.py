import json
import zipfile

import pytest

from myatri.app import Application
from myatri.interfaces.inspect import backup, doctor, restore_backup


async def test_backup_restores_archive_persona_and_queue_to_new_directory(tmp_path):
    app = Application(tmp_path / "original")
    await app.conversation.respond("共同安排改变时，我希望提前沟通。", message_id="test_message")
    await app.drain()
    original_snapshot = app.store.snapshot()
    path = backup(app, tmp_path / "backup.zip")
    target = restore_backup(path, tmp_path / "restored")
    recovered = Application(target)
    assert recovered.store.snapshot() == original_snapshot
    assert recovered.persona.read_state().content_hash == app.persona.read_state().content_hash
    assert recovered.queue.list_jobs() == app.queue.list_jobs()
    assert doctor(recovered)["ok"]
    with pytest.raises(ValueError): restore_backup(path, tmp_path / "restored")
    with pytest.raises(ValueError): backup(app, app.root / "nested.zip")


def test_restore_rejects_zip_path_escape(tmp_path):
    source = tmp_path / "bad.zip"
    with zipfile.ZipFile(source, "w") as bundle:
        bundle.writestr("../escape.txt", "do not extract")
    with pytest.raises(ValueError): restore_backup(source, tmp_path / "target")
    assert not (tmp_path / "escape.txt").exists()
