"""Offline contract and production-path tests; no real API/credentials."""
import asyncio
import json

import httpx
import pytest

from myatri.app import Application
from myatri.contracts import ModelResponse, Record, TemporaryEntry
from myatri.conversation.budget import TokenBudget
from myatri.conversation.compaction import Compactor
from myatri.conversation.context import ContextBuilder
from myatri.persona.patch import PersonaPatcher
from myatri.persona.state import PersonaState
from myatri.persona.temporary import TemporaryStates
from myatri.providers import DeepSeekProvider, FixtureProvider, Gateway, ProviderError
from myatri.retrieval import RecallService
from myatri.storage import ArchiveStore


class ScriptProvider:
    name = "offline-script"

    def __init__(self, handler):
        self.handler, self.requests = handler, []

    async def generate(self, request):
        self.requests.append(request.model_copy(deep=True))
        value = self.handler(request)
        if hasattr(value, "__await__"):
            value = await value
        if isinstance(value, ModelResponse):
            return value
        return ModelResponse(content=json.dumps(value, ensure_ascii=False), provider=self.name, model="contract-test")


def summary_item(ref="old@1", quote="我答应周六先确认时间", text="用户约定周六先确认时间"):
    return {"decision": "summarize", "reason": "离线脚本验证来源", "items": [
        {"category": "agreement", "text": text, "evidence": [{"ref": ref, "quote": quote}]}]}


def seeded(tmp_path):
    store = ArchiveStore(tmp_path)
    PersonaState(store).initialize()
    raw = store.append_message("user", "普通闲聊。" * 60 + "我答应周六先确认时间", "old")
    return store, raw


async def test_semantic_summary_recovers_late_agreement_keeps_exact_source_and_restart(tmp_path):
    store, raw = seeded(tmp_path)
    provider = ScriptProvider(lambda request: summary_item())
    compactor = Compactor(store, Gateway(provider))
    summary = await compactor.acompact(preserve_ids=[raw.record_id])
    assert summary.payload["strategy"] == "llm-semantic-v1"
    assert summary.author_kind == "model" and summary.generator["prompt_version"] == "compaction/v1"
    span = summary.payload["semantic_items"][0]["source_spans"][0]
    assert raw.body_markdown[span["start"]:span["end"]] == span["quote"]
    assert span["start"] > 160
    assert summary.payload["excerpts"][0]["text"] == raw.body_markdown
    reopened = ArchiveStore(tmp_path)
    assert Compactor(reopened).current().ref == summary.ref
    assert reopened.get_record(raw.record_id).body_markdown == raw.body_markdown
    # Unchanged material reuses the already validated result across restarts.
    again = await Compactor(reopened, Gateway(provider)).acompact()
    assert again.ref == summary.ref and len(provider.requests) == 1
    assert reopened.verify_archive() == []


@pytest.mark.parametrize("failure", ["invented_quote", "unknown_ref", "defer", "timeout", "bad_schema", "fixture"])
async def test_invalid_or_unavailable_semantics_explicitly_fall_back(tmp_path, failure):
    store, raw = seeded(tmp_path)
    def answer(request):
        if failure == "timeout":
            raise TimeoutError("offline simulated timeout")
        if failure == "defer":
            return {"decision": "defer", "reason": "暂缓", "items": []}
        if failure == "bad_schema":
            return {"decision": "summarize", "reason": "缺字段"}
        return summary_item(ref="invented@1" if failure == "unknown_ref" else raw.ref,
                            quote="并不存在的原话" if failure == "invented_quote" else "我答应周六先确认时间")
    provider = FixtureProvider() if failure == "fixture" else ScriptProvider(answer)
    summary = await Compactor(store, Gateway(provider, retries=0)).acompact()
    assert summary.payload["strategy"] == "source-excerpts-v1"
    assert summary.author_kind == "system" and summary.generator is None
    assert any("fallback" in text for text in summary.payload["limitations"])
    assert len(store.list_records("summary")) == 1  # No partial semantic publication.
    assert store.get_record(raw.record_id).body_markdown == raw.body_markdown


async def test_chunking_covers_originals_without_recursive_summaries_and_checks_input_cap(tmp_path):
    store, first = seeded(tmp_path)
    second = store.append_message("assistant", "新的完整原文。" * 120, "second")
    provider = ScriptProvider(lambda request: {"decision": "summarize", "reason": "此段无重要约定", "items": []})
    compactor = Compactor(store, Gateway(provider, daily_token_limit=200000), chunk_bytes=1500)
    summary = await compactor.acompact()
    assert summary.payload["strategy"] == "llm-semantic-v1"
    assert len(provider.requests) > 1
    pieces = [segment for request in provider.requests for segment in json.loads(request.messages[-1]["content"])]
    for original in (first, second):
        segments = [p for p in pieces if p["ref"] == original.ref]
        assert "".join(p["text"] for p in segments) == original.body_markdown
        assert all(original.body_markdown[p["start"]:p["end"]] == p["text"] for p in segments)
    store.append_message("user", "更新材料。", "third")
    provider.requests.clear()
    await compactor.acompact()
    assert all("summary_" not in row["ref"] for request in provider.requests
               for row in json.loads(request.messages[-1]["content"]))
    provider.requests.clear()
    capped = await Compactor(store, Gateway(provider), chunk_bytes=1000, max_chunks=1).acompact(preserve_ids=[first.ref])
    # A current semantic cache may be reused; force a new source to exercise cap.
    store.append_message("user", "更多新材料", "fourth")
    capped = await Compactor(store, Gateway(provider), chunk_bytes=1000, max_chunks=1).acompact()
    assert capped.payload["strategy"] == "llm-semantic-v1"
    assert len(provider.requests) == 1
    assert {row["ref"] for row in json.loads(provider.requests[0].messages[-1]["content"])} == {"fourth@1"}


async def test_incremental_summary_retains_old_agreement_and_exact_raw_spans_across_restarts(tmp_path):
    store, raw = seeded(tmp_path)
    def answer(request):
        segments = json.loads(request.messages[-1]["content"])
        if any(s["ref"] == raw.ref and "我答应周六先确认时间" in s["text"] for s in segments):
            return summary_item()
        return {"decision": "summarize", "reason": "新增原文没有新的约定", "items": []}
    provider = ScriptProvider(answer)
    gateway = Gateway(provider, daily_token_limit=1000000)
    first = await Compactor(store, gateway).acompact()
    for cycle in range(3):
        store.append_message("user", f"新增普通对话{cycle}。" * 35, f"delta_{cycle}")
        store = ArchiveStore(tmp_path)
        before = len(provider.requests)
        summary = await Compactor(store, gateway, chunk_bytes=1000, max_chunks=1).acompact()
        request = provider.requests[before:]
        assert len(request) == 1
        assert {s["ref"] for s in json.loads(request[0].messages[-1]["content"])} == {f"delta_{cycle}@1"}
        # A long delta can span multiple capped passes. Each restart resumes its raw cursor.
        for _ in range(5):
            if len(summary.payload["source_range"]) == len(store.list_records("raw_message")):
                break
            store = ArchiveStore(tmp_path)
            summary = await Compactor(store, gateway, chunk_bytes=1000, max_chunks=1).acompact()
        assert summary.payload["semantic_items"] == first.payload["semantic_items"]
        assert len(summary.payload["source_range"]) == len(store.list_records("raw_message"))
        span = summary.payload["semantic_items"][0]["source_spans"][0]
        assert store.get_record("old").body_markdown[span["start"]:span["end"]] == span["quote"]
    assert store.verify_archive() == []


async def test_more_than_batch_limit_makes_bounded_progress_instead_of_permanent_fallback(tmp_path):
    store, first = seeded(tmp_path)
    long_raw = store.append_message("assistant", "长原文保持完整。" * 250, "oversized")
    provider = ScriptProvider(lambda request: {"decision": "summarize", "reason": "无新的约定", "items": []})
    gateway = Gateway(provider, daily_token_limit=1000000)
    compactor = Compactor(store, gateway, chunk_bytes=1000, max_chunks=1)
    assert len(compactor._chunks(store.list_records("raw_message"))) > 8
    summary = await compactor.acompact()
    assert summary.payload["strategy"] == "llm-semantic-v1"
    assert len(provider.requests) == 1
    assert any("pending" in row for row in summary.payload["limitations"])
    assert long_raw.ref not in summary.payload["source_range"]
    for _ in range(30):
        if set(summary.payload["source_range"]) == {first.ref, long_raw.ref}:
            break
        store = ArchiveStore(tmp_path)
        before = len(provider.requests)
        summary = await Compactor(store, gateway, chunk_bytes=1000, max_chunks=1).acompact()
        assert len(provider.requests) - before <= 1
    assert set(summary.payload["source_range"]) == {first.ref, long_raw.ref}
    pieces = [s for request in provider.requests for s in json.loads(request.messages[-1]["content"])]
    for record in (first, long_raw):
        assert "".join(s["text"] for s in pieces if s["ref"] == record.ref) == record.body_markdown
    assert all("summary_" not in s["ref"] for s in pieces)


async def test_failed_delta_keeps_verified_old_agreement_and_does_not_cover_new_raw(tmp_path):
    store, raw = seeded(tmp_path)
    first = await Compactor(store, Gateway(ScriptProvider(lambda request: summary_item()))).acompact()
    fresh = store.append_message("user", "新增材料中的约定还没有处理。", "unprocessed")
    failing = ScriptProvider(lambda request: {"decision": "defer", "reason": "离线模拟失败", "items": []})
    retained = await Compactor(store, Gateway(failing)).acompact()
    assert retained.payload["strategy"] == "llm-semantic-v1"
    assert retained.payload["semantic_items"] == first.payload["semantic_items"]
    assert retained.payload["reused_summary_ref"] == first.ref
    assert retained.payload["source_range"] == [raw.ref]
    assert fresh.ref not in retained.payload["source_range"]
    assert any("fallback" in row for row in retained.payload["limitations"])
    builder = ContextBuilder(store, RecallService(store), gateway=Gateway(failing))
    messages, _ = await builder.abuild_context("其他话题")
    assert "用户约定周六先确认时间" in json.dumps(messages, ensure_ascii=False)
    assert fresh.ref in builder.explain_context()["history_refs"]


async def test_existing_summary_is_automatically_extended_after_growth_and_restart(tmp_path):
    store, _ = seeded(tmp_path)
    def answer(request):
        segments = json.loads(request.messages[-1]["content"])
        if any(s["ref"] == "old@1" and "我答应周六先确认时间" in s["text"] for s in segments):
            return summary_item()
        return {"decision": "summarize", "reason": "其他片段", "items": []}
    provider = ScriptProvider(answer)
    gateway = Gateway(provider, daily_token_limit=1000000)
    prior = None
    for cycle in range(3):
        for index in range(cycle * 20, (cycle + 1) * 20):
            store.append_message("user" if index % 2 else "assistant", "普通其他话题。" * 25, f"growth_{index}")
        store = ArchiveStore(tmp_path)
        builder = ContextBuilder(store, RecallService(store), gateway=gateway,
            budget=TokenBudget(limit=11000, output_reserve=512, safety=512))
        messages, _ = await builder.abuild_context("说点别的")
        summary = builder.compactor.current()
        assert summary.ref != prior
        prior = summary.ref
        assert summary.payload["strategy"] == "llm-semantic-v1"
        assert "用户约定周六先确认时间" in json.dumps(messages, ensure_ascii=False)
        assert builder.budget.fits(messages)
        assert len(builder.explain_context()["history_refs"]) <= 6
    assert store.verify_archive() == []


async def test_summary_cannot_publish_with_persona_version_changed_during_api_wait(tmp_path):
    store, _ = seeded(tmp_path)
    async def exercise():
        entered, release = asyncio.Event(), asyncio.Event()
        async def answer(request):
            entered.set()
            await release.wait()
            return summary_item()
        task = asyncio.create_task(Compactor(store, Gateway(ScriptProvider(answer))).acompact())
        await entered.wait()
        PersonaPatcher(store).human_edit("P03", "用户修改后的当前条目", "并发修改测试")
        release.set()
        summary = await task
        assert summary.payload["strategy"] == "source-excerpts-v1"
        assert summary.payload["persona_ref"] == "persona@2"
        assert any("ConflictError" in row for row in summary.payload["limitations"])
        assert len(store.list_records("summary")) == 1
    await exercise()


async def test_new_state_invalidates_summary_even_without_revision_change(tmp_path):
    store, _ = seeded(tmp_path)
    compactor = Compactor(store, Gateway(ScriptProvider(lambda request: summary_item())))
    await compactor.acompact()
    run = Record(record_id="idea_run", record_kind="cognitive_run")
    store.commit([run], "idea")
    TemporaryStates(store).create(TemporaryEntry(text="新的念头", origin_kind="generated_idea", origin_refs=[run.ref]))
    assert compactor.current() is None


async def test_automatic_production_context_uses_llm_summary_and_keeps_important_old_detail(tmp_path):
    store, _ = seeded(tmp_path)
    for index in range(20):
        store.append_message("user" if index % 2 else "assistant", "普通其他话题。" * 25, f"turn{index}")
    def answer(request):
        segments = json.loads(request.messages[-1]["content"])
        if any(s["ref"] == "old@1" and "我答应周六先确认时间" in s["text"] for s in segments):
            return summary_item()
        return {"decision": "summarize", "reason": "其他片段", "items": []}
    provider = ScriptProvider(answer)
    builder = ContextBuilder(store, RecallService(store), gateway=Gateway(provider, daily_token_limit=200000),
                             budget=TokenBudget(limit=11000, output_reserve=512, safety=512))
    messages, snapshot = await builder.abuild_context("说点别的")
    explanation = builder.explain_context()
    assert explanation["summary_strategy"] == "llm-semantic-v1"
    assert "old@1" not in explanation["history_refs"]
    assert "用户约定周六先确认时间" in json.dumps(messages, ensure_ascii=False)
    assert builder.budget.fits(messages)
    assert snapshot == explanation["snapshot"]
    assert {r.role for r in provider.requests} == {"compaction"}


async def test_open_state_llm_selection_is_injected_into_real_conversation_path(tmp_path):
    seen = []
    def answer(request):
        seen.append(request.role)
        if request.role == "activation":
            return {"decision": "select", "reason": "同义情境", "selected": [{"ref": "intent@1", "reason": "相关"}]}
        assert request.role == "foreground"
        assert "改期时先把自己的愿望讲清楚" in request.messages[1]["content"]
        return ModelResponse(content="我会先说清自己的需求。", provider="offline-script", model="contract-test")
    app = Application(tmp_path, provider=ScriptProvider(answer))
    run = Record(record_id="idea_run", record_kind="cognitive_run")
    app.store.commit([run], "idea")
    app.states.create(TemporaryEntry(text="改期时先把自己的愿望讲清楚", origin_kind="generated_idea", origin_refs=[run.ref]), entry_id="intent")
    result = await app.conversation.respond("以后遇到日程变动，我会坦率说出需求", message_id="turn")
    assert seen == ["activation", "foreground"]
    assert result.payload["role"] == "assistant"
    assert app.conversation.context.explain_context()["activation"]["selection_method"] == "llm"
    assert app.store.get_record("intent").revision == 1 and app.persona.read_state().revision == 1


async def test_compaction_rejects_unfinished_protocol_before_any_model_call(tmp_path):
    store, _ = seeded(tmp_path)
    provider = ScriptProvider(lambda request: pytest.fail("must not call model"))
    pending = [{"role": "assistant", "content": "", "tool_calls": [{"id": "t", "function": {"name": "read_record", "arguments": "{}"}}]}]
    with pytest.raises(ProviderError, match="unfinished"):
        await Compactor(store, Gateway(provider)).acompact(protocol_messages=pending)
    assert store.list_records("summary") == []


async def test_official_adapter_sends_both_new_role_schemas_without_real_network(tmp_path):
    """HTTP transport fixture verifies official wire path, not a live API test."""
    bodies = []
    def transport(request):
        body = json.loads(request.content)
        bodies.append(body)
        material = json.loads(body["messages"][-1]["content"])
        if isinstance(material, dict) and "candidates" in material:
            result = {"decision": "select", "selected": [], "reason": "暂不激活"}
        else:
            result = summary_item()
        assert body["response_format"] == {"type": "json_object"}
        assert "JSON Schema" in body["messages"][0]["content"]
        return httpx.Response(200, request=request, json={"model": "deepseek-flash", "usage": {"total_tokens": 10},
            "choices": [{"message": {"content": json.dumps(result, ensure_ascii=False)}, "finish_reason": "stop"}]})
    store, _ = seeded(tmp_path)
    run = Record(record_id="idea_run", record_kind="cognitive_run")
    store.commit([run], "idea")
    TemporaryStates(store).create(TemporaryEntry(text="暂时的想法", origin_kind="generated_idea", origin_refs=[run.ref]))
    async with httpx.AsyncClient(transport=httpx.MockTransport(transport)) as client:
        gateway = Gateway(DeepSeekProvider(model="deepseek-flash", api_key="offline-test-key", allow_paid=True, client=client))
        from myatri.persona.activation import ActivationSelector
        _, activation = await ActivationSelector(store, gateway=gateway).aselect_active_entries("其他话题")
        summary = await Compactor(store, gateway).acompact()
    assert len(bodies) == 2
    assert activation.selection_method == "llm" and summary.payload["strategy"] == "llm-semantic-v1"


async def test_retracted_state_and_old_summary_cannot_reenter_through_recall_after_model_wait(tmp_path):
    app = Application(tmp_path)
    run = Record(record_id="idea_run", record_kind="cognitive_run")
    app.store.commit([run], "idea")
    state = app.states.create(TemporaryEntry(text="散步时想表达期待", origin_kind="generated_idea", origin_refs=[run.ref]), entry_id="intent")
    app.store.append_message("assistant", "我想在散步时表达期待", "old_turn")
    old_summary = Compactor(app.store).compact()
    fixed = app.store.snapshot()
    entered, release = asyncio.Event(), asyncio.Event()
    async def answer(request):
        entered.set()
        await release.wait()
        return {"decision": "select", "reason": "原先相关", "selected": [{"ref": state.ref, "reason": "相关"}]}
    builder = ContextBuilder(app.store, app.recall, gateway=Gateway(ScriptProvider(answer)))
    pending = asyncio.create_task(builder.abuild_context("散步期待", snapshot=fixed))
    await entered.wait()
    app.states.review(state.record_id, base_revision=1, status="discarded", reason="模型等待期间撤回")
    release.set()
    messages, _ = await pending
    explanation = builder.explain_context()
    assert explanation["active_state_refs"] == []
    assert state.ref not in explanation["recall_refs"]
    assert old_summary.ref not in explanation["recall_refs"]
    assert explanation["summary_ref"] is None
    assert "散步时想表达期待" not in messages[1]["content"]


@pytest.mark.parametrize("role", ["activation", "compaction"])
async def test_context_preparation_does_not_wait_for_background_slot(role):
    entered, release = asyncio.Event(), asyncio.Event()
    async def answer(request):
        if request.role == "reflection":
            entered.set()
            await release.wait()
        return {"ok": True}
    from myatri.contracts import ModelRequest
    gateway = Gateway(ScriptProvider(answer), foreground_limit=1, background_limit=1)
    background = asyncio.create_task(gateway.generate(ModelRequest(role="reflection", messages=[])))
    await entered.wait()
    try:
        result = await asyncio.wait_for(gateway.generate(ModelRequest(role=role, messages=[])), timeout=1)
        assert result.provider == "offline-script"
    finally:
        release.set()
        await background


async def test_disabled_semantic_compaction_uses_explicit_baseline_without_call(tmp_path):
    store, _ = seeded(tmp_path)
    provider = ScriptProvider(lambda request: pytest.fail("disabled compaction cannot call API"))
    summary = await Compactor(store, Gateway(provider), llm_enabled=False).acompact()
    assert summary.payload["strategy"] == "source-excerpts-v1" and provider.requests == []
    assert "disabled" in summary.payload["limitations"][0]
