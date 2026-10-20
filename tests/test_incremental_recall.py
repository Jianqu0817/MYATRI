import pytest

from myatri.storage import ArchiveStore
from myatri.memory import MemoryIndex
from myatri.retrieval import RecallService
from myatri.contracts import Record


async def test_base_vectors_remain_active_after_foreground_append(tmp_path):
    store = ArchiveStore(tmp_path)
    original = store.append_message("user", "我喜欢喝红茶", "tea")
    index = MemoryIndex(store)
    await index.update()
    fresh = store.append_message("user", "我现在也喝红茶", "new")
    bundle = RecallService(store, index).recall("红茶", budget=10000)
    assert original.ref in {r.ref for r in bundle.records}
    assert "vector:event" in bundle.reasons[original.ref]
    assert "vector-delta:event" in bundle.reasons[fresh.ref]


async def test_future_index_and_replaced_state_never_leak(tmp_path):
    store = ArchiveStore(tmp_path)
    origin = store.append_message("user", "想聊红茶", "origin")
    state = Record(record_id="s", record_kind="temporary_state", source_refs=[origin.ref], body_markdown="想聊红茶", payload={"status": "open"})
    store.commit([state], "initial")
    past = store.snapshot()
    index = MemoryIndex(store)
    await index.update()
    newer = Record(record_id="s", revision=2, supersedes_revision=1, record_kind="temporary_state",
                   source_refs=[origin.ref], body_markdown="红茶话题已放下", payload={"status": "discarded"})
    store.commit([newer], "replace")
    assert state.ref not in {r.ref for r in RecallService(store, index).recall("红茶", budget=10000).records}
    secret = store.append_message("user", "未来才知道的秘密红茶", "future")
    await index.update()
    bundle = RecallService(store, index).recall("红茶", snapshot=past, budget=10000)
    assert secret.ref not in {r.ref for r in bundle.records}
    assert not any(reason.startswith("vector") for reasons in bundle.reasons.values() for reason in reasons)


def test_identity_prefilter_happens_before_budget(tmp_path):
    store = ArchiveStore(tmp_path)
    others = [store.append_message("user", "红茶" * 200, f"other{i}") for i in range(5)]
    own = store.append_message("user", "红茶", "own")
    result = RecallService(store).recall("红茶", filters={"candidate_refs": [own.ref]}, budget=500)
    assert [r.ref for r in result.records] == [own.ref]
    assert not {r.ref for r in others} & {r.ref for r in result.records}


@pytest.mark.parametrize("limit", [1, 500])
def test_evidence_companions_fit_atomically(tmp_path, limit):
    store = ArchiveStore(tmp_path)
    raw = store.append_message("user", "我现在不喝红茶", "raw")
    claim = Record(record_id="claim", record_kind="interpretation", source_refs=[raw.ref], body_markdown="红茶偏好已更正")
    store.commit([claim], "claim")
    result = RecallService(store).recall("偏好", filters={"evidence_companions": {claim.ref: [raw.ref]}}, budget=limit)
    refs = {r.ref for r in result.records}
    assert (claim.ref in refs) == (raw.ref in refs)
