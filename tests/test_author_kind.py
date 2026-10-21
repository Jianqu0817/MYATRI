"""作者归属：默认规则不变，显式值受限且经 Conversation.respond 透传。"""

import pytest

from myatri.app import Application
from myatri.providers import FixtureProvider
from myatri.storage import ArchiveError, ArchiveStore, IdempotencyError


def test_append_message_defaults_are_unchanged(tmp_path):
    """不传 author_kind 时沿用旧规则：user→human，其余→system。"""
    store = ArchiveStore(tmp_path)
    user = store.append_message("user", "用户原话", "user_msg")
    assistant = store.append_message("assistant", "角色发言", "assistant_msg")
    assert user.author_kind == "human"
    assert assistant.author_kind == "system"
    assert user.payload == {"role": "user"}
    assert assistant.payload == {"role": "assistant"}


def test_append_message_uses_explicit_self_initiated(tmp_path):
    """显式 self_initiated 写入 Record 信封，但不污染 payload。"""
    store = ArchiveStore(tmp_path)
    record = store.append_message("user", "我先开个话题。", "self_topic", author_kind="self_initiated")
    assert record.author_kind == "self_initiated"
    assert record.payload == {"role": "user"}
    assert store.get_record("self_topic").author_kind == "self_initiated"


def test_append_message_rejects_unknown_author_kind(tmp_path):
    """契约层未定义的归属必须被拒绝，且不留下任何记录。"""
    store = ArchiveStore(tmp_path)
    with pytest.raises(ArchiveError, match="author_kind"):
        store.append_message("user", "非法归属", "bad", author_kind="robot")
    assert store.list_records() == []


def test_append_message_retry_is_idempotent_and_rejects_relabelling(tmp_path):
    """同 message_id 同内容重试幂等；只改作者归属视为语义冲突。"""
    store = ArchiveStore(tmp_path)
    first = store.append_message("user", "我先开个话题。", "self_topic", author_kind="self_initiated")
    again = store.append_message("user", "我先开个话题。", "self_topic", author_kind="self_initiated")
    assert again.created_at == first.created_at
    assert again.author_kind == "self_initiated"
    with pytest.raises(IdempotencyError):
        store.append_message("user", "我先开个话题。", "self_topic", author_kind="human")


async def test_respond_forwards_author_kind_and_keeps_answer_system(tmp_path):
    """Conversation.respond 透传输入归属；角色答复仍按默认规则记为 system。"""
    app = Application(tmp_path, provider=FixtureProvider([{"content": "那我们从这儿聊起。"}]),
                      config={"context": {"llm_activation": False}})
    answer = await app.conversation.respond("我先开个话题。", message_id="self_turn",
                                            author_kind="self_initiated")
    raw = app.store.get_record("self_turn")
    assert raw.author_kind == "self_initiated"
    assert raw.payload["role"] == "user"
    assert answer.author_kind == "system"


async def test_self_initiated_input_never_enters_human_memory_pipeline(tmp_path):
    from myatri.cognition.experience import ExperienceOrganizer
    app = Application(tmp_path, provider=FixtureProvider(), config={"cognition": {"maintenance_turns": 50}})
    raw = app.store.append_message("user", "这是角色自己想说的话", "synthetic", author_kind="self_initiated")
    assert app.enqueue_message(raw) is None
    assert app.maintenance.pending()[0] == []
    app.recover_pending()
    assert not app.queue.list_jobs()
    with pytest.raises(ValueError, match="external evidence"):
        await ExperienceOrganizer(app.store, app.gateway).propose(raw)
