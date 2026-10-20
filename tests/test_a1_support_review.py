"""Synthetic A1 extraction/review checks; never invokes a remote model."""
import json

import pytest

from myatri.cognition.experience import ExperienceOrganizer
from myatri.contracts import ModelResponse
from myatri.providers import FixtureProvider, Gateway
from myatri.runtime.commit import Committer
from myatri.storage import ArchiveStore


class SyntheticReviewProvider(FixtureProvider):
    name = "synthetic"

    def __init__(self, *, verdict="supported", index=0, fail_reviews=0, subject="person-a"):
        super().__init__()
        self.verdict, self.index = verdict, index
        self.fail_reviews, self.subject = fail_reviews, subject

    async def generate(self, request):
        self.requests.append(request.model_copy(deep=True))
        if request.purpose == "A1_support":
            if self.fail_reviews:
                self.fail_reviews -= 1
                raise RuntimeError("synthetic support review failed")
            value = {"checks": [{"index": self.index, "verdict": self.verdict, "reason": "离线预设判定"}]}
        else:
            assert request.purpose in {"A1", "A1_batch"}
            item = {"summary": "本人自述喜欢红茶", "quote": "我喜欢红茶",
                    "reality_scope": "reported", "occurred_at": None,
                    "event_key": "tea-preference", "speaker_id": "person-a",
                    "subject_id": self.subject, "attribution": "self_report"}
            if request.purpose == "A1_batch":
                payload = json.loads(request.messages[-1]["content"])
                item["message_ref"] = payload["messages"][0]["ref"]
            value = {"events": [item]}
        return ModelResponse(content=json.dumps(value, ensure_ascii=False),
                             provider=self.name, model="synthetic-offline")


def setup_review(tmp_path, provider, *, enabled=True):
    store = ArchiveStore(tmp_path, agent_id="xiaowennuan", user_id="group")
    source = {"sender_id": "person-a", "sender_name": "甲", "message_id": "native-1",
              "support_review": enabled, "known_member_ids": ["person-a", "person-b"]}
    envelope = {**source, "text": "我喜欢红茶。", "recent_messages": []}
    message = store.append_message("user", json.dumps(envelope, ensure_ascii=False),
                                   message_id="wx_test", channel_source=source)
    return store, message, ExperienceOrganizer(store, Gateway(provider, retries=0))


async def organize(organizer, store, message, batch):
    commit = Committer(store).submit_proposal
    if batch:
        return await organizer.organize_batch([message], commit)
    return commit(await organizer.propose(message))


@pytest.mark.parametrize("batch", [False, True], ids=["propose", "batch"])
@pytest.mark.parametrize("verdict,expected", [("supported", 1), ("contradicted", 0), ("unclear", 0)])
async def test_enabled_support_review_only_commits_supported_events(tmp_path, batch, verdict, expected):
    provider = SyntheticReviewProvider(verdict=verdict)
    store, message, organizer = setup_review(tmp_path, provider)
    await organize(organizer, store, message, batch)
    assert len(store.list_records("event")) == expected
    assert [r.purpose for r in provider.requests] == ["A1_batch" if batch else "A1", "A1_support"]
    request = provider.requests[-1]
    payload = json.loads(request.messages[-1]["content"])
    assert payload["sources"][message.ref]["text"] == "我喜欢红茶。"
    assert payload["claims"][0]["speaker_id"] == "person-a"
    checkpoints = [r for r in store.list_records("cognitive_run")
                   if r.payload.get("role") == ("A1_batch" if batch else "A1_chunk")]
    assert len(checkpoints) == 1
    assert checkpoints[0].payload["support_review"]["checks"][0]["verdict"] == verdict
    assert organizer._organized(message)
    assert store.verify_archive() == []


@pytest.mark.parametrize("batch", [False, True], ids=["propose", "batch"])
async def test_support_review_wrong_index_rejected_without_event_or_completed_marker(tmp_path, batch):
    provider = SyntheticReviewProvider(index=7)
    store, message, organizer = setup_review(tmp_path, provider)
    with pytest.raises(ValueError, match="every selected item exactly once"):
        await organize(organizer, store, message, batch)
    assert not store.list_records("event")
    assert not organizer._organized(message)
    assert len([r for r in store.list_records("cognitive_run") if r.record_id.endswith("_draft")]) == 1


@pytest.mark.parametrize("batch", [False, True], ids=["propose", "batch"])
async def test_failed_review_reuses_persisted_extraction_after_reopen(tmp_path, batch):
    provider = SyntheticReviewProvider(fail_reviews=1)
    store, message, organizer = setup_review(tmp_path, provider)
    with pytest.raises(RuntimeError, match="synthetic support review failed"):
        await organize(organizer, store, message, batch)
    drafts = [r for r in store.list_records("cognitive_run") if r.record_id.endswith("_draft")]
    assert len(drafts) == 1 and drafts[0].payload["role"] == "A1_extraction_awaiting_support"
    assert not store.list_records("event") and not organizer._organized(message)
    reopened = ArchiveStore(tmp_path, agent_id="xiaowennuan", user_id="group")
    retry = ExperienceOrganizer(reopened, Gateway(provider, retries=0))
    await organize(retry, reopened, reopened.get_record(message.record_id), batch)
    assert len(reopened.list_records("event")) == 1
    purposes = [r.purpose for r in provider.requests]
    assert purposes.count("A1_batch" if batch else "A1") == 1
    assert purposes.count("A1_support") == 2
    assert retry._organized(message)
    assert reopened.verify_archive() == []


@pytest.mark.parametrize("batch", [False, True], ids=["propose", "batch"])
async def test_review_disabled_preserves_single_extraction_call(tmp_path, batch):
    provider = SyntheticReviewProvider()
    store, message, organizer = setup_review(tmp_path, provider, enabled=False)
    await organize(organizer, store, message, batch)
    assert len(store.list_records("event")) == 1
    assert [r.purpose for r in provider.requests] == ["A1_batch" if batch else "A1"]
    assert not any(r.record_id.endswith("_draft") for r in store.list_records("cognitive_run"))


@pytest.mark.parametrize("batch", [False, True], ids=["propose", "batch"])
async def test_invalid_self_report_subject_rejected_before_review(tmp_path, batch):
    provider = SyntheticReviewProvider(subject="person-b")
    store, message, organizer = setup_review(tmp_path, provider)
    with pytest.raises(ValueError, match="subject_id"):
        await organize(organizer, store, message, batch)
    assert not store.list_records("event")
    assert [r.purpose for r in provider.requests] == ["A1_batch" if batch else "A1"]
