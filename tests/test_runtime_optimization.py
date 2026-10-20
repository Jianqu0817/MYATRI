"""Offline durability, cadence and clock checks for reduced runtime overhead."""
import json
import sqlite3
from datetime import datetime
from pathlib import Path

import pytest

from myatri.app import Application
from myatri.contracts import Record, TemporaryEntry
from myatri.persona.state import PersonaState
from myatri.storage import ArchiveStore, IntegrityError
from test_persona_lifecycle import setup_state
from test_turn_maintenance import BatchProvider, turns


def test_verified_cache_reuses_bytes_but_isolation_and_tamper_checks_remain(tmp_path, monkeypatch):
    store = ArchiveStore(tmp_path)
    row = store.append_message("user", "原始内容", "raw", nested={"value": "original"})
    store.get_record("raw")
    reads = []
    original = Path.read_bytes

    def observed(path):
        reads.append(path)
        return original(path)

    monkeypatch.setattr(Path, "read_bytes", observed)
    first = store.get_record("raw")
    first.payload["nested"]["value"] = "caller mutation"
    assert store.get_record("raw").payload["nested"]["value"] == "original"
    assert reads == []
    other = ArchiveStore(tmp_path)
    snapshot = store.snapshot()
    other.append_message("user", "来自另一个写入器", "new")
    assert store.get_record("new").body_markdown == "来自另一个写入器"
    assert len(store.list_records(snapshot=snapshot)) == 1
    target = next((store.domain_path / "records").rglob("*.json"))
    data = json.loads(original(target))
    data["body_markdown"] = "被修改"
    target.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(IntegrityError):
        store.list_records()
    assert store.verify_archive()


def test_projection_checkpoint_is_incremental_durable_and_rebuildable(tmp_path, monkeypatch):
    store = ArchiveStore(tmp_path, projection_every=20)
    rebuilds = []
    original = store._rebuild
    monkeypatch.setattr(store, "_rebuild", lambda *args: (rebuilds.append(True), original(*args))[1])
    for i in range(6):
        store.append_message("user", f"消息{i}", f"raw_{i}")
    with sqlite3.connect(store.db_path) as db:
        assert db.execute("SELECT COUNT(*) FROM records").fetchone()[0] == 0
    assert len(store.list_records()) == 6
    store.flush_projection()
    store.flush_projection()
    assert not rebuilds
    with sqlite3.connect(store.db_path) as db:
        assert db.execute("SELECT COUNT(*) FROM records").fetchone()[0] == 6
        assert db.execute("SELECT COUNT(*) FROM records_fts").fetchone()[0] == 6
    store.append_message("user", "尚未投影但已保存", "last")
    recovered = ArchiveStore(tmp_path)
    assert recovered.get_record("last").body_markdown == "尚未投影但已保存"
    with sqlite3.connect(recovered.db_path) as db:
        assert db.execute("SELECT COUNT(*) FROM records").fetchone()[0] == 7


async def test_diagnostic_checkpoint_every_three_turns_and_time_is_visible(tmp_path):
    setup_state(tmp_path)
    provider = BatchProvider()
    config = {"context": {"trace_every_turns": 3, "llm_activation": False,
                          "limit": 1000000, "timezone": "Asia/Shanghai"},
              "cognition": {"maintenance_turns": 30}, "storage": {"projection_every_commits": 20}}
    app = Application(tmp_path, config=config, provider=provider)
    for i in range(4):
        answer = await app.conversation.respond("周末散步期待", message_id=f"chat_{i}")
        protocol = app.queue.get_protocol(f"chat_{i}")
        assert ("messages" in protocol) == (i == 2)
        assert protocol["sent_at"] == app.store.get_record(f"chat_{i}").created_at
        assert protocol["replied_at"] == answer.created_at
    assert len(app.store.list_records("activation")) == 1
    assert len(provider.requests) == 4
    request = provider.requests[-1]
    user = app.store.get_record("chat_3")
    sent = app.conversation.context.message_time(user)
    assert sent.endswith("+08:00")
    assert any(m["role"] == "user" and m["content"] == f"[消息发送时间：{sent}]\n周末散步期待" for m in request.messages)
    assert any(m["content"].startswith("本轮服务端时间") for m in request.messages)
    assert user.body_markdown == "周末散步期待"
    reopened = Application(tmp_path, config=config)
    assert reopened.store.get_record(answer.record_id).ref == answer.ref


async def test_deep_cadence_accumulates_prior_batches_and_force_flushes_on_compaction(tmp_path):
    provider = BatchProvider()
    config = {"context": {"limit": 1000000, "llm_activation": False},
              "cognition": {"maintenance_turns": 2, "deep_every_batches": 2, "persona_every_batches": 3}}
    app = Application(tmp_path, config=config, provider=provider)
    await turns(app, 2)
    assert sum(r.purpose == "A1_batch" for r in provider.requests) == 1
    assert not any(r.role == "reflection" for r in provider.requests)
    assert not any(r.role == "persona_revision" for r in provider.requests)
    assert app.queue.get_meta("deep_pending_messages") == ["turn_0@1", "turn_1@1"]
    app.states.create(TemporaryEntry(text="还想知道对方的研究兴趣", origin_refs=[app.store.list_records("event")[0].ref]))
    # Restart while the accumulated deep-review material has not been processed.
    app = Application(tmp_path, config=config, provider=provider)
    await turns(app, 2, start=2)
    assert any(r.role == "reflection" for r in provider.requests)
    assert not any(r.role == "persona_revision" for r in provider.requests)
    assert app.queue.get_meta("deep_pending_messages") == []
    assert len(app.queue.get_meta("persona_pending_messages")) == 4
    # There are no unprocessed user messages, but deferred personality work
    # must still complete/defer before compression is allowed.
    before = len(provider.requests)
    await app.conversation.context.compactor.acompact()
    roles = [r.role for r in provider.requests[before:]]
    assert roles.index("persona_revision") < roles.index("compaction")
    assert app.queue.get_meta("persona_pending_messages") == []
    assert not app.queue.get_meta("deep_pending_messages")


async def test_persona_review_runs_only_on_its_batch_multiple(tmp_path):
    provider = BatchProvider()
    config = {"context": {"limit": 1000000, "llm_activation": False},
              "cognition": {"maintenance_turns": 1, "deep_every_batches": 2, "persona_every_batches": 3}}
    app = Application(tmp_path, config=config, provider=provider)
    await turns(app, 1)
    app.states.create(TemporaryEntry(text="还想知道对方的研究兴趣", origin_refs=[app.store.list_records("event")[0].ref]))
    await turns(app, 2, start=1)
    assert sum(r.role == "persona_revision" for r in provider.requests) == 1
    assert app.queue.get_meta("maintenance_batch_count") == 3
    assert not app.queue.get_meta("persona_pending_messages")


def test_old_message_timestamp_is_preserved_in_model_context(tmp_path):
    from myatri.conversation.context import ContextBuilder
    from myatri.conversation.budget import TokenBudget
    from myatri.retrieval import RecallService
    store = ArchiveStore(tmp_path)
    PersonaState(store).initialize()
    row = Record(record_id="historic", record_kind="raw_message", created_at="2025-01-01T18:30:00+00:00",
                 body_markdown="明天再谈。", payload={"role": "user"})
    store.commit([row], "historic")
    builder = ContextBuilder(store, RecallService(store), budget=TokenBudget(limit=1000000))
    messages, _ = builder.build_context("你好")
    assert any(m["content"] == "[消息发送时间：2025-01-02T02:30:00+08:00]\n明天再谈。" for m in messages)
    assert store.get_record("historic").created_at == row.created_at
