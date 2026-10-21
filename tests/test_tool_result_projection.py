import json

import pytest

from myatri.app import Application
from myatri.contracts import RecallBundle, Record
from myatri.conversation.engine import read_record_page
from myatri.conversation.tool_results import encoded_size, recall_page
from myatri.memory.imports import import_history
from myatri.providers import FixtureProvider, ProviderError
from myatri.retrieval import RecallService
from myatri.storage import ArchiveStore


def call(name, args, identifier="lookup"):
    return {"id": identifier, "type": "function", "function": {
        "name": name, "arguments": json.dumps(args, ensure_ascii=False)}}


def tool_results(provider):
    return [json.loads(message["content"]) for message in provider.requests[-1].messages
            if message.get("role") == "tool"]


def test_chinese_directory_pages_fit_actual_utf8_and_do_not_mutate_bundle():
    rows = [Record(record_id=f"row_{n}", record_kind="raw_message", body_markdown="中文原话，\"引号\"。" * 100,
                   payload={"role": "user", "large_private_payload": "重复元数据" * 500}) for n in range(12)]
    bundle = RecallBundle(records=rows, limitations=["索引维护信息" * 200] * 100)
    original = bundle.model_dump_json()
    found, offset = [], 0
    while True:
        page = recall_page(bundle, offset=offset, limit=8)
        assert encoded_size(page) <= 6000 and "error" not in page
        assert page["limitation_count"] == 100 and not page["limitations_complete"]
        assert "large_private_payload" not in json.dumps(page)
        found.extend(row["ref"] for row in page["records"])
        if page["next_offset"] is None:
            break
        assert page["next_offset"] > offset
        offset = page["next_offset"]
    assert found == [row.ref for row in rows]
    assert bundle.model_dump_json() == original


def test_nested_import_provenance_is_flat_and_original_payload_remains_pageable(tmp_path):
    source, middle, target = [ArchiveStore(tmp_path / name) for name in ("source", "middle", "target")]
    original = source.append_message("user", "最初的中文原话。" * 1000)
    one = import_history(source, middle, owner_label="本人")
    two = import_history(middle, target, owner_label="本人")
    ref = two["original_to_import"][one["original_to_import"][original.ref]]
    row = target.get_record(ref.rsplit("@", 1)[0])
    page = recall_page(RecallBundle(records=[row]))
    entry = page["records"][0]
    assert encoded_size(page) <= 6000
    assert len(entry["import_provenance"]) == 2
    assert entry["import_provenance"][-1]["original_ref"] == original.ref
    assert entry["import_provenance"][-1]["role"] == "user"
    raw = read_record_page(target, ref, field="payload_json")
    assert raw["content_field"] == "payload_json" and raw["next_offset"] is not None


def test_long_earliest_source_omission_keeps_a_readable_locator(tmp_path):
    store = ArchiveStore(tmp_path)
    original = store.append_message("user", "最初保留的消息。" * 2000)
    bundle = RecallService(store).recall("最早的聊天记忆", budget=1800)
    assert bundle.records == []
    page = recall_page(bundle)
    assert page["records"][0]["ref"] == original.ref
    assert page["records"][0]["content_loaded"] is False
    assert read_record_page(store, original.ref)["body_markdown"] == original.body_markdown[:800]


def test_projection_does_not_expand_hidden_person_or_retrieve_outside_selected_snapshot():
    allowed = Record(record_id="alice", record_kind="raw_message", body_markdown="甲的偏好")
    bundle = RecallBundle(snapshot="snapshot-original", records=[allowed],
        reasons={"bob@1": ["ineligible graph candidate"]}, paths=[["alice@1", "bob@1"]])
    page = recall_page(bundle)
    assert page["snapshot"] == "snapshot-original"
    assert "bob@1" not in json.dumps(page)
    assert [row["ref"] for row in page["records"]] == [allowed.ref]


async def test_actual_recall_then_read_roundtrip_and_compact_audit(tmp_path):
    provider = FixtureProvider([
        {"tool_calls": [call("recall", {"query": "最早的聊天记忆"})]},
        {"tool_calls": [call("read_record", {"ref": "early@1", "offset": 0, "limit": 60}, "read")]},
        {"content": "已经读到最初保留的原话。"}])
    app = Application(tmp_path, provider=provider,
        config={"context": {"limit": 100000, "trace_every_turns": 30}})
    app.store.append_message("user", "第一次见面时，下着雨。" * 1000, message_id="early")
    await app.conversation.respond("请寻找初期记录", message_id="turn")
    results = tool_results(provider)
    assert "early@1" in {row["ref"] for row in results[0]["records"]}
    assert results[1]["body_markdown"].startswith("第一次见面时，下着雨。")
    assert all(encoded_size(result) <= 6000 for result in results)
    protocol = app.queue.get_protocol("turn")
    assert "messages" not in protocol
    audit = protocol["tool_audit"]
    assert [entry["name"] for entry in audit] == ["recall", "read_record"]
    assert all(entry["success"] and entry["pending_pagination"] for entry in audit)
    assert audit[1]["source_refs"] == ["early@1"]
    assert audit[1]["result_bytes"] == encoded_size(results[1])


async def test_large_limitations_no_longer_replace_recall_with_budget_error(tmp_path):
    provider = FixtureProvider([{ "tool_calls": [call("recall", {"query": "test"})]}, {"content": "找到来源。"}])
    app = Application(tmp_path, provider=provider)
    row = app.store.append_message("user", "有效的小原话。")
    class Recall:
        def recall(self, query, snapshot, budget):
            assert snapshot and budget == 1800
            return RecallBundle(snapshot=snapshot, records=[row], limitations=["维护说明" * 300] * 50)
    app.conversation.recall = Recall()
    await app.conversation.respond("查找", message_id="turn")
    result = tool_results(provider)[0]
    assert result["records"][0]["ref"] == row.ref
    assert result["limitation_count"] == 50 and encoded_size(result) <= 6000
    assert app.queue.get_protocol("turn")["tool_audit"][0]["success"]


async def test_tool_failures_are_bounded_audited_and_not_claimed_as_reads(tmp_path):
    provider = FixtureProvider([{ "tool_calls": [
        call("read_record", {"ref": "missing@1"}, "missing"),
        call("read_record", {"ref": "persona@1", "limit": 0}, "invalid"),
        call("broken_host", {}, "host")]}, {"content": "这次读取没有成功。"}])
    app = Application(tmp_path, provider=provider)
    def broken():
        raise RuntimeError("host private internal detail")
    definition = {"type": "function", "function": {"name": "broken_host", "parameters": {"type": "object"}}}
    app.conversation.tool_handlers["broken_host"] = (definition, broken)
    await app.conversation.respond("查询", message_id="turn")
    assert all("error" in result for result in tool_results(provider))
    audit = app.queue.get_protocol("turn")["tool_audit"]
    assert not any(entry["success"] for entry in audit)
    assert all(not entry["source_refs"] for entry in audit)
    assert audit[-1]["error_type"] == "RuntimeError"
    assert "private internal" not in json.dumps(tool_results(provider))


async def test_step_limit_is_still_bounded_and_keeps_audit_for_resume(tmp_path):
    provider = FixtureProvider([{ "tool_calls": [call("read_record", {"ref": "persona@1"})]}])
    app = Application(tmp_path, provider=provider)
    app.conversation.max_steps = 1
    with pytest.raises(ProviderError, match="step limit"):
        await app.conversation.respond("查找", message_id="turn")
    saved = app.queue.get_protocol("turn")
    assert saved["status"] == "active" and saved["tool_audit"][0]["success"]
    assert not any(row.payload.get("reply_to") for row in app.store.list_records("raw_message"))


def test_source_ref_and_metadata_pages_remain_bounded_and_reconstructable(tmp_path):
    store = ArchiveStore(tmp_path, agent_id="代理" * 1000, user_id="用户" * 1000)
    refs = ["source_" + str(i) + "@1" for i in range(60)]
    sources = [Record(record_id=f"source_{i}", record_kind="raw_message", body_markdown="来源",
        agent_id=store.agent_id, user_id=store.user_id) for i in range(60)]
    row = Record(record_id="large", record_kind="raw_message", body_markdown="短文",
        source_refs=refs, agent_id="代理" * 1000, user_id="用户" * 1000,
        payload={"participants": ["人" * 1000] * 30, "event_refs": ["事" * 1000] * 30,
            "channel_source": {key: "成员" * 1000 for key in
                ("sender_id", "sender_name", "message_id", "speaker_id", "subject_id", "attribution", "source_message_id")},
            "attribution": {"subject_id": "人" * 1000}})
    store.commit([*sources, row], "large")
    assert encoded_size(read_record_page(store, row.ref)) <= 6000
    chunks, offset = [], 0
    while True:
        page = read_record_page(store, row.ref, offset=offset, field="source_refs_json", limit=80)
        assert encoded_size(page) <= 6000 and page["content_field"] == "source_refs_json"
        chunks.append(page["body_markdown"])
        if page["next_offset"] is None:
            break
        offset = page["next_offset"]
    assert json.loads("".join(chunks)) == refs


@pytest.mark.parametrize("args", [{"offset": True}, {"limit": 0}, {"offset": -1}, {"limit": 9}])
def test_invalid_recall_paging_rejected(args):
    with pytest.raises(ValueError):
        recall_page(RecallBundle(), **args)
