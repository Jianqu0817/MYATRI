"""Richer context retains sources and whole turns, without extra model calls."""
import json
from datetime import datetime, timedelta, timezone

import jsonschema
import pytest

from myatri.app import Application
from myatri.contracts import Record
from myatri.conversation.compaction import COMPACTION_SCHEMA, Compactor
from myatri.conversation.context import ContextBuilder
from myatri.conversation.reply import ReplyPolicy
from myatri.conversation.window import context_stats, excerpt
from myatri.persona.state import PersonaState
from myatri.providers import FixtureProvider, Gateway
from myatri.retrieval import RecallService
from myatri.storage import ArchiveStore


def raw_record(store, name, text, role="user", **payload):
    return Record(record_id=name, record_kind="raw_message", agent_id=store.agent_id,
                  user_id=store.user_id, body_markdown=text, payload={"role": role, **payload})


def test_eighty_complete_turns_survive_compaction_and_restart(tmp_path):
    store = ArchiveStore(tmp_path)
    PersonaState(store).initialize()
    records = []
    origin = datetime(2026, 10, 20, tzinfo=timezone.utc)
    for i in range(90):
        user = raw_record(store, f"user_{i}", f"保留相处细节{i}。")
        answer = raw_record(store, f"answer_{i}", f"接住之前的话{i}。", "assistant", reply_to=user.ref)
        user = user.model_copy(update={"created_at": (origin + timedelta(seconds=2*i)).isoformat()})
        answer = answer.model_copy(update={"created_at": (origin + timedelta(seconds=2*i+1)).isoformat()})
        records.extend((user, answer))
    store.commit(records, "ninety-whole-turns")
    Compactor(store).compact()
    store = ArchiveStore(tmp_path)
    builder = ContextBuilder(store, RecallService(store), options={"limit": 1000000,
        "compact_at": 650000, "recent_history_turns": 80, "recent_history_bytes": 240000,
        "llm_activation": False})
    messages, _ = builder.build_context("继续我们刚才的日常话题")
    history = builder.explain_context()["history_refs"]
    assert history == [r.ref for r in records[20:]]
    assert len([m for m in messages if m["role"] == "user"]) == 80
    assert len([m for m in messages if m["role"] == "assistant"]) == 80
    assert len(store.list_records("raw_message")) == 180
    assert store.verify_archive() == []


def test_recent_window_never_keeps_half_an_exchange_and_preserves_pending_input(tmp_path):
    store = ArchiveStore(tmp_path)
    PersonaState(store).initialize()
    user = raw_record(store, "older_user", "约好以后再聊。")
    answer = raw_record(store, "older_answer", "那就等你回来。", "assistant", reply_to=user.ref)
    large_user = raw_record(store, "large_user", "很长的话" * 1000)
    large_answer = raw_record(store, "large_answer", "完整回应。", "assistant", reply_to=large_user.ref)
    pending = raw_record(store, "pending", "我刚回来了。")
    records = [user, answer, large_user, large_answer, pending]
    builder = ContextBuilder(store, RecallService(store), options={"recent_history_turns": 80,
        "recent_history_bytes": 1000})
    result = builder._recent_history(records)
    assert pending in result
    refs = {r.ref for r in result}
    for u, a in ((user, answer), (large_user, large_answer)):
        assert (u.ref in refs) == (a.ref in refs)


def test_excerpt_recovers_late_query_and_exposes_literal_coverage():
    text = "我记得前面都是无关的闲聊。" * 200 + "周六晚上的书店约定" + "后面的日常。" * 100
    row = excerpt(text, "我记得我们有个书店约定", 200)
    assert "书店约定" in row["text"]
    assert row["excerpt_start"] > 500
    assert row["text"] == text[row["excerpt_start"]:row["excerpt_end"]]
    assert len(row["text"]) <= 200
    assert row["omitted_chars"] == len(text) - len(row["text"])
    assert row["full_record_in_context"] is False
    short = excerpt("完整的原话。", "原话", 4000)
    assert short["full_record_in_context"] is True


def test_recall_ranking_is_local_but_literal_coverage_stays_in_model_context(tmp_path):
    store = ArchiveStore(tmp_path)
    PersonaState(store).initialize()
    raw = store.append_message("user", "书店约定：周六下午见。原话  空格不变。", "bookshop")
    builder = ContextBuilder(store, RecallService(store), options={"limit": 1000000,
        "llm_activation": False, "recall_budget_chars": 10000})
    messages, _ = builder.build_context("书店约定")
    memory = json.loads(messages[2]["content"].split("\n", 1)[1].split("\n检索局限：")[0])
    row = next(row for row in memory if row["ref"] == raw.ref)
    assert row["text"] == raw.body_markdown
    assert row["full_record_in_context"] is True
    assert row["excerpt_end"] == len(raw.body_markdown)
    assert "reason" not in row
    assert raw.ref in builder.explain_context()["recall_reasons"]
    assert store.get_record(raw.record_id).body_markdown == raw.body_markdown


@pytest.mark.parametrize("caveat", ["counterevidence:contradicts", "historical revision; not current state",
                                  "original source for interpretation@1"])
def test_lean_recall_does_not_strip_evidence_roles(tmp_path, monkeypatch, caveat):
    store = ArchiveStore(tmp_path)
    PersonaState(store).initialize()
    raw = store.append_message("user", "原来的说法后来有更正。", "changed")
    recall = RecallService(store)
    bundle = recall.recall("更正")
    bundle = bundle.model_copy(update={"reasons": {raw.ref: ["vector:body", "fts", caveat]}})
    monkeypatch.setattr(recall, "recall", lambda *a, **kw: bundle)
    builder = ContextBuilder(store, recall, options={"limit": 1000000, "llm_activation": False})
    messages, _ = builder.build_context("更正")
    memory = json.loads(messages[2]["content"].split("\n", 1)[1].split("\n检索局限：")[0])
    row = next(row for row in memory if row["ref"] == raw.ref)
    assert row["evidence_notes"] == [caveat]
    assert builder.explain_context()["recall_reasons"][raw.ref] == ["vector:body", "fts", caveat]


def test_reply_target_is_soft_and_no_filler_is_added():
    policy = ReplyPolicy({"reply_min_chars": 20, "reply_target_max_chars": 100,
                          "reply_max_chars": 160, "reply_max_tokens": 1024})
    assert policy.prepare("嗯，回来就好。") == "嗯，回来就好。"
    body = "你刚才说的那件事，我还记得。" * 9
    assert 100 < len(body) < 160
    assert policy.prepare(body) == body
    assert len(policy.prepare(body * 3)) <= 160
    assert "前面的往返" in policy.instruction
    assert "只接住眼前这一句话" not in policy.instruction


def test_context_statistics_contain_counts_but_no_chat_text_or_identifiers():
    messages = [{"role": "system", "content": "回忆材料：PRIVATE KEY sk-not-a-real-key"},
                {"role": "user", "content": "SECRET CHAT wxid_private"}]
    stats = context_stats(messages, dialogue_turns=2)
    serialized = json.dumps(stats)
    assert not any(s in serialized for s in ("PRIVATE", "SECRET", "wxid_private", "sk-not-a-real-key"))
    assert stats["components"]["dialogue"]["chars"] == len(messages[1]["content"])
    assert stats["measurement"] == "local_utf8_upper_estimate_not_api_tokens"


async def test_statistics_are_saved_every_turn_without_full_trace_or_extra_calls(tmp_path):
    provider = FixtureProvider([{"content": "嗯，我还记着呢。"}])
    app = Application(tmp_path, config={"context": {"limit": 1000000, "trace_every_turns": 30,
        "llm_activation": False}, "embedding": {"backend": "tfidf"}}, provider=provider)
    answer = await app.conversation.respond("SECRET CHAT:继续刚才的话。", message_id="current")
    protocol = app.queue.get_protocol("current")
    assert protocol["status"] == "completed"
    assert protocol["full_checkpoint"] is False
    assert "messages" not in protocol
    assert protocol["context_stats"]["version"] == 1
    assert "SECRET CHAT" not in json.dumps(protocol["context_stats"])
    assert answer.body_markdown == "嗯，我还记着呢。"
    assert len(provider.requests) == 1


@pytest.mark.parametrize("saved_stats", [None, {"version": 1, "dialogue_turns": 7, "components": {}}])
async def test_resumed_protocol_keeps_its_own_statistics_instead_of_previous_turn(tmp_path, saved_stats):
    provider = FixtureProvider([{"content": "嗯，接着说。"}])
    app = Application(tmp_path, config={"context": {"limit": 1000000, "trace_every_turns": 30,
        "llm_activation": False}, "embedding": {"backend": "tfidf"}}, provider=provider)
    raw = app.store.append_message("user", "继续旧请求。", message_id="resume")
    messages = [{"role": "system", "content": "固定角色规则。"},
                {"role": "user", "content": "继续旧请求。"}]
    protocol = {"status": "active", "messages": messages, "snapshot": app.store.snapshot(), "steps": 0}
    if saved_stats is not None:
        protocol["context_stats"] = saved_stats
    app.queue.save_protocol(raw.record_id, protocol)
    app.conversation.context.last_explanation = {"context_stats": {"version": 1, "dialogue_turns": 9999}}
    await app.conversation.respond("继续旧请求。", message_id="resume")
    stats = app.queue.get_protocol("resume")["context_stats"]
    assert stats != app.conversation.context.last_explanation["context_stats"]
    if saved_stats is not None:
        assert stats == saved_stats
    else:
        assert stats["components"]["dialogue"]["messages"] == 1
        assert "继续旧请求" not in json.dumps(stats, ensure_ascii=False)
    assert len(provider.requests) == 1


async def test_richer_semantic_schema_accepts_more_detail_and_keeps_source_spans(tmp_path):
    store = ArchiveStore(tmp_path)
    PersonaState(store).initialize()
    raw = store.append_message("user", "我答应周六先确认时间。今天说起书店时，我们还接着昨天的玩笑。", "source")
    items = [{"category": "agreement", "text": f"第{i}个可核对细节：" + "具体相处语境。" * 40,
              "evidence": [{"ref": raw.ref, "quote": "我答应周六先确认时间"}]} for i in range(8)]
    result = {"decision": "summarize", "reason": "保存上下文", "items": items}
    provider = FixtureProvider([{"content": json.dumps(result, ensure_ascii=False)}])
    compactor = Compactor(store, Gateway(provider), detail_items=24, detail_chars=600, output_tokens=8000)
    jsonschema.validate(result, compactor.schema)
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(result, COMPACTION_SCHEMA)
    summary = await compactor.acompact()
    assert summary.payload["strategy"] == "llm-semantic-v1"
    assert summary.generator["prompt_version"] == "compaction/v2"
    assert len(summary.payload["semantic_items"]) == 8
    for item in summary.payload["semantic_items"]:
        span = item["source_spans"][0]
        assert raw.body_markdown[span["start"]:span["end"]] == span["quote"]
    assert provider.requests[0].max_tokens == 8000
    assert "共同玩笑" in provider.requests[0].messages[0]["content"]
    assert len(provider.requests) == 1
