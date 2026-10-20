import json

import pytest

from myatri.app import Application
from myatri.providers import FixtureProvider, ProviderError
from myatri.conversation.engine import Conversation


async def test_tool_roundtrip_durable_protocol_never_becomes_memory(tmp_path):
    call = {"id": "lookup1", "type": "function", "function": {"name": "read_record", "arguments": '{"ref":"persona@1"}'}}
    provider = FixtureProvider([{"content": "", "tool_calls": [call], "finish_reason": "tool_calls",
                                 "provider_fields": {"reasoning_content": "protocol_fixture_field"}},
                                {"content": "完成原文回查"}])
    app = Application(tmp_path, provider=provider)
    answer = await app.conversation.respond("读取当前人格", message_id="protocol_turn")
    trace = app.queue.get_protocol("protocol_turn")
    assert trace["status"] == "completed"
    messages = provider.requests[-1].messages
    assert any(m.get("reasoning_content") == "protocol_fixture_field" for m in messages)
    assert any(m.get("tool_call_id") == "lookup1" for m in messages)
    assert not any("protocol_fixture_field" in r.model_dump_json() for r in app.store.list_records())
    restarted = Application(tmp_path)
    assert restarted.queue.get_protocol("protocol_turn")["reply_ref"] == answer.ref
    assert (await restarted.conversation.respond("读取当前人格", message_id="protocol_turn")).ref == answer.ref


async def test_restart_resumes_at_complete_tool_boundary(tmp_path):
    call = {"id": "lookup1", "type": "function", "function": {"name": "read_record", "arguments": '{"ref":"persona@1"}'}}
    class Interrupted(FixtureProvider):
        async def generate(self, request):
            if self.requests:
                raise ProviderError("simulated interruption after durable tool result")
            return await super().generate(request)
    app = Application(tmp_path, provider=Interrupted([{"content": "", "tool_calls": [call], "finish_reason": "tool_calls"}]))
    with pytest.raises(ProviderError):
        await app.conversation.respond("查询", message_id="resume")
    assert app.queue.get_protocol("resume")["status"] == "active"
    provider = FixtureProvider([{"content": "已恢复并完成"}])
    restarted = Application(tmp_path, provider=provider)
    answer = await restarted.conversation.respond("查询", message_id="resume")
    assert answer.body_markdown == "已恢复并完成"
    assert any(m.get("role") == "tool" for m in provider.requests[0].messages)


async def test_answer_callback_observes_persisted_answer_and_replays_idempotently(tmp_path):
    provider = FixtureProvider([{"content": "首次持久化答案"}])
    app = Application(tmp_path, provider=provider)
    seen = []
    def callback(answer):
        assert app.store.get_record(answer.record_id).ref == answer.ref
        seen.append(answer.ref)
    conversation = Conversation(app.store, app.gateway, app.recall, on_answer=callback, protocol_store=app.queue)
    answer = await conversation.respond("同一轮", message_id="callback_turn")
    assert seen == [answer.ref]
    assert (await conversation.respond("同一轮", message_id="callback_turn")).ref == answer.ref
    assert seen == [answer.ref, answer.ref] and len(provider.requests) == 1
    reopened = Application(tmp_path)
    replayed = []
    resumed = Conversation(reopened.store, reopened.gateway, reopened.recall, on_answer=lambda record: replayed.append(record.ref))
    assert (await resumed.respond("同一轮", message_id="callback_turn")).ref == answer.ref
    assert replayed == [answer.ref]


async def test_callback_failure_preserves_answer_and_retry_does_not_regenerate(tmp_path):
    provider = FixtureProvider([{"content": "答案先落盘"}])
    app = Application(tmp_path, provider=provider)
    calls = []
    def callback(answer):
        calls.append(answer.ref)
        if len(calls) == 1:
            raise RuntimeError("模拟入队前中断")
    conversation = Conversation(app.store, app.gateway, app.recall, on_answer=callback)
    with pytest.raises(RuntimeError, match="模拟"):
        await conversation.respond("可重试", message_id="callback_retry")
    answer = await conversation.respond("可重试", message_id="callback_retry")
    assert calls == [answer.ref, answer.ref]
    assert len(provider.requests) == 1
