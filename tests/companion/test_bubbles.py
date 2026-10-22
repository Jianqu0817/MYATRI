"""One model call, ordered bubbles, durable partial delivery and no resend."""
from contextlib import closing
import json
from pathlib import Path
import sqlite3

import pytest

from myatri.conversation.reply import ReplyPolicy
from myatri.providers import FixtureProvider
from myatri.companion.bridge import Bridge, Conflict
from myatri.companion.bubbles import BUBBLE_RULES, SEPARATOR, prepare_bubbles


POLICY = ReplyPolicy({"reply_min_chars": 20, "reply_max_chars": 160, "reply_target_max_chars": 100})
FIRST = "回来啦，今天好像比平时晚一点。"
SECOND = "先把东西放下吧，我陪你歇会儿。"


@pytest.mark.parametrize("text, expected", [
    ("嗯，回来就好。", ["嗯，回来就好。"]),
    ("好" * 15, ["好" * 15]),
    (FIRST + SEPARATOR + SECOND, [FIRST, SECOND]),
    (SEPARATOR + FIRST + SEPARATOR + SEPARATOR + SECOND + SEPARATOR, [FIRST, SECOND]),
    (FIRST + SECOND, [FIRST, SECOND]),
    ("这句话没有自然断点所以应该保持完整才自然", ["这句话没有自然断点所以应该保持完整才自然"]),
    ("```python\nprint('请保留这段代码完整')\n```", ["```python\nprint('请保留这段代码完整')\n```"]),
    ("短" + SEPARATOR + "句", ["短", "句"]),
    ('先看结果\n再接着说', ['先看结果', '再接着说']),
    ('你说“先休息\n明天再聊”\n那就好好睡', ['你说“先休息\n明天再聊”', '那就好好睡']),
    ('你说“今天有点累。明天再聊吧。”那就早点休息。', ['你说“今天有点累。明天再聊吧。”', '那就早点休息。']),
    ('这个链接是 https://example.com/?q=hello 先保存起来吧。', ['这个链接是 https://example.com/?q=hello 先保存起来吧。']),
])
def test_marker_and_safe_fallback_preserve_complete_meaning(text, expected):
    body, parts = prepare_bubbles(text, POLICY)
    assert parts == expected and SEPARATOR not in body
    assert len(parts) <= 3
    assert "".join(body.split()) == "".join("".join(parts).split())


def test_three_part_cap_and_whole_reply_length_cap():
    body, parts = prepare_bubbles(SEPARATOR.join([FIRST, SECOND, FIRST, SECOND] * 4), POLICY)
    assert 1 <= len(parts) <= 3
    assert len("".join(body.split())) <= 160
    assert all(SEPARATOR not in part and part for part in parts)
    assert "".join(body.split()) == "".join("".join(parts).split())


def provider_for(bridge):
    provider = FixtureProvider([{"content": FIRST + SEPARATOR + SECOND}])
    bridge.provider_factory = lambda scope: provider
    return provider


async def test_one_generation_one_archive_turn_and_per_part_confirmation(bridge, message):
    provider = provider_for(bridge)
    result = await bridge.receive(message)
    assert result["reply_parts"] == [FIRST, SECOND] and result["sent_parts"] == 0
    assert len(provider.requests) == 1 and BUBBLE_RULES in provider.requests[0].messages[-2]["content"]
    app = bridge.apps[message.scope]
    answer = app.store.get_record("answer_" + message.key)
    assert answer.payload["reply_parts"] == [FIRST, SECOND] and SEPARATOR not in answer.body_markdown
    assert len(app.store.list_records("raw_message")) == 2
    await bridge.claim(message.key)
    with pytest.raises(Conflict):
        await bridge.acknowledge(message.key, "sent", 1)
    assert (await bridge.acknowledge(message.key, "sent", 0))["status"] == "sending"
    assert (await bridge.acknowledge(message.key, "sent", 0))["sent_parts"] == 1
    assert (await bridge.acknowledge(message.key, "sent", 1))["status"] == "sent"
    with closing(sqlite3.connect(bridge.short_memory.path)) as db:
        own = [json.loads(row[0]) for row in db.execute(
            "SELECT payload FROM listening_assistant_context WHERE scope=? ORDER BY rowid", (message.scope,))]
    assert [row["text"] for row in own] == [FIRST, SECOND]
    assert len({row["message_id"] for row in own}) == 2
    # The next request replays the full confirmed answer once, not its bubbles again.
    await bridge.receive(message.model_copy(update={"message_id": "next", "text": "接着说吧"}))
    envelope = json.loads(provider.requests[-1].messages[-1]["content"].split("\n", 1)[1])
    assert not any(row.get("role") == "assistant" for row in envelope["recent_messages"])


async def test_restart_retains_partial_progress_and_does_not_resend(bridge, message):
    provider_for(bridge)
    await bridge.receive(message)
    await bridge.claim(message.key)
    await bridge.acknowledge(message.key, "sent", 0)
    await bridge.close()
    restored = Bridge(bridge.root, bridge.config, bridge.engine_config,
        Path(__file__).resolve().parents[2] / "config/personas/xiaowennuan/persona.md", provider_factory=bridge.provider_factory)
    try:
        state = await restored.receive(message)
        assert state["status"] == "unknown" and state["sent_parts"] == 1
        assert state["reply_parts"] == [FIRST, SECOND]
        assert (await restored.claim(message.key))["claimed"] is False
        assert not restored.apps
    finally:
        await restored.close()
