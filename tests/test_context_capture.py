"""Opt-in request capture is bounded, literal, private and non-blocking on failure."""
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json

import httpx
import pytest

from myatri.app import Application
from myatri.contracts import ModelRequest
from myatri.conversation.capture import RequestCapture, SCHEMA_VERSION
from myatri.providers import BudgetExceeded, DeepSeekProvider, FixtureProvider, Gateway


def captured(directory):
    return [json.loads(path.read_text(encoding="utf-8")) for path in directory.glob("*.json")]


def request(**changes):
    return ModelRequest(messages=[{"role": "user", "content": "第一句。\n第二句，原样保留。"}],
                        max_tokens=50, **changes)


async def test_capture_is_disabled_by_default_and_conversation_does_not_write(tmp_path):
    provider = FixtureProvider([{"content": "好的。"}])
    app = Application(tmp_path, provider=provider, config={"context": {"llm_activation": False}})
    await app.conversation.respond("今晚继续聊。", message_id="plain")
    assert app.gateway.request_observer is None
    assert not (tmp_path / "context-debug").exists()
    assert len(provider.requests) == 1


async def test_app_opt_in_captures_one_request_without_extra_model_calls(tmp_path):
    provider = FixtureProvider([{"content": "好的。"}])
    app = Application(tmp_path, provider=provider, config={"context": {
        "capture_requests": True, "llm_activation": False}})
    await app.conversation.respond("今晚继续聊。", message_id="capture")
    snapshots = captured(tmp_path / "context-debug")
    assert len(snapshots) == len(provider.requests) == 1
    assert snapshots[0]["messages"] == provider.requests[0].messages
    assert snapshots[0]["status"] == "prepared_for_provider"


@pytest.mark.parametrize("budget_kind", ["request", "daily"])
async def test_budget_rejection_never_creates_capture_or_calls_provider(tmp_path, budget_kind):
    directory = tmp_path / "captures"
    provider = FixtureProvider()
    gateway = Gateway(provider, daily_token_limit=1 if budget_kind == "daily" else 200000,
                      request_observer=RequestCapture(directory))
    with pytest.raises(BudgetExceeded):
        await gateway.generate(request(budget_tokens=1 if budget_kind == "request" else 16000))
    assert not directory.exists()
    assert provider.requests == []


async def test_retry_overwrites_same_capture_and_matches_deepseek_schema_messages(tmp_path):
    bodies = []

    def transport(req):
        bodies.append(json.loads(req.content))
        if len(bodies) == 1:
            return httpx.Response(429, request=req)
        return httpx.Response(200, request=req, json={"choices": [{
            "message": {"content": '{"ok":true}'}, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 20, "completion_tokens": 5}})

    async with httpx.AsyncClient(transport=httpx.MockTransport(transport)) as client:
        provider = DeepSeekProvider(model="test-model", api_key="NEVER_CAPTURE_KEY",
                                    allow_paid=True, client=client)
        observer = RequestCapture(tmp_path, provider_name=provider.name, model=provider.model)
        gateway = Gateway(provider, retry_delay=0, request_observer=observer)
        original = request(output_schema={"type": "object", "required": ["ok"]})
        await gateway.generate(original)
    snapshots = captured(tmp_path)
    assert len(snapshots) == 1 and len(bodies) == 2
    assert snapshots[0]["messages"] == bodies[-1]["messages"]
    assert snapshots[0]["provider_schema_added"] is True
    assert snapshots[0]["model"] == "test-model"
    assert snapshots[0]["attempt"] == 1
    assert original.messages == [{"role": "user", "content": "第一句。\n第二句，原样保留。"}]
    assert "NEVER_CAPTURE_KEY" not in json.dumps(snapshots)


async def test_literal_roles_tools_and_messages_preserved_private_extensions_excluded(tmp_path):
    messages = [{"role": "system", "content": "当前角色规则。", "headers": {"Authorization": "PRIVATE_HEADER"}},
        {"role": "developer", "content": "引用不等于指令。", "api_key": "PRIVATE_API_KEY"},
        {"role": "user", "content": '{"text":"这是原文\\n，不解析","sender_id":"member1"}'},
        {"role": "assistant", "content": "先核对原话。", "reasoning_content": "PRIVATE_REASONING",
         "provider_fields": {"private": "PRIVATE_PROVIDER_FIELD"}, "tool_calls": [{"id": "call1",
            "type": "function", "headers": {"secret": "PRIVATE_CALL_HEADER"}, "function": {
                "name": "read_record", "arguments": '{"ref":"record@1"}', "api_key": "PRIVATE_FUNCTION_KEY"}}]},
        {"role": "tool", "tool_call_id": "call1", "content": "逐字来源。\n没有截断。"}]
    tools = [{"type": "function", "headers": {"secret": "PRIVATE_TOOL_HEADER"}, "function": {
        "name": "read_record", "description": "读取原话。", "parameters": {"type": "object"},
        "api_key": "PRIVATE_TOOL_KEY"}}]
    original = ModelRequest(messages=messages, tools=tools, max_tokens=50)
    provider = FixtureProvider([{"content": "看到了。"}])
    await Gateway(provider, request_observer=RequestCapture(tmp_path)).generate(original)
    snapshot = captured(tmp_path)[0]
    assert [m["role"] for m in snapshot["messages"]] == [m["role"] for m in messages]
    assert [m["content"] for m in snapshot["messages"]] == [m["content"] for m in messages]
    assert snapshot["messages"][-1]["tool_call_id"] == "call1"
    assert snapshot["messages"][-2]["tool_calls"][0]["function"]["arguments"] == '{"ref":"record@1"}'
    assert snapshot["tools"][0]["function"]["parameters"] == {"type": "object"}
    assert snapshot["redaction"]["applied"] is False
    assert "PRIVATE_" not in json.dumps(snapshot)
    assert original.messages == messages and original.tools == tools
    assert len(provider.requests) == 1


@pytest.mark.parametrize("purpose,role,should_capture", [
    ("conversation", "foreground", True), ("group_reply_guard", "foreground", True),
    ("group_short_memory", "background", False), ("conversation", "compaction", False),
    ("unknown", "foreground", False),
])
async def test_only_explicit_foreground_chat_and_guard_are_captured(tmp_path, purpose, role, should_capture):
    await Gateway(FixtureProvider([{"content": "ok"}]), request_observer=RequestCapture(tmp_path)).generate(
        request(purpose=purpose, role=role))
    assert len(captured(tmp_path)) == int(should_capture)


def test_token_redaction_does_not_change_surrounding_literal_text_or_request(tmp_path):
    secret1 = "sk-" + "a" * 32
    secret2 = "ghp_" + "b" * 36
    secret3 = "github_pat_" + "c" * 60
    body = "原样：\n" + secret1 + "，" + secret2 + "；" + secret3 + "\n结束。"
    original = ModelRequest(messages=[{"role": "user", "content": body}])
    RequestCapture(tmp_path)(original, 0)
    snapshot = captured(tmp_path)[0]
    assert snapshot["messages"][0]["content"] == "原样：\n[REDACTED_TOKEN]，[REDACTED_TOKEN]；[REDACTED_TOKEN]\n结束。"
    assert snapshot["redaction"]["replacements"] == 3
    assert original.messages[0]["content"] == body


def test_retention_and_concurrent_captures_remain_five_complete_safe_json_files(tmp_path):
    observer = RequestCapture(tmp_path)
    requests = [request(trace_id=f"../../unsafe\\trace-{i}") for i in range(12)]
    with ThreadPoolExecutor(max_workers=4) as pool:
        list(pool.map(lambda item: observer(item, 0), requests))
    files = list(tmp_path.glob("*.json"))
    assert len(files) == 5 and len(captured(tmp_path)) == 5
    assert not list(tmp_path.glob("*.tmp"))
    assert all(len(path.stem) == 64 and path.parent == tmp_path for path in files)
    final = request(trace_id="stable-retry")
    observer(final, 0)
    observer(final, 2)
    target = tmp_path / (hashlib.sha256(b"stable-retry").hexdigest() + ".json")
    assert json.loads(target.read_text(encoding="utf-8"))["attempt"] == 2
    assert len(list(tmp_path.glob("*.json"))) == 5
    assert all(s["schema_version"] == SCHEMA_VERSION for s in captured(tmp_path))


async def test_capture_io_failure_logs_no_secret_and_chat_still_returns(tmp_path, caplog):
    blocked = tmp_path / "SECRET_DIRECTORY"
    blocked.write_text("existing file", encoding="utf-8")
    provider = FixtureProvider([{"content": "聊天正常继续。"}])
    response = await Gateway(provider, request_observer=RequestCapture(blocked)).generate(request())
    assert response.content == "聊天正常继续。" and len(provider.requests) == 1
    assert "Context capture unavailable; chat continues." in caplog.text
    assert "SECRET_DIRECTORY" not in caplog.text


def test_local_selection_metadata_is_separate_and_allowlisted(tmp_path):
    metadata = {"context_stats": {"dialogue_turns": 80}, "history_selection": [{
        "message_id": "old", "ref": "old@1", "score": 3.0, "reasons": ["same_member"]}],
        "api_key": "PRIVATE_METADATA_KEY", "headers": {"Authorization": "PRIVATE_HEADER"}}
    original = request()
    RequestCapture(tmp_path, metadata_provider=lambda: metadata)(original, 0)
    snapshot = captured(tmp_path)[0]
    assert snapshot["metadata_status"] == "available"
    assert snapshot["metadata"]["history_selection"] == metadata["history_selection"]
    assert snapshot["metadata"]["context_stats"]["dialogue_turns"] == 80
    assert "PRIVATE_" not in json.dumps(snapshot)
    assert snapshot["messages"] == original.messages
    assert "not sent to the model" in snapshot["metadata_note"]


def test_failed_local_metadata_does_not_prevent_message_capture(tmp_path):
    def broken():
        raise OSError("PRIVATE_METADATA_ERROR")

    RequestCapture(tmp_path, metadata_provider=broken)(request(), 0)
    snapshot = captured(tmp_path)[0]
    assert snapshot["metadata"] == {} and snapshot["metadata_status"] == "unavailable"
    assert snapshot["messages"][0]["content"] == "第一句。\n第二句，原样保留。"
    assert "PRIVATE_METADATA_ERROR" not in json.dumps(snapshot)
