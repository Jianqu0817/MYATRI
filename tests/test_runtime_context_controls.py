"""Working-window reset preserves archive, long-term recall and new turns."""
import json

import pytest

from myatri.app import Application
from myatri.providers import FixtureProvider, ProviderError


def application(path, provider=None):
    return Application(path, provider=provider or FixtureProvider(), config={
        "context": {"limit": 1000000, "llm_compaction": False, "llm_activation": False},
        "cognition": {"maintenance_turns": 50}, "embedding": {"backend": "tfidf"}})


def test_reset_survives_restart_and_never_erases_raw_or_replays_old_summary(tmp_path):
    app = application(tmp_path)
    old = app.store.append_message("user", "旧会话保留在长期档案。", "old")
    old_answer = app.store.append_message("assistant", "这是旧回复。", "old_answer", reply_to=old.ref)
    old_summary = app.conversation.context.compactor.compact()
    before_records = {r.ref: r.body_markdown for r in app.store.list_records()}
    boundary = app.clear_context()
    assert boundary["snapshot"] and boundary["cleared_at"]
    assert app.conversation.context.compactor.current() is None
    restored = application(tmp_path)
    context = restored.conversation.context
    current = restored.store.append_message("user", "现在开始新的话题。", "new")
    messages, _ = context.build_context("现在开始新的话题")
    assert context.context_boundary() == boundary
    assert context.explain_context()["history_refs"] == [current.ref]
    assert context.explain_context()["summary_ref"] is None
    assert old_summary.ref not in context.explain_context()["recall_refs"]
    assert all(old.body_markdown not in row["content"] for row in messages if row["role"] == "user")
    for ref, body in before_records.items():
        assert restored.recall.read_record(ref).body_markdown == body
    assert restored.recall.read_record(old_answer.ref).body_markdown == old_answer.body_markdown
    assert restored.store.verify_archive() == []


def test_compaction_after_reset_only_covers_new_window(tmp_path):
    app = application(tmp_path)
    app.store.append_message("user", "旧窗口不能被新会话摘要带回来。", "old")
    app.conversation.context.compactor.compact()
    app.clear_context()
    new = app.store.append_message("user", "新窗口的约定。", "new")
    summary = app.conversation.context.compactor.compact()
    assert summary.payload["source_range"] == [new.ref]
    assert app.conversation.context.summary_allowed(summary)
    assert "旧窗口" not in summary.body_markdown


async def test_clear_retires_interrupted_protocol_and_next_turn_is_usable(tmp_path):
    provider = FixtureProvider([{"content": "新窗口可以正常回应。"}])
    app = application(tmp_path, provider)
    old = app.store.append_message("user", "失败后遗留的旧轮次", "interrupted")
    frozen = [{"role": "user", "content": old.body_markdown}]
    app.queue.save_protocol(old.record_id, {"status": "active", "messages": frozen, "steps": 1})
    app.queue.set_meta("context_token_anchor", {"prompt_tokens": 1000, "parts": []})
    async with app.conversation._lock:
        app.clear_context()
    protocol = app.queue.get_protocol(old.record_id)
    assert protocol["status"] == "context_reset" and protocol["messages"] == frozen
    assert app.queue.get_meta("context_token_anchor") is None
    assert app.conversation.context.budget.anchor is None
    with pytest.raises(ProviderError, match="cleared context"):
        await app.conversation.respond(old.body_markdown, message_id="interrupted")
    assert provider.requests == []
    result = await app.conversation.respond("新的输入", message_id="fresh")
    assert result.body_markdown == "新窗口可以正常回应。"
    assert len(provider.requests) == 1
    assert all(old.body_markdown not in row["content"] for row in provider.requests[0].messages if row["role"] == "user")
    assert json.dumps(app.queue.get_meta("context_window_boundary"))
