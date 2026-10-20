from concurrent.futures import ThreadPoolExecutor
import json
import sqlite3

import pytest

from myatri.contracts import Event, Record, SourceSpan, digest
from myatri.storage import ArchiveStore, ArchiveError, ConflictError, IdempotencyError, IntegrityError


def item(record_id="event_a", kind="raw_message", revision=1, **kwargs):
    return Record(record_id=record_id, revision=revision, record_kind=kind, agent_id="atri", user_id="local", body_markdown="原始中文材料", **kwargs)


def test_atomic_batch_snapshot_and_rebuild(tmp_path):
    store = ArchiveStore(tmp_path)
    raw = item()
    first = store.commit([raw], "raw")
    card = item("personality", "persona_version", source_refs=[raw.ref])
    audit = item("change", "persona_change", source_refs=[raw.ref])
    second = store.commit([card, audit], "personality", expected={"personality": 0})
    assert len(store.list_records(snapshot=first)) == 1
    assert store.snapshot() == second
    store.db_path.unlink()
    store.rebuild_projection()
    with sqlite3.connect(store.db_path) as connection:
        assert connection.execute("SELECT count(*) FROM records").fetchone()[0] == 3
        assert connection.execute("SELECT value FROM metadata WHERE key='archive_watermark'").fetchone()[0] == second
        assert connection.execute("SELECT ref FROM records_fts WHERE records_fts MATCH ?", ('"原始中文"',)).fetchall()
    assert store.get_record("personality").source_refs == [raw.ref]
    assert store.verify_archive() == []


def test_cas_new_revision_and_original_immutability(tmp_path):
    store = ArchiveStore(tmp_path)
    store.commit([item()], "raw")
    with pytest.raises(ConflictError):
        store.commit([item(revision=2, supersedes_revision=1)], "rewrite")
    interpretation = item("interpretation", "interpretation", source_refs=["event_a@1"])
    store.commit([interpretation], "interpretation")
    newer = item("interpretation", "interpretation", 2, supersedes_revision=1, source_refs=["event_a@1"])
    store.commit([newer], "rev2", expected={"interpretation": 1})
    assert store.get_record("interpretation", 1).revision == 1
    assert store.get_record("interpretation").revision == 2
    with pytest.raises(ConflictError):
        store.commit([item("other")], "bad_cas", expected={"interpretation": 1})


def test_idempotency_same_and_different_payload(tmp_path):
    store = ArchiveStore(tmp_path)
    record = item()
    commit = store.commit([record], "key")
    assert store.commit([record], "key") == commit
    with pytest.raises(IdempotencyError):
        store.commit([item("other")], "key")
    assert len(store.list_records()) == 1


def test_sources_isolation_and_paths(tmp_path):
    store = ArchiveStore(tmp_path)
    private = ArchiveStore(tmp_path, user_id="someone_else")
    private.append_message("user", "secret", "secret")
    assert store.list_records() == []
    with pytest.raises(KeyError):
        store.get_record("secret")
    with pytest.raises(ArchiveError):
        store.commit([item("guess", source_refs=["secret@1"])], "guess")
    with pytest.raises(ValueError):
        store.commit([item("../escape")], "escape")
    with pytest.raises(ArchiveError):
        store.commit([item("a", source_refs=["b@1"]), item("b", source_refs=["a@1"])], "cycle")
    with pytest.raises(ArchiveError):
        store.get_record("../../secret")
    with pytest.raises(ArchiveError):
        store.list_records(snapshot=private.snapshot())
    store.commit([item("base"), item("derived", "interpretation", source_refs=["base@1"])], "same_batch")


def test_concurrent_cas_has_single_winner(tmp_path):
    stores = [ArchiveStore(tmp_path), ArchiveStore(tmp_path)]
    stores[0].commit([item("state", "persona_version")], "initial")
    def compete(index):
        record = item("state", "persona_version", 2, supersedes_revision=1)
        try:
            stores[index].commit([record], f"worker_{index}", expected={"state": 1})
            return "committed"
        except ConflictError:
            return "conflict"
    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(compete, range(2))) == ["committed", "conflict"]
    assert stores[0].get_record("state").revision == 2


def test_tampered_record_blocks_recovery(tmp_path):
    store = ArchiveStore(tmp_path)
    store.commit([item()], "key")
    path = next((store.domain_path / "records").rglob("*.json"))
    data = json.loads(path.read_text(encoding="utf-8"))
    data["body_markdown"] = "篡改"
    path.write_text(json.dumps(data), encoding="utf-8")
    assert "checksum" in store.verify_archive()[0]
    with pytest.raises(IntegrityError):
        ArchiveStore(tmp_path)


def test_corrupt_projection_recovers_from_authority(tmp_path):
    store = ArchiveStore(tmp_path)
    store.commit([item()], "key")
    store.db_path.write_bytes(b"not sqlite")
    store.recover()
    assert store.get_record("event_a").body_markdown == "原始中文材料"


def test_mutated_nested_payload_rejected_before_publication(tmp_path):
    store = ArchiveStore(tmp_path)
    record = item(payload={"nested": {"fact": "original"}})
    record.payload["nested"]["fact"] = "changed without hash update"
    with pytest.raises(ValueError, match="content hash"):
        store.commit([record], "invalid")
    assert store.snapshot() is None


def test_message_retry_retains_original_timestamp(tmp_path):
    store = ArchiveStore(tmp_path)
    first = store.append_message("user", "消息", "message_1", conversation="a")
    again = store.append_message("user", "消息", "message_1", conversation="a")
    assert again.created_at == first.created_at
    with pytest.raises(IdempotencyError):
        store.append_message("user", "changed", "message_1", conversation="a")


def test_event_span_exact_source_role_and_same_batch(tmp_path):
    store = ArchiveStore(tmp_path)
    raw = Record(record_id="original", record_kind="raw_message", body_markdown="原话不能改变", payload={"role": "user"})
    event = Event(fact_summary="原话", source_spans=[SourceSpan(message_ref=raw.ref, start=0, end=2, quote="原话")], event_fingerprint=digest("source"))
    derived = Record(record_id="event", record_kind="event", source_refs=[raw.ref], body_markdown="原话", payload=event.model_dump(mode="json"))
    store.commit([raw, derived], "same_batch_event")
    invalid = event.model_dump(mode="json")
    invalid["source_spans"][0]["quote"] = "伪造"
    with pytest.raises(ArchiveError, match="quote"):
        store.commit([Record(record_id="invalid", record_kind="event", source_refs=[raw.ref], payload=invalid)], "invalid_quote")
    assistant = store.append_message("assistant", "这只是角色的话", "assistant")
    invalid_role = Event(fact_summary="角色话", source_spans=[SourceSpan(message_ref=assistant.ref, start=0, end=2, quote="这只")], event_fingerprint="role")
    with pytest.raises(ArchiveError, match="user messages"):
        store.commit([Record(record_id="wrong_role", record_kind="event", source_refs=[assistant.ref], payload=invalid_role.model_dump(mode="json"))], "wrong_role")
