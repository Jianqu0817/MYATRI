from myatri.app import Application
from myatri.contracts import Record
from myatri.memory.imports import import_history
from myatri.persona.patch import PersonaPatcher
from myatri.persona.temporary import event_roots


def test_import_preserves_every_original_and_group_history_without_replaying_private_turns(tmp_path):
    source = Application(tmp_path / "private")
    original = Record(record_id="old_user", record_kind="raw_message", author_kind="human",
                      body_markdown="我叫菅蘧，喜欢吃草莓。", payload={"role": "user"})
    source.store.commit([original], idempotency_key="old-message")
    PersonaPatcher(source.store).human_edit("P02", "保留旧记忆和新的判断。", "测试版本链迁移")
    target = Application(tmp_path / "group", "xiaowennuan", "group",
                         config={"context": {"limit": 1000000, "llm_activation": False}})
    group_message = Record(record_id="group_user", record_kind="raw_message", agent_id="xiaowennuan",
                           user_id="group", body_markdown="我是另一个群成员。", payload={"role": "user"})
    target.store.commit([group_message], idempotency_key="group-message")
    report = import_history(source.store, target.store, owner_label="菅蘧")
    imported = target.recall.read_record(report["original_to_import"][original.ref])
    assert imported.payload["original"] == original.model_dump(mode="json")
    assert imported.created_at == original.created_at
    _, originals = source.store._load()
    for ref, record in originals.items():
        copied = target.recall.read_record(report["original_to_import"][ref])
        assert copied.payload["original"] == record.model_dump(mode="json")
        assert all(report["original_to_import"][r] in copied.source_refs for r in record.source_refs)
    assert event_roots(target.store, [imported.ref]) == []
    assert target.store.list_records("raw_message") == [group_message]
    assert target.store.get_record("persona").revision == 1
    count = len(target.store.list_records())
    assert import_history(source.store, target.store, owner_label="菅蘧") == report
    assert len(target.store.list_records()) == count
    assert not source.store.verify_archive() and not target.store.verify_archive()
    assert any(r.ref == imported.ref for r in target.recall.recall("喜欢吃草莓").records)
    messages, _ = target.conversation.context.build_context("喜欢吃草莓")
    explanation = target.conversation.context.explain_context()
    block = next(m["content"] for m in messages if "用户授权迁入的原私聊历史" in m["content"])
    assert "喜欢吃草莓" in block and "原角色：user" in block and imported.ref in block
    assert imported.ref in explanation["imported_history_refs"]
    assert all("喜欢吃草莓" not in m["content"] for m in messages if m["role"] == "user")
    assert source.gateway.provider.requests == [] and target.gateway.provider.requests == []
