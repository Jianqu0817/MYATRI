"""Offline scripted gateway tests for the semantic activation control path.

These scripts verify contracts, snapshot safety and program limits. They do not
establish live model quality, incur API cost, or read credentials.
"""
import asyncio
import json

import pytest

from myatri.contracts import ModelResponse, Record, TemporaryEntry
from myatri.persona.activation import ActivationSelector
from myatri.persona.state import PersonaState
from myatri.persona.temporary import TemporaryStates
from myatri.providers import FixtureProvider, Gateway
from myatri.storage import ArchiveStore, ConflictError


class ScriptProvider:
    name = "offline-script"

    def __init__(self, handler):
        self.handler, self.requests = handler, []

    async def generate(self, request):
        self.requests.append(request.model_copy(deep=True))
        result = self.handler(request)
        if hasattr(result, "__await__"):
            result = await result
        return ModelResponse(content=json.dumps(result, ensure_ascii=False), provider="offline-script", model="activation-contract-test")


def seeded(tmp_path, texts=None):
    store = ArchiveStore(tmp_path)
    PersonaState(store).initialize()
    run = Record(record_id="seed_run", record_kind="cognitive_run", payload={"role": "test_candidate_generation"})
    store.commit([run], "seed")
    states = TemporaryStates(store)
    records = [states.create(TemporaryEntry(text=text, scope="下次约会", origin_kind="generated_idea", origin_refs=[run.ref]), entry_id=f"thought_{number}")
               for number, text in enumerate(texts or ["改期时先把自己的愿望讲清楚"])]
    return store, states, records


def selection(*refs):
    return {"decision": "select", "selected": [{"ref": ref, "reason": "当前情境与这条暂定想法相关"} for ref in refs], "reason": "离线结构化选择脚本"}


def test_synonym_without_lexical_hit_still_reaches_model_and_selects_existing_state(tmp_path):
    store, states, records = seeded(tmp_path)
    record = records[0]
    context = "以后碰到日程变动，我会坦率说出需求"
    assert ActivationSelector(store).select_active_entries(context, persist=False)[0] == []
    before = store.get_record("persona")
    provider = ScriptProvider(lambda request: selection(record.ref))
    selected, activation = asyncio.run(ActivationSelector(store, gateway=Gateway(provider)).aselect_active_entries(context))
    assert [r.ref for r in selected] == [record.ref]
    assert activation.selection_method == "llm"
    assert activation.saliency_components[record.ref]["context_overlap"] == 0
    request = provider.requests[0]
    assert request.role == "activation" and request.prompt_version == "activation/v1"
    assert json.loads(request.messages[-1]["content"])["candidates"][0]["ref"] == record.ref
    trace = store.list_records("activation")[-1]
    assert trace.generator == activation.generator
    assert trace.generator["run_id"] == trace.record_id
    assert trace.generator["provider"] == "offline-script"
    assert states.list()[0].ref == record.ref
    assert store.get_record("persona").content_hash == before.content_hash
    assert store.list_records("behavior_attempt") == store.list_records("event") == []


def test_model_can_choose_none_even_when_heuristic_would_select(tmp_path):
    store, _, records = seeded(tmp_path, ["散步时想先表达期待"])
    provider = ScriptProvider(lambda request: selection())
    selected, activation = asyncio.run(ActivationSelector(store, gateway=Gateway(provider)).aselect_active_entries("散步期待"))
    assert selected == [] and activation.selected_refs == []
    assert activation.selection_method == "llm"
    assert store.get_record(records[0].record_id).payload["status"] == "open"


def test_conflicting_states_coexist_but_program_limits_count(tmp_path):
    store, _, records = seeded(tmp_path, ["散步时想表达期待", "散步时想先保留期待"])
    provider = ScriptProvider(lambda request: selection(*(r.ref for r in records)))
    selected, snapshot = asyncio.run(ActivationSelector(store, gateway=Gateway(provider)).aselect_active_entries("散步期待", max_entries=1))
    assert [r.ref for r in selected] == [records[0].ref]
    assert any("clipped" in limitation for limitation in snapshot.limitations)
    provider = ScriptProvider(lambda request: selection(*(r.ref for r in records)))
    together, _ = asyncio.run(ActivationSelector(store, gateway=Gateway(provider)).aselect_active_entries("散步期待", max_entries=2))
    assert {r.ref for r in together} == {r.ref for r in records}
    assert all(r.payload["status"] == "open" for r in store.list_records("temporary_state"))


def test_full_body_budget_prevents_large_selected_state_injection(tmp_path):
    store, _, records = seeded(tmp_path, ["散步时想表达期待。" * 100])
    provider = ScriptProvider(lambda request: selection(records[0].ref))
    selected, activation = asyncio.run(ActivationSelector(store, gateway=Gateway(provider)).aselect_active_entries("散步期待", budget=60))
    assert selected == []
    assert any("clipped_by_program" in limitation for limitation in activation.limitations)
    assert any("candidate_text_truncated" in limitation for limitation in activation.limitations)
    assert store.get_record(records[0].record_id).body_markdown == records[0].body_markdown


@pytest.mark.parametrize("invalid", ["unknown", "duplicate", "closed", "rewrite"])
def test_invalid_reference_or_rewrite_is_explicit_heuristic_fallback(tmp_path, invalid):
    store, states, records = seeded(tmp_path, ["散步时想表达期待", "另一条已经撤回的念头"])
    states.review(records[1].record_id, base_revision=1, status="discarded", reason="已撤回")
    def reply(request):
        offered = json.loads(request.messages[-1]["content"])["candidates"]
        assert {row["ref"] for row in offered} == {records[0].ref}
        if invalid == "unknown":
            return selection("invented@1")
        if invalid == "duplicate":
            return selection(records[0].ref, records[0].ref)
        if invalid == "closed":
            return selection(records[1].ref)
        value = selection(records[0].ref)
        value["selected"][0]["text"] = "不得改写正文"
        return value
    selected, activation = asyncio.run(ActivationSelector(store, gateway=Gateway(ScriptProvider(reply), retries=0)).aselect_active_entries("散步期待"))
    assert {r.ref for r in selected} == {records[0].ref}
    assert activation.selection_method == "heuristic_fallback"
    assert any("model_selection_failed" in limitation for limitation in activation.limitations)
    assert store.get_record(records[0].record_id).body_markdown == records[0].body_markdown
    assert store.get_record(records[1].record_id).payload["status"] == "discarded"


@pytest.mark.parametrize("mode", ["timeout", "defer", "default_fixture"])
def test_failure_and_defer_fallback_are_transparent(tmp_path, mode):
    store, _, records = seeded(tmp_path, ["散步时想表达期待"])
    def reply(request):
        if mode == "timeout":
            raise TimeoutError("offline test timeout")
        return {"decision": "defer", "selected": [], "reason": "没有把握，只保留启发式线索"}
    provider = FixtureProvider() if mode == "default_fixture" else ScriptProvider(reply)
    selected, activation = asyncio.run(ActivationSelector(store, gateway=Gateway(provider, retries=0)).aselect_active_entries("散步期待"))
    assert [r.ref for r in selected] == [records[0].ref]
    assert activation.selection_method == "heuristic_fallback"
    assert any("model_defer" in limitation or "model_selection_failed" in limitation for limitation in activation.limitations)
    assert len(provider.requests) == 1


def test_waiting_model_result_cannot_activate_retracted_or_revised_state(tmp_path):
    store, states, records = seeded(tmp_path, ["散步时想表达期待", "散步时想先确认安排"])
    async def exercise():
        entered, release = asyncio.Event(), asyncio.Event()
        async def reply(request):
            entered.set()
            await release.wait()
            return selection(*(r.ref for r in records))
        selector = ActivationSelector(store, gateway=Gateway(ScriptProvider(reply)))
        fixed = store.snapshot()
        task = asyncio.create_task(selector.aselect_active_entries("散步期待", snapshot=fixed))
        await entered.wait()
        states.review(records[0].record_id, base_revision=1, status="discarded", reason="等模型期间撤回")
        states.review(records[1].record_id, base_revision=1, text="改版后的新想法", reason="等模型期间更新")
        release.set()
        selected, activation = await task
        assert selected == []
        assert activation.context_snapshot == fixed
        assert activation.selection_method == "heuristic_fallback"
        assert any("changed_after_await" in limitation for limitation in activation.limitations)
        assert activation.selected_refs == []
        trace = store.list_records("activation")[-1]
        assert all(record.ref in trace.source_refs for record in store.list_records("temporary_state"))
    asyncio.run(exercise())


def test_closed_or_no_candidates_do_not_call_gateway(tmp_path):
    store, states, records = seeded(tmp_path)
    states.review(records[0].record_id, base_revision=1, status="paused", reason="先暂停")
    provider = ScriptProvider(lambda request: pytest.fail("No open states may call provider"))
    selected, activation = asyncio.run(ActivationSelector(store, gateway=Gateway(provider)).aselect_active_entries("散步期待"))
    assert selected == [] and activation.entry_refs == []
    assert provider.requests == []
    assert store.list_records("activation") == []


def test_model_pool_and_context_are_bounded_without_dropping_zero_lexical_candidates(tmp_path):
    store, _, records = seeded(tmp_path, [f"独立念头{number}：" + "完全保留正文" * 100 for number in range(20)])
    def reply(request):
        payload = json.loads(request.messages[-1]["content"])
        assert 0 < len(payload["candidates"]) <= 12
        assert len(json.dumps(payload["candidates"], ensure_ascii=False).encode("utf-8")) <= 6000
        assert len(payload["context"].encode("utf-8")) <= 2048
        return selection()
    selected, activation = asyncio.run(ActivationSelector(store, gateway=Gateway(ScriptProvider(reply))).aselect_active_entries("不相交的其他话题" * 1000))
    assert selected == [] and activation.selection_method == "llm"
    assert any("bounded_candidate_pool" in limitation for limitation in activation.limitations)
    assert any("context_truncated" in limitation for limitation in activation.limitations)


def test_persistence_cas_revalidates_race_and_never_returns_old_open_state(tmp_path, monkeypatch):
    store, states, records = seeded(tmp_path, ["散步时想表达期待"])
    original = store.commit
    raced = False
    def racing_commit(batch, *args, **kwargs):
        nonlocal raced
        if batch[0].record_kind == "activation" and not raced:
            raced = True
            states.review(records[0].record_id, base_revision=1, status="discarded", reason="trace提交前发生撤回")
        return original(batch, *args, **kwargs)
    monkeypatch.setattr(store, "commit", racing_commit)
    selected, activation = asyncio.run(ActivationSelector(store, gateway=Gateway(ScriptProvider(lambda request: selection(records[0].ref)))).aselect_active_entries("散步期待"))
    assert selected == []
    assert any("CAS_conflict" in limitation for limitation in activation.limitations)
    assert len(store.list_records("activation")) == 1
    assert store.get_record(records[0].record_id).payload["status"] == "discarded"


def test_repeated_cas_conflict_returns_safe_empty_without_claiming_trace(tmp_path, monkeypatch):
    store, _, records = seeded(tmp_path, ["散步时想表达期待"])
    original = store.commit
    def denied_commit(batch, *args, **kwargs):
        if batch[0].record_kind == "activation":
            raise ConflictError("offline conflict injection")
        return original(batch, *args, **kwargs)
    monkeypatch.setattr(store, "commit", denied_commit)
    selected, activation = asyncio.run(ActivationSelector(store, gateway=Gateway(ScriptProvider(lambda request: selection(records[0].ref)))).aselect_active_entries("散步期待"))
    assert selected == [] and activation.selection_method == "heuristic_fallback"
    assert any("not_persisted" in limitation for limitation in activation.limitations)
    assert store.list_records("activation") == []


def test_persisted_activation_trace_round_trips_after_restart(tmp_path):
    store, _, records = seeded(tmp_path, ["散步时想表达期待"])
    provider = ScriptProvider(lambda request: selection(records[0].ref))
    selected, activation = asyncio.run(ActivationSelector(store, gateway=Gateway(provider)).aselect_active_entries("散步期待"))
    restored = ArchiveStore(tmp_path)
    trace = restored.list_records("activation")[-1]
    assert trace.payload["selection_method"] == "llm"
    assert trace.payload["selected_refs"] == activation.selected_refs == [records[0].ref]
    assert trace.payload["generator"] == trace.generator == activation.generator
    assert trace.generator["prompt_version"] == "activation/v1"
    assert trace.generator["run_id"] == trace.record_id
    assert restored.get_record(records[0].record_id).ref == records[0].ref


def test_disabled_llm_uses_explicit_heuristic_without_gateway_call(tmp_path):
    store, _, records = seeded(tmp_path, ["散步时想表达期待"])
    provider = ScriptProvider(lambda request: pytest.fail("disabled activation must not call provider"))
    selected, activation = asyncio.run(ActivationSelector(store, gateway=Gateway(provider), llm_enabled=False).aselect_active_entries("散步期待"))
    assert [record.ref for record in selected] == [records[0].ref]
    assert provider.requests == []
    assert activation.selection_method == "heuristic"
    assert "llm_activation_disabled" in activation.limitations
    assert activation.generator is None
