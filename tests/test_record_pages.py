import json

import pytest

from myatri.app import Application
from myatri.conversation.engine import read_record_page
from myatri.providers import FixtureProvider
from myatri.storage import ArchiveStore


def test_small_record_remains_compatible_and_explicit_offset_pages(tmp_path):
    store = ArchiveStore(tmp_path)
    record = store.append_message("user", "小记录原文")
    assert read_record_page(store, record.ref) == record.model_dump(mode="json")
    page = read_record_page(store, record.ref, offset=2, limit=2)
    assert page["body_markdown"] == "录原"
    assert page["next_offset"] == 4


def test_large_record_automatic_first_page_and_following_pages_preserve_all_text(tmp_path):
    store = ArchiveStore(tmp_path)
    text = '含有中文与"引号"\n' * 500
    record = store.append_message("user", text, channel_source={"sender_id": "member_a", "sender_name": "甲"})
    first = read_record_page(store, record.ref)
    assert first["offset"] == 0 and first["total_chars"] == len(text)
    assert first["ref"] == record.ref and len(first["body_markdown"]) <= 800
    assert first["payload"]["channel_source"]["sender_id"] == "member_a"
    chunks, page = [], first
    while True:
        assert len(json.dumps(page, ensure_ascii=False).encode()) <= 6000
        chunks.append(page["body_markdown"])
        if page["next_offset"] is None:
            break
        page = read_record_page(store, record.ref, offset=page["next_offset"])
    assert "".join(chunks) == text


@pytest.mark.parametrize("args", [{"offset": -1}, {"offset": True}, {"limit": 0}, {"limit": 801}])
def test_invalid_page_arguments_rejected(tmp_path, args):
    store = ArchiveStore(tmp_path)
    record = store.append_message("user", "小记录")
    with pytest.raises(ValueError):
        read_record_page(store, record.ref, **args)


async def test_tool_read_record_returns_large_first_page_instead_of_error(tmp_path):
    provider = FixtureProvider([{"content": "", "tool_calls": [{"id": "page1", "type": "function",
        "function": {"name": "read_record", "arguments": '{"ref":"long_raw@1"}'}}]},
        {"content": "原文已读到。"}])
    app = Application(tmp_path, provider=provider, config={"context": {"limit": 100000}})
    app.store.append_message("user", "长原文。" * 1000, message_id="long_raw")
    await app.conversation.respond("请回查长原文", message_id="lookup")
    tool = next(message for message in provider.requests[-1].messages if message.get("tool_call_id") == "page1")
    page = json.loads(tool["content"])
    assert page["next_offset"] == 800 and page["total_chars"] == 4000
    assert "error" not in page
