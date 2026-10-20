import importlib.util
import json
from pathlib import Path
import sqlite3

import pytest

from myatri.app import Application
from myatri.contracts import Event, Record, SourceSpan, digest
from myatri.persona.patch import PersonaPatcher


PROJECT = Path(__file__).resolve().parents[1]


def test_inherit_retains_all_versions_and_runtime_with_new_persona(tmp_path, monkeypatch):
    monkeypatch.syspath_prepend(str(PROJECT / "scripts"))
    spec = importlib.util.spec_from_file_location("memory_inheritance", PROJECT / "scripts/inherit_atri_memory.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    source, target = tmp_path / "ATRI", tmp_path / "小温暖"
    app = Application(source)
    message = app.store.append_message("user", "我喜欢研究政治经济学。", "interest")
    app.store.append_message("assistant", "我记得你喜欢政治经济学。", "answer", reply_to=message.ref)
    facts = Event(fact_summary="用户喜欢政治经济学", event_fingerprint=digest(message.ref),
                  source_spans=[SourceSpan(message_ref=message.ref, start=0,
                                           end=len(message.body_markdown), quote=message.body_markdown)])
    event = Record(record_id="study", record_kind="event", source_refs=[message.ref],
                   body_markdown="用户说喜欢政治经济学。", payload=facts.model_dump())
    app.store.commit([event], idempotency_key="study")
    PersonaPatcher(app.store).human_edit("P02", "我会尊重交流中的分歧。", "人工调整")
    app.queue.set_meta("last_activity", message.created_at)
    with app.queue.db() as db:
        db.execute("INSERT INTO usage(agent,user,payload) VALUES ('atri','local',?)",
                   (json.dumps({"tokens": 123}),))
    before_files = {str(p.relative_to(source)): p.read_bytes() for p in source.rglob("*.json")}
    before_snapshot = app.store.snapshot()
    report = module.inherit(source, target, tmp_path / "backup.zip",
                            PROJECT / "config/personas/xiaowennuan/persona.md")
    assert report["doctor_ok"] and report["index_current"]
    assert report["current_persona"] == "persona@3"
    copied = Application(target, config={"context": {"limit": 1000000, "compact_at": 650000}})
    assert "小温暖" in copied.persona.read_state().body_markdown
    assert "ATRI 记忆继承" in copied.persona.read_state().payload["entries"]["P14_memory_continuity"]
    assert copied.store.get_record(message.record_id).model_dump() == message.model_dump()
    assert copied.store.get_record("persona", revision=1).model_dump() == app.store.get_record("persona", revision=1).model_dump()
    assert copied.queue.get_meta("last_activity") == message.created_at
    with sqlite3.connect(target / "runtime.sqlite3") as db:
        assert db.execute("SELECT COUNT(*) FROM usage").fetchone()[0] == 1
    assert app.store.snapshot() == before_snapshot
    assert all((source / name).read_bytes() == data for name, data in before_files.items())
    assert copied.recall.recall("政治经济学").records
    old_reply = copied.store.get_record("answer")
    messages, _ = copied.conversation.context.build_context("你是谁？")
    assert not any(row["role"] == "assistant" and row["content"] == old_reply.body_markdown for row in messages)
    inherited_block = next(row["content"] for row in messages if row["content"].startswith("继承历史档案"))
    assert message.body_markdown in inherited_block and old_reply.body_markdown in inherited_block
    assert messages[-1]["content"].startswith("本轮当前身份")
    assert "小温暖" in messages[-1]["content"]
    inherited_snapshot = copied.persona.read_state().payload["inherited_snapshot"]
    PersonaPatcher(copied.store).human_edit("P07_language", "自然中文。", "人工调整措辞")
    assert copied.persona.read_state().payload["inherited_snapshot"] == inherited_snapshot
    current = copied.persona.read_state()
    new_entries = {**current.payload["entries"], "extra": "测试条目"}
    replacement = PersonaPatcher(copied.store).human_replace(new_entries, "人工完整修改卡片")
    assert replacement.payload["inherited_snapshot"] == inherited_snapshot
    assert copied.store.get_record("persona", revision=current.revision).model_dump() == current.model_dump()
    with pytest.raises(ValueError, match="Target already exists"):
        module.inherit(source, target, tmp_path / "again.zip",
                       PROJECT / "config/personas/xiaowennuan/persona.md")
    assert not (tmp_path / "again.zip").exists()
