import pytest

from myatri.cognition.experience import ExperienceOrganizer
from myatri.providers import Gateway, FixtureProvider
from myatri.storage import ArchiveStore
from myatri.runtime.commit import Committer
from myatri.contracts import Record


async def test_ten_mentions_one_root_new_followup_not_merged(tmp_path):
    store = ArchiveStore(tmp_path)
    organizer = ExperienceOrganizer(store, Gateway(FixtureProvider()))
    for index in range(10):
        message = store.append_message("user", "那次电影取消了，还是有点失落。", message_id=f"msg{index}")
        Committer(store).submit_proposal(await organizer.propose(message))
    assert len(store.list_records("event")) == 1
    assert len(store.list_records("interpretation")) == 9
    message = store.append_message("user", "后来我们重新约定周六看电影。")
    Committer(store).submit_proposal(await organizer.propose(message))
    assert len(store.list_records("event")) == 2


async def test_fiction_and_quote_are_not_external_evidence(tmp_path):
    store = ArchiveStore(tmp_path)
    organizer = ExperienceOrganizer(store, Gateway(FixtureProvider()))
    message = store.append_message("user", "故事里电影取消了。")
    fixture = {"events": [{"summary": "故事电影取消", "quote": "电影取消了", "event_key": "fiction", "occurred_at": None, "reality_scope": "fictional"}]}
    Committer(store).submit_proposal(await organizer.propose(message, fixture=fixture))
    from myatri.persona.temporary import event_roots
    assert event_roots(store, [store.list_records("event")[0].ref]) == []
    bad = {"events": [{"summary": "x", "quote": "原文不存在", "event_key": "bad", "occurred_at": None, "reality_scope": "reported"}]}
    with pytest.raises(ValueError, match="verbatim"):
        await organizer.propose(message, fixture=bad)
    assistant = store.append_message("assistant", "我想主动找你")
    with pytest.raises(ValueError): await organizer.propose(assistant)


def test_contract_missing_source_version_and_generator_rejected():
    with pytest.raises(ValueError): Record(record_id="x", record_kind="reflection")
    with pytest.raises(ValueError): Record(record_id="x", record_kind="persona_version", revision=2)
    with pytest.raises(ValueError): Record(record_id="x", record_kind="raw_message", author_kind="model")


async def test_a1_subjective_interpretation_reaches_feeling_view_without_rewriting_event(tmp_path):
    store = ArchiveStore(tmp_path)
    organizer = ExperienceOrganizer(store, Gateway(FixtureProvider()))
    message = store.append_message("user", "电影取消后，我觉得失落，也想说清自己的期待。")
    data = {"events": [{"summary": "电影取消", "quote": "电影取消", "event_key": "movie1", "occurred_at": None,
        "reality_scope": "reported", "interpretation": "我可能希望期待被看见，但不代表对方不重视我。",
        "feeling": "失落，想说清期待", "uncertainty": ["不知道是否适用于下次安排"]}]}
    Committer(store).submit_proposal(await organizer.propose(message, fixture=data))
    event = store.list_records("event")[0]
    initial_hash = event.content_hash
    from myatri.memory import MemoryIndex
    index = MemoryIndex(store)
    await index.rebuild()
    assert index.query("失落期待", view="feeling")
    assert index.indexes["feeling"].rows[0]["event_ref"] == event.ref
    assert store.get_record(event.record_id).content_hash == initial_hash
