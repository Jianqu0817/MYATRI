import json

import pytest

from myatri.app import Application
from myatri.cognition.experience import ExperienceOrganizer
from myatri.contracts import ModelResponse
from myatri.providers import FixtureProvider, Gateway
from myatri.runtime.commit import Committer
from myatri.storage import ArchiveStore


def group_message(store, text="我喜欢红茶。", *, sender="member_a", mid="wx_one", legacy=False):
    source = {"sender_id": sender, "sender_name": "同名", "message_id": mid}
    envelope = {**source, "text": text,
                "recent_messages": [{"sender_id": "member_b", "sender_name": "同名",
                                      "message_id": "other", "text": "我喜欢咖啡。"}]}
    return store.append_message("user", json.dumps(envelope, ensure_ascii=False, sort_keys=True),
                                message_id=mid, **({} if legacy else {"channel_source": source}))


def extraction(quote="我喜欢红茶", **changes):
    return {"events": [{"summary": "甲自述喜欢红茶", "quote": quote,
             "reality_scope": "reported", "occurred_at": None, "event_key": "preference",
             "speaker_id": "member_a", "subject_id": "member_a", "attribution": "self_report", **changes}]}


@pytest.mark.parametrize("changes,reason", [
    ({"speaker_id": "member_b", "subject_id": "member_b"}, "speaker_id"),
    ({"subject_id": "member_b"}, "subject_id"),
    ({"participants": ["同名"]}, "real known"),
])
async def test_same_nickname_cannot_move_self_report_to_other_id(tmp_path, changes, reason):
    store = ArchiveStore(tmp_path, agent_id="xiaowennuan", user_id="group")
    organizer = ExperienceOrganizer(store, Gateway(FixtureProvider()))
    with pytest.raises(ValueError, match=reason):
        await organizer.propose(group_message(store), fixture=extraction(**changes))
    assert not store.list_records("event")


async def test_recent_message_quote_never_becomes_current_speaker_fact(tmp_path):
    store = ArchiveStore(tmp_path, agent_id="xiaowennuan", user_id="group")
    organizer = ExperienceOrganizer(store, Gateway(FixtureProvider()))
    with pytest.raises(ValueError, match="current transport text"):
        await organizer.propose(group_message(store), fixture=extraction("我喜欢咖啡"))


async def test_newlines_quotes_and_backslashes_keep_exact_original_offsets(tmp_path):
    store = ArchiveStore(tmp_path, agent_id="xiaowennuan", user_id="group")
    organizer = ExperienceOrganizer(store, Gateway(FixtureProvider()))
    quote = '我喜欢"红茶"\n也喜欢\\音乐'
    message = group_message(store, "前面。" + quote + "。后面。")
    Committer(store).submit_proposal(await organizer.propose(message, fixture=extraction(quote)))
    event = store.list_records("event")[0]
    span = event.payload["source_spans"][0]
    assert message.body_markdown[span["start"]:span["end"]] == span["quote"]
    assert span["quote"] == json.dumps(quote, ensure_ascii=False)[1:-1]
    assert event.payload["participants"] == ["member_a"]
    attribution = store.list_records("interpretation")[0].payload["attribution"]
    assert attribution["original_quote"] == quote
    coverage = next(r for r in store.list_records("cognitive_run") if r.payload["role"] == "A1").payload["source_coverage"]
    assert coverage["scope"] == "only_current_transport_text"
    assert coverage["recent_messages_extracted"] is False
    assert store.verify_archive() == []


async def test_legacy_transport_is_limited_without_new_metadata(tmp_path):
    store = ArchiveStore(tmp_path, agent_id="xiaowennuan", user_id="group")
    message = group_message(store, legacy=True)
    proposal = await ExperienceOrganizer(store, Gateway(FixtureProvider())).propose(message)
    event = next(r for r in proposal.records if r.record_kind == "event")
    assert event.body_markdown == "我喜欢红茶。"
    assert "咖啡" not in event.body_markdown
    assert event.payload["participants"] == ["member_a"]


async def test_third_party_report_remains_unconfirmed(tmp_path):
    store = ArchiveStore(tmp_path, agent_id="xiaowennuan", user_id="group")
    proposal = await ExperienceOrganizer(store, Gateway(FixtureProvider())).propose(
        group_message(store, "乙说他喜欢咖啡"), fixture=extraction("乙说他喜欢咖啡",
            subject_id="member_b", attribution="reported"))
    event = next(r for r in proposal.records if r.record_kind == "event")
    assert event.payload["participants"] == ["member_a", "member_b"]
    attribution = next(r for r in proposal.records if r.record_kind == "interpretation").payload["attribution"]
    assert attribution["confirmed"] is False and attribution["speaker_id"] == "member_a"


async def test_non_group_json_remains_original_source(tmp_path):
    store = ArchiveStore(tmp_path)
    message = store.append_message("user", '{"text": "我喜欢红茶", "other": "并非渠道信封"}')
    proposal = await ExperienceOrganizer(store, Gateway(FixtureProvider())).propose(message)
    event = next(r for r in proposal.records if r.record_kind == "event")
    assert event.body_markdown == message.body_markdown
    assert event.payload["source_spans"][0]["quote"] == message.body_markdown


class EmptyProvider:
    name = "scripted-offline"

    def __init__(self):
        self.requests = []

    async def generate(self, request):
        self.requests.append(request)
        return ModelResponse(content='{"events": []}', provider=self.name, model="test")


async def test_batch_excludes_organized_records_and_passes_only_current_group_text(tmp_path):
    store = ArchiveStore(tmp_path, agent_id="xiaowennuan", user_id="group")
    provider = EmptyProvider()
    organizer = ExperienceOrganizer(store, Gateway(provider))
    commit = Committer(store).submit_proposal
    first = group_message(store)
    commit(await organizer.propose(first, fixture=extraction()))
    second = group_message(store, "我喜欢绿茶", mid="wx_two")
    refs = await organizer.organize_batch([first, second], commit)
    assert refs == [second.ref]
    assert len(provider.requests) == 1
    rows = json.loads(provider.requests[0].messages[-1]["content"])["messages"]
    assert [row["text"] for row in rows] == ["我喜欢绿茶"]
    assert rows[0]["channel_source"]["sender_id"] == "member_a"
    assert "recent_messages" not in rows[0]


async def test_conversation_persists_channel_metadata_without_changing_body(tmp_path):
    app = Application(tmp_path, provider=FixtureProvider([{"content": "记住啦。"}]))
    source = {"sender_id": "member_a", "sender_name": "甲", "message_id": "transport1"}
    text = json.dumps({**source, "text": "我喜欢红茶"}, ensure_ascii=False, sort_keys=True)
    await app.conversation.respond(text, message_id="wx_metadata", metadata={"channel_source": source})
    raw = app.store.get_record("wx_metadata")
    assert raw.body_markdown == text and raw.payload["channel_source"] == source


async def test_existing_event_cannot_be_merged_across_member_ids(tmp_path):
    store = ArchiveStore(tmp_path, agent_id="xiaowennuan", user_id="group")
    organizer = ExperienceOrganizer(store, Gateway(FixtureProvider()))
    Committer(store).submit_proposal(await organizer.propose(group_message(store), fixture=extraction()))
    prior = store.list_records("event")[0]
    second = group_message(store, sender="member_b", mid="wx_other")
    with pytest.raises(ValueError, match="ownership"):
        await organizer.propose(second, fixture=extraction(speaker_id="member_b", subject_id="member_b",
                                                          existing_event_ref=prior.ref))
