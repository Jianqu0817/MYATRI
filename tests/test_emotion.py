"""Emotion source integrity, deterministic replay and production integration.

Synthetic semantic responses are protocol fixtures, not live-model evidence.
"""
import json
import math
from datetime import datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from myatri._vendor.emotional_memory import lerp_pad, pad_distance, regress_pad, update_mood
from myatri.app import Application
from myatri.cognition.emotion import APPRAISAL_SCHEMA, EmotionAgent
from myatri.contracts import Event, Record, SourceSpan, digest
from myatri.contracts.emotion import EmotionConfig, PAD, appraisal_id
from myatri.persona.emotion import EmotionState
from myatri.persona.temporary import event_roots
from myatri.providers import FixtureProvider, Gateway
from myatri.runtime.commit import Committer


BASE = datetime(2026, 10, 20, 0, 0, tzinfo=timezone.utc)


def seed(app, number=0, *, when=BASE, scope="reported", text="约好的电影临时取消了。"):
    raw = Record(record_id=f"raw_emotion_{number}", record_kind="raw_message", created_at=when.isoformat(),
        body_markdown=text, payload={"role": "user"})
    event = Event(fact_summary=text, event_fingerprint=digest([number, text]), reality_scope=scope,
        source_spans=[SourceSpan(message_ref=raw.ref, start=0, end=len(text), quote=text)])
    record = Record(record_id=f"event_emotion_{number}", record_kind="event", source_refs=[raw.ref],
        body_markdown=text, payload=event.model_dump())
    app.store.commit([raw, record], "seed_emotion_" + str(number))
    return raw, record


def response(raw, *, target=None, concern="我想找机会说明自己很期待这次安排。", quote=None):
    return {"decision": "propose", "reason": "原文涉及共同期待的变化，保留暂定理解。",
        "appraisal": {"target": target or {"valence": -0.8, "arousal": 0.7, "dominance": 0.4},
                      "confidence": 0.8, "label": "失落", "meaning": "期待的安排改变，暂时感到失落。", "concern": concern},
        "evidence": [{"message_ref": raw.ref, "quote": quote or raw.body_markdown}]}


async def propose(app, raw, event, **kwargs):
    provider = FixtureProvider([{"content": json.dumps(response(raw, **kwargs), ensure_ascii=False)}])
    proposal = await EmotionAgent(app.store, Gateway(provider)).propose(event.ref)
    return proposal, provider


def test_upstream_half_life_ema_and_distance_contract():
    current, baseline = (-0.8, 0.9, 0.1), (0, 0.3, 0.5)
    assert regress_pad(current, baseline, 3600, 3600) == pytest.approx((-0.4, 0.6, 0.3))
    assert regress_pad(current, baseline, 7200, 3600, 0.5) == pytest.approx((-0.4, 0.6, 0.3))
    assert update_mood(current, baseline, 0.2, 0.5) == pytest.approx((-0.72, 0.84, 0.14))
    assert lerp_pad(current, baseline, 0.5) == pytest.approx((-0.4, 0.6, 0.3))
    assert pad_distance((-1, 0, 0), (1, 1, 1)) == pytest.approx(math.sqrt(6))
    partitioned = regress_pad(regress_pad(current, baseline, 1800, 3600), baseline, 1800, 3600)
    assert partitioned == pytest.approx(regress_pad(current, baseline, 3600, 3600))


@pytest.mark.parametrize("kwargs", [{"valence": float("nan")}, {"arousal": float("inf")},
                                   {"dominance": -0.1}, {"valence": 1.1}])
def test_pad_rejects_nonfinite_and_out_of_range(kwargs):
    with pytest.raises(ValidationError):
        PAD(**kwargs)


@pytest.mark.parametrize("kwargs", [{"emotion_half_life_seconds": 0}, {"inertia": 1.1},
                                   {"mood_alpha": float("nan")}, {"recall_weight": 0.5}])
def test_config_rejects_invalid_dynamics(kwargs):
    with pytest.raises(ValidationError):
        EmotionConfig(**kwargs)


async def test_appraisal_echo_replay_sources_and_persona_separation(tmp_path):
    app = Application(tmp_path)
    raw, event = seed(app)
    before = app.store.snapshot()
    proposal, provider = await propose(app, raw, event)
    Committer(app.store).submit_proposal(proposal)
    records = app.store.list_records("emotion_appraisal")
    assert len(records) == 1 and records[0].record_id == appraisal_id(event.ref)
    assert records[0].payload["observed_at"] == raw.created_at
    echo = app.states.list()[0]
    assert echo.payload["kind_hint"] == "emotional_echo"
    assert event_roots(app.store, echo.source_refs) == [event.ref]
    assert event_roots(app.store, [records[0].ref]) == []
    assert app.persona.read_state().revision == 1
    at = BASE + timedelta(minutes=5)
    state = app.emotions.read(now=at)
    assert state["affect"]["valence"] < state["mood"]["valence"] < 0
    assert state["unique_event_count"] == 1 and state["open_concern_refs"] == [echo.ref]
    old = app.emotions.read(snapshot=before, now=at)
    assert old["unique_event_count"] == 0 and old["affect"] == PAD().model_dump()
    restored = Application(tmp_path).emotions.read(now=at)
    assert restored == state
    assert app.store.verify_archive() == []
    # Re-reading at the same instant and recalling cannot add experiences.
    count = len(app.store.list_records())
    app.emotions.read(now=at)
    app.recall.recall("电影")
    assert len(app.store.list_records()) == count
    assert len(provider.requests) == 1


async def test_decay_does_not_settle_concerns_or_overstate_old_label(tmp_path):
    app = Application(tmp_path)
    raw, event = seed(app)
    proposal, _ = await propose(app, raw, event)
    app.committer.submit_proposal(proposal)
    state = app.emotions.read(now=BASE + timedelta(days=200))
    assert state["affect"] == pytest.approx(PAD().model_dump())
    assert state["open_concern_refs"]
    assert "last_event_meaning" not in app.emotions.context_block(state)
    assert app.states.list()[0].payload["status"] == "open"


async def test_duplicate_appraisal_no_second_call_and_concurrent_publish(tmp_path):
    app = Application(tmp_path)
    raw, event = seed(app)
    first, provider = await propose(app, raw, event)
    second, _ = await propose(app, raw, event, target={"valence": 0.4, "arousal": 0.5, "dominance": 0.6})
    await app._apply({"kind": "proposal", "proposal": first.model_dump(mode="json")})
    await app._apply({"kind": "proposal", "proposal": second.model_dump(mode="json")})
    assert len(app.store.list_records("emotion_appraisal")) == 1
    gateway = Gateway(provider)
    assert await EmotionAgent(app.store, gateway).propose(event.ref) is None
    assert len(provider.requests) == 1


@pytest.mark.parametrize("scope", ["fictional", "quoted"])
async def test_fiction_or_quote_does_not_get_automatic_emotional_impulse(tmp_path, scope):
    app = Application(tmp_path)
    _, event = seed(app, scope=scope)
    provider = FixtureProvider()
    assert await EmotionAgent(app.store, Gateway(provider)).propose(event.ref) is None
    assert not provider.requests


async def test_default_fixture_defers_without_fabricating_state(tmp_path):
    app = Application(tmp_path)
    _, event = seed(app)
    proposal = await EmotionAgent(app.store, app.gateway).propose(event.ref)
    app.committer.submit_proposal(proposal)
    assert proposal.records[0].payload["decision"] == "defer"
    assert not app.store.list_records("emotion_appraisal") and not app.states.list()


async def test_forged_evidence_and_oversized_materials_are_rejected_or_deferred(tmp_path):
    app = Application(tmp_path)
    raw, event = seed(app)
    with pytest.raises(ValueError, match="quote"):
        await propose(app, raw, event, quote="不存在的原话")
    assert not app.store.list_records("emotion_appraisal")
    raw, event = seed(app, 1, text="长原文" * 5000)
    provider = FixtureProvider()
    proposal = await EmotionAgent(app.store, Gateway(provider)).propose(event.ref)
    assert not provider.requests
    assert proposal.records[0].payload["decision"] == "defer"


async def test_archive_rejects_forged_appraisal_identity_and_time(tmp_path):
    app = Application(tmp_path)
    raw, event = seed(app)
    proposal, _ = await propose(app, raw, event, concern="")
    row = next(r for r in proposal.records if r.record_kind == "emotion_appraisal")
    for changed in ({"record_id": "duplicate_impulse"},
                    {"payload": {**row.payload, "observed_at": (BASE + timedelta(days=1)).isoformat()}},
                    {"payload": {**row.payload, "source_spans": [{"message_ref": raw.ref, "start": 0, "end": 1, "quote": "错"}]}}):
        bad = Record(**{**row.model_dump(exclude={"content_hash"}), **changed})
        with pytest.raises(ValueError):
            app.store.commit([proposal.records[0], bad], "bad" + digest(changed))
    assert not app.store.list_records("emotion_appraisal")


async def test_source_receipt_order_beats_worker_completion_order(tmp_path):
    first = Application(tmp_path / "first")
    second = Application(tmp_path / "second")
    for app, order in ((first, [0, 1]), (second, [1, 0])):
        pairs = [seed(app, i, when=BASE + timedelta(minutes=10*i)) for i in range(2)]
        for i in order:
            raw, event = pairs[i]
            proposal, _ = await propose(app, raw, event,
                target={"valence": -0.8 if i == 0 else 0.6, "arousal": 0.7, "dominance": 0.4}, concern="")
            app.committer.submit_proposal(proposal)
    a = first.emotions.read(now=BASE + timedelta(minutes=15))
    b = second.emotions.read(now=BASE + timedelta(minutes=15))
    assert a["affect"] == b["affect"] and a["mood"] == b["mood"]
    assert first.emotions.read(now=BASE - timedelta(seconds=1))["unique_event_count"] == 0
    with pytest.raises(ValueError, match="timezone"):
        first.emotions.read(now=datetime(2026, 10, 20))


async def test_context_budget_state_injection_disabled_mode_and_isolation(tmp_path):
    app = Application(tmp_path)
    raw, event = seed(app, when=datetime.now(timezone.utc))
    proposal, _ = await propose(app, raw, event)
    app.committer.submit_proposal(proposal)
    messages, _ = app.conversation.context.build_context("电影")
    explain = app.conversation.context.explain_context()
    assert "情绪连续性" in messages[1]["content"]
    assert explain["emotion"]["unique_event_count"] == 1
    assert app.conversation.context.budget.fits(messages, [])
    isolated = Application(tmp_path, user_id="another")
    assert isolated.emotions.read()["unique_event_count"] == 0
    disabled = EmotionState(app.store, {"enabled": False})
    assert disabled.context_block(disabled.read()) == ""
    provider = FixtureProvider()
    assert await EmotionAgent(app.store, Gateway(provider), {"enabled": False}).propose(event.ref) is None
    assert not provider.requests


async def test_new_events_enqueue_emotion_and_worker_can_replay_saved_result(tmp_path):
    app = Application(tmp_path)
    raw = app.store.append_message("user", "今天取消电影", message_id="integrated_emotion")
    app.enqueue_message(raw)
    await app.drain()
    jobs = app.queue.list_jobs()
    assert any(j["role"] == "emotion" and j["status"] == "succeeded" for j in jobs)
    assert all(j["status"] == "succeeded" for j in jobs), jobs
    restored = Application(tmp_path)
    restored.recover_pending()
    assert await restored.drain() == 0


def test_schema_is_valid_and_defer_does_not_require_targets():
    import jsonschema
    jsonschema.Draft202012Validator.check_schema(APPRAISAL_SCHEMA)
    jsonschema.validate({"decision": "defer", "reason": "unknown"}, APPRAISAL_SCHEMA)
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate({"decision": "propose", "reason": "missing"}, APPRAISAL_SCHEMA)


async def test_human_retraction_preserves_history_and_retires_echo_atomically(tmp_path):
    app = Application(tmp_path)
    raw, event = seed(app)
    proposal, _ = await propose(app, raw, event)
    app.committer.submit_proposal(proposal)
    prior = app.store.snapshot()
    ref = appraisal_id(event.ref) + "@1"
    correction = app.emotions.propose_retraction(ref, "这次评价误解了上下文，撤回该冲击。")
    app.committer.submit_proposal(correction)
    assert len(app.store.list_records("emotion_appraisal")) == 1
    assert app.emotions.read()["unique_event_count"] == 0
    assert app.emotions.read(snapshot=prior)["unique_event_count"] == 1
    assert app.states.list()[0].payload["status"] == "discarded"
    assert app.emotions.propose_retraction(ref, "重复操作") is None
    assert app.persona.read_state().revision == 1
    assert app.store.verify_archive() == []


async def test_worker_saved_appraisal_result_survives_restart_without_model_replay(tmp_path):
    app = Application(tmp_path)
    raw, event = seed(app)
    proposal, _ = await propose(app, raw, event)
    job_id = app.enqueue_emotion(event.ref)
    leased = app.queue.lease_job("synthetic-worker")
    assert leased["id"] == job_id
    saved = {"kind": "proposal", "proposal": proposal.model_dump(mode="json")}
    app.queue.save_result(job_id, "synthetic-worker", saved)
    app.queue.finish(job_id, "synthetic-worker", status="retry_wait")
    restored = Application(tmp_path)
    await restored.drain()
    assert not restored.gateway.provider.requests
    assert len(restored.store.list_records("emotion_appraisal")) == 1
    assert all(j["status"] == "succeeded" for j in restored.queue.list_jobs())


async def test_later_event_appraisal_receives_prior_interpretation_as_data(tmp_path):
    app = Application(tmp_path)
    raw, event = seed(app)
    proposal, _ = await propose(app, raw, event)
    app.committer.submit_proposal(proposal)
    later_raw, later = seed(app, 1, when=BASE + timedelta(minutes=5), text="因为生病临时取消，很抱歉。")
    _, provider = await propose(app, later_raw, later, concern="")
    prompt = provider.requests[0].messages[0]["content"]
    assert "既有状态" in prompt and appraisal_id(event.ref) in prompt
    assert "不是新增外部证据" in prompt


def test_optional_ranking_preserves_candidates_head_and_counterevidence(tmp_path):
    from types import SimpleNamespace
    from myatri.contracts.emotion import EmotionAppraisal
    app = Application(tmp_path)
    raw, event = seed(app)
    candidates = [SimpleNamespace(ref=f"candidate_{i}@1") for i in range(50)]
    tags = []
    for i, candidate in enumerate(candidates):
        payload = EmotionAppraisal(event_ref=candidate.ref, persona_ref="persona@1", observed_at=BASE.isoformat(),
            target=PAD(valence=(-1 if i % 2 else 1), arousal=0.3, dominance=0.5), confidence=1,
            label="fixture", meaning="合成排序输入", source_spans=[SourceSpan(message_ref=raw.ref, start=0, end=1, quote="约")],
            evidence_refs=[event.ref]).model_dump(mode="json")
        tags.append(SimpleNamespace(ref=f"appraisal_{i}@1", payload=payload))
    class StubStore:
        def list_records(self, kind, **kwargs):
            assert kind == "emotion_appraisal"
            return tags
    service = EmotionState(StubStore(), {"mood_recall": True, "recall_weight": 0.1})
    state = {"appraisal_refs": [tag.ref for tag in tags], "mood": PAD(valence=1).model_dump()}
    output, changed = service.rerank_context(candidates, [candidates[9].ref], state)
    assert changed
    assert output[:4] == candidates[:4] and output[9] == candidates[9]
    assert sorted(r.ref for r in output) == sorted(r.ref for r in candidates)


async def test_provider_failure_keeps_original_data_without_fabricated_emotion(tmp_path):
    app = Application(tmp_path)
    _, event = seed(app)
    class BrokenProvider:
        name = "synthetic-failure"
        async def generate(self, request):
            raise RuntimeError("offline injected failure")
    with pytest.raises(RuntimeError, match="injected"):
        await EmotionAgent(app.store, Gateway(BrokenProvider())).propose(event.ref)
    assert not app.store.list_records("emotion_appraisal")
    assert app.store.get_record(event.record_id).ref == event.ref
    assert app.persona.read_state().revision == 1
