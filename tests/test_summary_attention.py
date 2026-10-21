"""Long-lived summary attention uses durable raw provenance, entirely offline."""
import json

import pytest

from myatri.contracts import ModelResponse
from myatri.conversation.budget import TokenBudget
from myatri.conversation.compaction import Compactor
from myatri.conversation.context import ContextBuilder
from myatri.conversation.serialization import compact_json
from myatri.persona.patch import PersonaPatcher
from myatri.persona.state import PersonaState
from myatri.providers import Gateway
from myatri.retrieval import RecallService
from myatri.storage import ArchiveStore


class ExtractProvider:
    name = "offline-summary-attention"

    def __init__(self, prefix=""):
        self.requests, self.prefix = [], prefix

    async def generate(self, request):
        assert request.role == "compaction"
        self.requests.append(request.model_copy(deep=True))
        segments = json.loads(request.messages[-1]["content"])
        items = []
        for segment in segments:
            category, separator, text = segment["text"].partition("|")
            assert separator and category in {"agreement", "fact", "change", "open_question"}
            items.append({"category": category, "text": (self.prefix + text)[:240],
                "evidence": [{"ref": segment["ref"], "quote": text[:30]}]})
        assert len(items) <= 6
        return ModelResponse(content=json.dumps({"decision": "summarize", "reason": "offline source check",
            "items": items}, ensure_ascii=False), provider=self.name, model="fixture-attention")


def seed(tmp_path):
    store = ArchiveStore(tmp_path)
    PersonaState(store).initialize()
    return store


def append(store, category, text, name):
    return store.append_message("user", f"{category}|{text}", name)


def filler(store, start, count):
    for number in range(start, start + count):
        append(store, "fact", f"普通闲谈第{number}项。" + "各地云层与植物颜色没有额外约定。" * 12, f"filler_{number}")


def build(store, query, *, snapshot=None):
    builder = ContextBuilder(store, RecallService(store),
        budget=TokenBudget(limit=24000, output_reserve=512, safety=512))
    messages, _ = builder.build_context(query, snapshot=snapshot)
    return builder, messages


def projected(messages):
    blocks = [message["content"] for message in messages
              if message["content"].startswith("会话语义摘要（")]
    assert len(blocks) == 1
    return json.loads(blocks[0].split("\n", 1)[1])


@pytest.mark.asyncio
async def test_dense_summary_keeps_early_agreement_new_change_question_and_query_match(tmp_path):
    store = seed(tmp_path)
    agreement = append(store, "agreement", "早期约定：周末见面前先确认时间。", "early_agreement")
    filler(store, 0, 4)
    relevant = append(store, "fact", "讨论过鳍甲海豚探测计划的来源。", "relevant_middle")
    filler(store, 4, 16)
    provider = ExtractProvider()
    gateway = Gateway(provider, daily_token_limit=1000000)
    first = await Compactor(store, gateway, chunk_bytes=3000, max_chunks=64).acompact()
    assert sum(len(json.dumps(item, ensure_ascii=False).encode("utf-8"))
               for item in first.payload["semantic_items"]) > 5000
    change = append(store, "change", "后来变化：周六取消，改在周日碰面；先确认时间的习惯仍要核对。", "new_change")
    question = append(store, "open_question", "待确认：是否需要准备雨伞。", "new_question")
    filler(store, 20, 7)  # Neither change nor question can enter as last-six raw.
    second = await Compactor(store, gateway, chunk_bytes=3000, max_chunks=64).acompact()
    assert second.payload["reused_summary_ref"] == first.ref

    reopened = ArchiveStore(tmp_path)
    builder, messages = build(reopened, "鳍甲海豚探测计划")
    projection = projected(messages)
    refs = {ref for item in projection["items"] for ref in item["source_refs"]}
    assert {agreement.ref, relevant.ref, change.ref, question.ref} <= refs
    assert change.ref not in builder.explain_context()["history_refs"]
    assert question.ref not in builder.explain_context()["history_refs"]
    assert projection["omitted_source_count"] > 0 and projection["omitted_source_refs"]
    assert len(compact_json(projection["items"]).encode("utf-8")) <= 5000
    # Selection does not erase old agreements or manufacture a conflict ruling.
    assert "较早约定与后续变化" in projection["note"]
    assert reopened.get_record(agreement.record_id).body_markdown == agreement.body_markdown
    assert len(Compactor(reopened).current().payload["semantic_items"]) == len(second.payload["semantic_items"])
    assert reopened.verify_archive() == []


@pytest.mark.asyncio
async def test_attention_cannot_revive_invalidated_semantic_summary_through_either_path(tmp_path):
    store = seed(tmp_path)
    append(store, "agreement", "我答应周末前核对时间。", "agreement")
    provider = ExtractProvider(prefix="摘要专用失效标记：")
    summary = await Compactor(store, Gateway(provider)).acompact()
    past = store.snapshot()
    PersonaPatcher(store).human_edit("P03", "遇到安排变化时愿意核对双方期待。", "离线并发失效测试")
    assert Compactor(store).current() is None
    recalled = RecallService(store).recall("摘要专用失效标记", snapshot=past, budget=1800)
    assert summary.ref in {record.ref for record in recalled.records}

    builder, messages = build(store, "摘要专用失效标记", snapshot=past)
    explanation = builder.explain_context()
    assert explanation["summary_ref"] is None
    assert summary.ref not in explanation["recall_refs"]
    assert "摘要专用失效标记" not in json.dumps(messages, ensure_ascii=False)
    assert not any(message["content"].startswith("会话语义摘要（") for message in messages)
    assert store.get_record(summary.record_id).body_markdown == summary.body_markdown


@pytest.mark.asyncio
async def test_repeated_incremental_compaction_rotates_recent_attention_without_losing_early_agreement(tmp_path):
    store = seed(tmp_path)
    early = append(store, "agreement", "最早约定：涉及私人安排时先询问是否方便。", "early")
    provider = ExtractProvider()
    gateway = Gateway(provider, daily_token_limit=1000000)
    previous, prior_raw = None, set()
    for cycle in range(3):
        filler(store, cycle * 12, 12)
        change = append(store, "change", f"第{cycle}轮变化：出行地点有调整，须回查本轮原文。", f"change_{cycle}")
        agreement = append(store, "agreement", f"第{cycle}轮新约定：先确认本轮交通安排再出发。", f"agreement_{cycle}")
        before = len(provider.requests)
        summary = await Compactor(store, gateway, chunk_bytes=3000, max_chunks=64).acompact()
        assert summary.payload["strategy"] == "llm-semantic-v1"
        assert summary.payload["reused_summary_ref"] == (previous.ref if previous else None)
        inputs = {segment["ref"] for request in provider.requests[before:]
                  for segment in json.loads(request.messages[-1]["content"])}
        assert inputs.isdisjoint(prior_raw)
        prior_raw |= inputs
        store = ArchiveStore(tmp_path)
        builder, messages = build(store, f"第{cycle}轮新约定：先确认本轮交通安排再出发")
        projection = projected(messages)
        refs = {ref for item in projection["items"] for ref in item["source_refs"]}
        assert {early.ref, change.ref, agreement.ref} <= refs
        assert len(compact_json(projection["items"]).encode("utf-8")) <= 5000
        assert builder.budget.fits(messages)
        span = next(item for item in summary.payload["semantic_items"] if early.ref in item["source_refs"])["source_spans"][0]
        assert early.body_markdown[span["start"]:span["end"]] == span["quote"]
        previous = summary
    assert projection["omitted_source_count"] > 0
    assert store.verify_archive() == []
