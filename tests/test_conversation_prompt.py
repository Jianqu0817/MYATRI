"""Prompt integration checks; fixtures do not claim improved semantic quality."""
import pytest

from myatri.app import Application
from myatri.conversation.reply import ReplyPolicy
from myatri.providers import FixtureProvider


OPTIONS = {"limit": 1000000, "llm_activation": False, "trace_every_turns": 30,
           "reply_min_chars": 20, "reply_target_max_chars": 100,
           "reply_max_chars": 160, "reply_max_tokens": 1024}


@pytest.mark.parametrize("body", [
    "嗯，回来就好。",
    "你刚才说的那件事，我还记得。" * 9,
    "这个地方我不确定，得先核对原话。",
])
def test_style_guidance_does_not_rewrite_short_or_complete_answers(body):
    assert len(body) <= 160
    policy = ReplyPolicy(OPTIONS)
    assert policy.prepare(body) == body
    assert "通常20—100字，必要时可到160字" in policy.instruction


def test_chat_style_keeps_selection_honesty_and_current_persona_boundaries():
    instruction = ReplyPolicy(OPTIONS).instruction
    assert "只说眼下最相关的一点" in instruction
    assert "不把所有背景、旧事和每个话头塞进同一句" in instruction
    assert "有自然关联才接旧梗" in instruction
    assert "语气沿用当前角色卡" in instruction
    assert "不为表现人设而每句调情" in instruction
    assert "不知道就承认，不为拟人故意答错" in instruction
    assert "被问身份时如实说明是AI" in instruction
    assert "不汇报读上下文、检索、保存记忆或组织回复的过程" in instruction
    assert "看见不等于要说，记得不等于要提" in instruction
    assert "若能，就不特意提旧事" in instruction
    assert "这只约束说什么，不删除已提供的历史" in instruction
    assert "只有本轮明确要求总结、比较、回忆或同时提出多个问题时" in instruction
    for upstream_only in ("send_message", "memory_append", "send_sticker", "小鲸鱼", "没有跨次运行的对话记忆"):
        assert upstream_only not in instruction


async def test_guidance_reaches_model_without_removing_history_or_changing_persona(tmp_path):
    provider = FixtureProvider([{"content": "还记得那个纸飞机，折歪了也舍不得扔。"}])
    app = Application(tmp_path, provider=provider, config={"context": OPTIONS,
        "cognition": {"maintenance_turns": 50}, "embedding": {"backend": "tfidf"},
        "initial_persona_entries": {"P00_current_identity": "小温暖，保留当前角色。"}})
    user = app.store.append_message("user", "那只纸飞机是我们昨天没聊完的玩笑。", "previous")
    old_answer = app.store.append_message("assistant", "折得有点歪，倒是飞得挺远。", "old_answer", reply_to=user.ref)
    persona = app.store.get_record("persona")
    answer = await app.conversation.respond("接着说纸飞机吧。", message_id="current")
    messages = provider.requests[0].messages
    assert any(user.body_markdown in row.get("content", "") for row in messages if row["role"] == "user")
    assert any(old_answer.body_markdown in row.get("content", "") for row in messages if row["role"] == "assistant")
    assert any("只说眼下最相关的一点" in row.get("content", "") for row in messages if row["role"] == "system")
    assert any("小温暖，保留当前角色。" in row.get("content", "") for row in messages if row["role"] == "system")
    assert app.store.get_record("persona").ref == persona.ref
    assert answer.body_markdown == "还记得那个纸飞机，折歪了也舍不得扔。"
    assert len(provider.requests) == 1
    assert app.store.get_record(user.record_id).body_markdown == user.body_markdown
