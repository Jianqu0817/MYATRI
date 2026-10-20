from datetime import datetime, timedelta, timezone

import pytest

from myatri.contracts import Record
from myatri.conversation.engine import read_record_page
from myatri.memory import MemoryIndex
from myatri.memory.imports import import_history
from myatri.retrieval import RecallService
from myatri.storage import ArchiveStore


def message(store, identifier, text, day):
    row = Record(record_id=identifier, record_kind="raw_message", body_markdown=text,
        created_at=(datetime(2026, 1, 1, tzinfo=timezone.utc) + timedelta(days=day)).isoformat(),
        payload={"role": "user"})
    store.commit([row], identifier)
    return row


async def test_earliest_query_prioritizes_originals_over_later_repeated_recollections(tmp_path):
    store = ArchiveStore(tmp_path)
    first = message(store, "first", "你好，今天下了雨。", 0)
    index = MemoryIndex(store)
    await index.update()
    message(store, "later", "最开始认识你的时候第一次聊天，我总是想起来。" * 15, 10)
    result = RecallService(store, index).recall("最早我们聊了什么", budget=1800)
    assert result.records[0].ref == first.ref
    assert any("不表示旧记忆丢失" in limit for limit in result.limitations)
    assert any("不证明现实中首次认识" in limit for limit in result.limitations)


def test_large_earliest_source_remains_locatable_and_readable(tmp_path):
    store = ArchiveStore(tmp_path)
    first = message(store, "first", "最早保留的很长的消息" * 1000, 0)
    result = RecallService(store).recall("你记得第一次聊天吗", budget=100)
    assert not result.records
    assert any(first.ref in limit and "早期原文定位" in limit for limit in result.limitations)
    assert read_record_page(store, first.ref)["body_markdown"] == first.body_markdown[:800]


def test_imported_history_and_candidate_isolation_are_preserved(tmp_path):
    source, target = ArchiveStore(tmp_path / "source"), ArchiveStore(tmp_path / "target")
    early = message(source, "old", "当时一起聊下雨。", 0)
    report = import_history(source, target, owner_label="测试用户")
    native = message(target, "native", "现在在群里聊天。", 20)
    recall = RecallService(target)
    old_ref = report["original_to_import"][early.ref]
    assert recall.recall("最开始我们聊了什么", budget=5000).records[0].ref == old_ref
    assert recall.recall("群里最早聊了什么", budget=5000).records[0].ref == native.ref
    filtered = recall.recall("最早我们聊了什么", filters={"candidate_refs": [native.ref]}, budget=5000)
    assert {r.ref for r in filtered.records} == {native.ref}


def test_twice_migrated_atri_history_keeps_its_original_beginning(tmp_path):
    atri, private, group = [ArchiveStore(tmp_path / name) for name in ("atri", "private", "group")]
    original = message(atri, "original", "初次打招呼的原话。", 0)
    first_import = import_history(atri, private, owner_label="测试用户")
    message(private, "private_recent", "后来换了名字。", 10)
    second_import = import_history(private, group, owner_label="测试用户")
    expected = second_import["original_to_import"][first_import["original_to_import"][original.ref]]
    result = RecallService(group).recall("最开始认识我时说了什么", budget=15000)
    assert result.records[0].ref == expected


@pytest.mark.parametrize("query", ["现在聊天吧", "我第一次喝咖啡", "最近下雨了吗"])
def test_ordinary_questions_do_not_force_the_beginning(tmp_path, query):
    store = ArchiveStore(tmp_path)
    message(store, "first", "你好，今天下了雨。", 0)
    result = RecallService(store).recall(query)
    assert not any("早期原文定位" in limit for limit in result.limitations)
