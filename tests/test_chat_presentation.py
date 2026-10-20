import re

import pytest

from myatri.app import Application
from myatri.conversation.reply import ReplyPolicy
from myatri.interfaces.cli import parser, run
from myatri.providers import FixtureProvider, ProviderError


OPTIONS = {"limit": 1000000, "llm_activation": False, "reply_min_chars": 40,
           "reply_max_chars": 80, "reply_max_tokens": 512}


@pytest.mark.parametrize("body", [
    "今天想安静待着。" * 20,
    "很长的一整句没有标点也不要再调用模型去改写" * 10,
    "这是一句有逗号的长话，" * 12,
    "第一段自然的聊天。\n\n" * 20,
])
def test_overlong_output_is_bounded_without_filler(body):
    result = ReplyPolicy(OPTIONS).prepare(body)
    assert 40 <= sum(not c.isspace() for c in result) <= 80
    assert result.endswith(("。", "…"))
    assert result.rstrip("…") in body


def test_strip_only_leading_model_time_metadata_and_keep_actual_time_references():
    policy = ReplyPolicy(OPTIONS)
    body = "你刚才说的是明天，而不是今天。[消息发送时间：2026-10-21T01:41:03+08:00]是你引用的原文。"
    assert policy.prepare("[消息发送时间：2026-10-21T01:41:03+08:00]\n" + body) == body
    assert policy.prepare("嗯，等你回来。") == "嗯，等你回来。"


async def test_bounded_reply_is_same_in_archive_checkpoint_and_terminal_with_no_extra_calls(tmp_path, monkeypatch, capsys):
    raw_response = "[消息发送时间：2026-10-21T01:41:03+08:00]\n" + "今天就陪你慢慢说话，不用把每句话都讲得那么周全。" * 6
    provider = FixtureProvider([{"content": raw_response}])
    app = Application(tmp_path, config={"context": OPTIONS, "cognition": {"maintenance_turns": 50}}, provider=provider)
    monkeypatch.setattr("myatri.interfaces.cli.Application", lambda *args, **kwargs: app)
    inputs = iter(["少说一点就好。", "/quit"])

    def enter(prompt):
        value = next(inputs)
        print(prompt + value)
        return value

    monkeypatch.setattr("builtins.input", enter)
    await run(parser().parse_args(["--root", str(tmp_path), "chat", "--display-name", "小温暖"]))
    shown = capsys.readouterr().out
    answers = [r for r in app.store.list_records("raw_message") if r.payload["role"] == "assistant"]
    assert len(answers) == 1 and len(provider.requests) == 1
    answer = answers[0]
    assert 40 <= len(answer.body_markdown) <= 80
    assert "消息发送时间" not in shown and "消息发送时间" not in answer.body_markdown
    assert "[你]\n  > 少说一点就好。" in shown
    assert re.search(r"\[小温暖\]  \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\n  " + re.escape(answer.body_markdown), shown)
    assert "发送时间：" in shown
    user = app.store.get_record(answer.payload["reply_to"].split("@")[0])
    assert user.body_markdown == "少说一点就好。"
    assert app.queue.get_protocol(user.record_id)["messages"][-1]["content"] == answer.body_markdown
    assert provider.requests[0].max_tokens == 512
    assert any("40—80字" in m["content"] and "默认用陈述句" in m["content"] for m in provider.requests[0].messages)
    assert Application(tmp_path).store.get_record(answer.record_id).body_markdown == answer.body_markdown


async def test_tool_protocol_is_not_shortened_by_chat_body_limit(tmp_path):
    arguments = '{"query":"' + "一段用于查找历史来源的查询" * 10 + '"}'
    call = {"id": "recall1", "type": "function", "function": {"name": "recall", "arguments": arguments}}
    provider = FixtureProvider([{"content": "", "tool_calls": [call], "finish_reason": "tool_calls"},
                                {"content": "我先看看原来的记录。" * 10}])
    app = Application(tmp_path, config={"context": OPTIONS}, provider=provider)
    answer = await app.conversation.respond("回忆一下", message_id="lookup")
    tool_message = next(m for m in provider.requests[-1].messages if m.get("tool_calls"))
    assert tool_message["tool_calls"][0]["function"]["arguments"] == arguments
    assert len(provider.requests) == 2
    assert 40 <= len(answer.body_markdown) <= 80


async def test_metadata_only_reply_does_not_commit_an_empty_answer(tmp_path):
    app = Application(tmp_path, config={"context": OPTIONS}, provider=FixtureProvider([
        {"content": "[消息发送时间：2026-10-21T01:41:03+08:00]"}]))
    with pytest.raises(ProviderError, match="empty reply"):
        await app.conversation.respond("你好", message_id="empty")
    assert app.store.get_record("empty").body_markdown == "你好"
    with pytest.raises(KeyError):
        app.store.get_record("answer_empty")
