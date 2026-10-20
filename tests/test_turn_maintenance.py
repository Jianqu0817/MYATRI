"""Turn cadence and pre-compaction ordering; scripted providers only."""
import json
import pytest

from myatri.app import Application
from myatri.contracts import ModelResponse, JobSpec
from myatri.conversation.budget import TokenBudget


CONFIG = {"cognition": {"maintenance_turns": 20}, "context": {
    "limit": 1000000, "compact_at": 650000, "llm_activation": False},
    "budget": {"daily_tokens": 1000000}}


class BatchProvider:
    name = "script-batch"

    def __init__(self):
        self.requests = []
        self.fail_memory = False

    async def generate(self, request):
        self.requests.append(request)
        if request.role == "foreground":
            return ModelResponse(content="好的，继续聊。", provider=self.name, model="offline-script",
                                 usage={"prompt_tokens": 100, "completion_tokens": 10})
        payload = json.loads(request.messages[-1]["content"])
        if request.purpose == "A1_batch":
            if self.fail_memory:
                raise ValueError("scripted memory failure")
            events = []
            for row in payload["messages"]:
                if "我叫" in row["text"]:
                    events.append({"message_ref": row["ref"], "summary": "用户自述姓名为小林",
                        "quote": "我叫小林", "reality_scope": "reported", "occurred_at": None,
                        "event_key": "name", "participants": ["小林"]})
            value = {"events": events}
        elif request.purpose == "emotion_batch":
            value = {"appraisals": [{"event_ref": row["event_ref"], "decision": "propose",
                "reason": "离线合成评价", "appraisal": {"target": {"valence": .2, "arousal": .3, "dominance": .5},
                    "confidence": .5, "label": "关注", "meaning": "对方介绍了名字", "concern": ""},
                "evidence": row["evidence"][:1]} for row in payload["events"]]}
        elif request.role == "compaction":
            value = {"decision": "summarize", "reason": "合成摘要", "items": []}
        else:
            value = {"decision": "defer", "reason": "没有需要更新的充分证据"}
            for key in (request.output_schema or {}).get("required", []):
                if key not in value:
                    kind = request.output_schema.get("properties", {}).get(key, {}).get("type")
                    value[key] = [] if kind == "array" else False if kind == "boolean" else ""
        return ModelResponse(content=json.dumps(value, ensure_ascii=False), provider=self.name, model="offline-script",
                             usage={"prompt_tokens": 100, "completion_tokens": 30})


async def turns(app, count, start=0):
    for i in range(start, start + count):
        await app.conversation.respond("我叫小林" if i == 0 else f"闲聊第{i}轮", message_id=f"turn_{i}")
        await app.drain()


async def test_nineteen_turns_no_background_then_one_durable_batch_and_restart(tmp_path):
    provider = BatchProvider()
    app = Application(tmp_path, provider=provider, config=CONFIG)
    await turns(app, 19)
    assert len(provider.requests) == 19
    assert not app.store.list_records("summary")
    assert not app.store.list_records("event")
    assert len(app.store.list_records("raw_message")) == 38
    await turns(app, 1, start=19)
    assert len(app.store.list_records("event")) == 1
    assert len(app.store.list_records("emotion_appraisal")) == 1
    assert sum(r.purpose == "A1_batch" for r in provider.requests) == 1
    assert sum(r.purpose == "emotion_batch" for r in provider.requests) == 1
    assert len([j for j in app.queue.list_jobs() if j["role"] == "maintenance"]) == 1
    assert all(j["status"] == "succeeded" for j in app.queue.list_jobs())
    before = len(provider.requests)
    resumed = Application(tmp_path, provider=provider, config=CONFIG)
    resumed.recover_pending()
    await resumed.drain()
    assert len(provider.requests) == before
    assert resumed.store.verify_archive() == []


async def test_compression_flushes_memory_and_state_first(tmp_path):
    provider = BatchProvider()
    app = Application(tmp_path, provider=provider, config=CONFIG)
    await turns(app, 3)
    assert len(provider.requests) == 3
    summary = await app.conversation.context.compactor.acompact()
    purposes = [r.purpose for r in provider.requests]
    assert purposes.index("A1_batch") < purposes.index("emotion_batch") < purposes.index("context_compaction")
    assert purposes.index("temporary_state") < purposes.index("context_compaction")
    assert summary and app.store.list_records("event")
    before = len(provider.requests)
    await app.conversation.context.compactor.acompact()
    assert len(provider.requests) == before


async def test_failed_dependency_prevents_compression_and_preserves_all_raw(tmp_path):
    provider = BatchProvider()
    app = Application(tmp_path, provider=provider, config=CONFIG)
    await turns(app, 2)
    provider.fail_memory = True
    with pytest.raises(ValueError, match="scripted memory"):
        await app.conversation.context.compactor.acompact()
    assert not app.store.list_records("summary")
    assert len(app.store.list_records("raw_message")) == 4
    assert not any(r.role == "compaction" for r in provider.requests)


async def test_old_per_message_jobs_are_cancelled_not_replayed(tmp_path):
    app = Application(tmp_path, provider=BatchProvider(), config=CONFIG)
    raw = app.store.append_message("user", "旧消息", "old")
    job = app.queue.enqueue(JobSpec(role="ingest", input_refs=[raw.ref]))
    await app.drain()
    row = next(j for j in app.queue.list_jobs() if j["id"] == job)
    assert row["status"] == "cancelled"
    assert not app.gateway.provider.requests
    assert app.store.get_record("old").body_markdown == "旧消息"


def test_soft_context_threshold_is_separate_and_uses_real_usage_anchor():
    budget = TokenBudget(limit=1000000, compact_at=650000)
    old = [{"role": "user", "content": "很长的中文" * 50000}]
    budget.calibrate(old, {"prompt_tokens": 300000})
    assert budget.estimate(old) == 300064
    assert not budget.needs_compaction(old)
    grown = [*old, {"role": "user", "content": "新增" * 60000}]
    assert budget.needs_compaction(grown)
    assert budget.fits(grown)
    assert all(len(value) == 64 for value in budget.anchor["parts"])


async def test_batch_quote_forgery_cannot_publish_user_memory(tmp_path):
    class Forged(BatchProvider):
        async def generate(self, request):
            response = await super().generate(request)
            if request.purpose == "A1_batch":
                data = json.loads(response.content)
                data["events"][0]["quote"] = "不存在的用户原话"
                response.content = json.dumps(data, ensure_ascii=False)
            return response
    app = Application(tmp_path, provider=Forged(), config=CONFIG)
    await turns(app, 1)
    with pytest.raises(ValueError, match="outside"):
        await app.maintenance.before_compact()
    assert not app.store.list_records("event")


async def test_restart_after_state_failure_does_not_pay_for_memory_again(tmp_path):
    class FailState(BatchProvider):
        failing = True
        async def generate(self, request):
            if request.role == "temporary_state" and self.failing:
                raise ValueError("scripted state failure")
            return await super().generate(request)
    provider = FailState()
    app = Application(tmp_path, provider=provider, config=CONFIG)
    await turns(app, 2)
    with pytest.raises(ValueError, match="state failure"):
        await app.maintenance.before_compact()
    assert len(app.store.list_records("event")) == 1
    assert app.queue.get_meta("maintenance_cursor") is None
    provider.failing = False
    resumed = Application(tmp_path, provider=provider, config=CONFIG)
    await resumed.maintenance.before_compact()
    assert sum(r.purpose == "A1_batch" for r in provider.requests) == 1
    assert sum(r.purpose == "emotion_batch" for r in provider.requests) == 1
    assert resumed.queue.get_meta("maintenance_cursor") == "turn_1@1"


async def test_automatic_compression_obeys_soft_threshold_and_runs_dependencies(tmp_path):
    config = {**CONFIG, "context": {"limit": 1000000, "compact_at": 3000, "llm_activation": False}}
    provider = BatchProvider()
    app = Application(tmp_path, provider=provider, config=config)
    for i in range(7):
        app.store.append_message("user", f"较早的闲聊{i}", f"earlier_{i}")
    # A large newly received message forces automatic compression before the
    # ordinary 20-turn threshold, while preserving raw text and its sources.
    await app.conversation.respond("我叫小林。" + "普通内容。" * 250, message_id="large")
    purposes = [r.purpose for r in provider.requests]
    assert purposes.index("A1_batch") < purposes.index("context_compaction") < purposes.index("conversation")
    assert app.store.list_records("summary")
    assert app.store.get_record("large").body_markdown.endswith("普通内容。")


async def test_emotion_batch_wrong_source_is_rejected(tmp_path):
    from myatri.cognition.emotion import EmotionAgent
    from myatri.contracts import Event, SourceSpan, Record
    class ForgedEmotion(BatchProvider):
        async def generate(self, request):
            response = await super().generate(request)
            if request.purpose == "emotion_batch":
                data = json.loads(response.content)
                data["appraisals"][0]["evidence"][0]["quote"] = "伪造引文"
                response.content = json.dumps(data, ensure_ascii=False)
            return response
    app = Application(tmp_path, provider=ForgedEmotion(), config=CONFIG)
    raw = app.store.append_message("user", "我叫小林", "raw")
    event = Event(fact_summary="用户自述姓名", source_spans=[SourceSpan(message_ref=raw.ref, start=0, end=4, quote="我叫小林")],
                  event_fingerprint="test", reality_scope="reported")
    row = Record(record_id="event", record_kind="event", body_markdown="用户自述姓名", source_refs=[raw.ref], payload=event.model_dump())
    app.store.commit([row], "event")
    with pytest.raises(ValueError, match="outside"):
        await EmotionAgent(app.store, app.gateway).propose_batch([row.ref])
    assert not app.store.list_records("emotion_appraisal")
