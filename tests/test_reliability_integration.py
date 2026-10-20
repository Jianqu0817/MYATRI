import asyncio
from datetime import datetime, timedelta, timezone
import json

import pytest

from myatri.app import Application
from myatri.contracts import JobSpec, Record, TemporaryEntry, ModelResponse, BehaviorAttempt, Event, SourceSpan
from myatri.persona.temporary import TemporaryStates, event_roots
from myatri.runtime.jobs import JobQueue
from myatri.runtime.scheduler import Scheduler
from myatri.providers import FixtureProvider, BudgetExceeded
from myatri.runtime.worker import Worker
from myatri.cognition.attribution import AttributionAgent
from myatri.runtime.commit import Committer


def seed_intent(app):
    run = Record(record_id="idea", record_kind="cognitive_run")
    app.store.commit([run], "seed-idea")
    return app.states.create(TemporaryEntry(text="安排有变化时先问清对方的期待", origin_kind="generated_idea",
                                           origin_refs=[run.ref]), entry_id="intent")


def test_state_boundaries_and_aware_dates(tmp_path):
    app = Application(tmp_path)
    state = seed_intent(app)
    with pytest.raises(ValueError, match="timezone"):
        TemporaryEntry(text="test", origin_refs=["idea@1"], origin_kind="generated_idea", review_at="2026-10-20")
    entry = TemporaryEntry(text="test", origin_refs=["idea@1"], origin_kind="generated_idea",
                           review_at="2026-10-20T10:00:00+08:00")
    assert entry.review_at == "2026-10-20T02:00:00+00:00"
    with pytest.raises(ValueError, match="atomic"):
        app.states.create(TemporaryEntry(text="bad", origin_kind="generated_idea", origin_refs=["idea@1"],
                                          status="consolidated", persona_change_ref="missing@1"))
    closed = app.states.review(state.record_id, base_revision=1, status="discarded", reason="不继续")
    with pytest.raises(ValueError, match="retired"):
        app.states.review(closed.record_id, base_revision=2, status="settled", reason="绕行不能复活")


def test_due_review_new_evidence_and_idle_edge(tmp_path):
    queue = JobQueue(tmp_path / "runtime.sqlite3")
    scheduler = Scheduler(queue)
    now = datetime(2026, 10, 20, 8, tzinfo=timezone.utc)
    activity = now - timedelta(hours=2)
    assert len(scheduler.tick(now=now, dirty_refs=["e1@1"], review_refs=["s1@1"], last_activity=activity)) == 2
    first_meta = queue.get_meta("last_scheduled")
    assert scheduler.tick(now=now + timedelta(seconds=1), dirty_refs=["e1@1"], review_refs=["s1@1"], last_activity=activity) == []
    assert queue.get_meta("last_scheduled") == first_meta
    scheduler.tick(now=now + timedelta(seconds=2), dirty_refs=["e1@1", "e2@1"], review_refs=["s1@1"], last_activity=activity)
    reviews = [j for j in queue.list_jobs() if j["role"] == "temporary_review"]
    assert len(reviews) == 2
    assert "e2@1" in json.loads(reviews[-1]["payload"])["input_refs"]


async def test_bad_legacy_timestamp_isolated_while_background_runs(tmp_path):
    app = Application(tmp_path)
    state = seed_intent(app)
    # Simulate a valid old archive written before strict field validation.
    old = Record(**{**state.model_dump(exclude={"content_hash"}), "revision": 2, "supersedes_revision": 1,
                    "payload": {**state.payload, "review_at": "not a date"}, "source_refs": [state.ref]})
    app.store.commit([old], "legacy-invalid", expected={state.record_id: 1})
    task = asyncio.create_task(app.run_background())
    try:
        for _ in range(30):
            await asyncio.sleep(.02)
            if app.queue.get_meta("scheduler_issues"):
                break
        assert not task.done()
        assert app.queue.get_meta("scheduler_issues")[0]["ref"] == "intent@2"
    finally:
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task


class AttributionFixture(FixtureProvider):
    async def generate(self, request):
        if request.role == "foreground":
            self.requests.append(request)
            return ModelResponse(content="安排变了，你希望怎么调整？", provider="fixture", model="audit")
        if request.role != "attribution":
            return await super().generate(request)
        self.requests.append(request)
        material = json.loads(request.messages[-1]["content"])
        by_kind = {}
        for row in material:
            by_kind.setdefault(row["kind"], []).append(row)
        value = {"decision": "propose", "reason": "合成的明确表达与反馈", "expressions": [], "feedback": []}
        if "raw_message" in by_kind and "temporary_state" in by_kind:
            value["expressions"] = [{"intent_ref": by_kind["temporary_state"][0]["ref"],
                "action_ref": by_kind["raw_message"][0]["ref"], "quote": "你希望怎么调整"}]
        if "behavior_attempt" in by_kind and "event" in by_kind:
            value["feedback"] = [{"attempt_ref": by_kind["behavior_attempt"][0]["ref"],
                "event_ref": by_kind["event"][0]["ref"], "quote": by_kind["event"][0]["payload"]["source_spans"][0]["quote"]}]
        return ModelResponse(content=json.dumps(value, ensure_ascii=False), provider="fixture", model="attribution-audit")


async def test_daily_chat_expression_feedback_restart_and_no_fake_growth(tmp_path):
    provider = AttributionFixture()
    app = Application(tmp_path, provider=provider)
    seed_intent(app)
    answer = await app.conversation.respond("今天安排变化了", message_id="first")
    await app.drain()
    attempts = app.store.list_records("behavior_attempt")
    assert len(attempts) == 1
    first = attempts[0]
    assert first.payload["decision_status"] == "expressed"
    assert first.payload["action_refs"] == [answer.ref]
    assert first.payload["outcome_unknown"] is True
    assert event_roots(app.store, [first.ref]) == []  # A generated idea and its expression are not external evidence.
    app.states.review("intent", base_revision=1, status="discarded", reason="先放下，但保留迟到反馈")
    await app.conversation.respond("你先问我的期待很有帮助", message_id="later")
    await app.drain()
    attempt = app.store.get_record(first.record_id)
    assert attempt.revision == 2
    assert attempt.payload["observed_feedback_refs"]
    assert attempt.payload["outcome_unknown"] is False
    assert app.store.get_record("intent").payload["status"] == "discarded"
    assert app.persona.read_state().revision == 1
    restored = Application(tmp_path, provider=AttributionFixture())
    restored.recover_pending()
    await restored.drain()
    assert restored.store.get_record(first.record_id).revision == 2
    assert len(restored.store.list_records("behavior_attempt")) == 1
    assert restored.store.verify_archive() == []
    assert not [j for j in restored.queue.list_jobs() if j["status"] != "succeeded"]


async def test_material_size_error_not_hourly_retried(tmp_path):
    queue = JobQueue(tmp_path / "jobs.sqlite3")
    queue.enqueue(JobSpec(role="oversize"))
    async def handler(spec):
        raise BudgetExceeded("too large", reason="request_size")
    await Worker(queue, {"oversize": handler}).run_once()
    assert queue.list_jobs()[0]["status"] == "failed"
    assert "material planning" in queue.list_jobs()[0]["error"]


async def test_pending_ingest_checkpoint_immediately_continues(tmp_path):
    queue = JobQueue(tmp_path / "jobs.sqlite3")
    queue.enqueue(JobSpec(role="ingest"))
    calls = []
    async def handler(spec):
        calls.append(True)
        if len(calls) == 1:
            raise BudgetExceeded("saved next cursor", reason="ingest_pending")
        return {"kind": "noop"}
    worker = Worker(queue, {"ingest": handler})
    await worker.run_once()
    await worker.run_once()
    assert len(calls) == 2 and queue.list_jobs()[0]["status"] == "succeeded"


async def test_ninth_pending_theme_is_enqueued(tmp_path):
    app = Application(tmp_path)
    app.index.themes = {f"t{i}": {"members": [], "material_hash": str(i), "needs_summary": i == 8} for i in range(9)}
    result = await app._cycle(JobSpec(role="cycle"))
    themes = [j for j in result["jobs"] if j["role"] == "theme"]
    assert len(themes) == 1 and themes[0]["payload"]["theme_id"] == "t8"


async def test_attribution_rejects_invented_quote_and_future_intent(tmp_path):
    app = Application(tmp_path)
    state = seed_intent(app)
    answer = await app.conversation.respond("安排有变化", message_id="turn")
    invalid = {"decision": "propose", "reason": "bad", "expressions": [
        {"intent_ref": state.ref, "action_ref": answer.ref, "quote": "这句话并不存在"}], "feedback": []}
    from myatri.providers import Gateway
    gateway = Gateway(FixtureProvider([{"content": json.dumps(invalid, ensure_ascii=False)}]))
    with pytest.raises(ValueError, match="exact assistant"):
        await AttributionAgent(app.store, gateway).propose([state.ref, answer.ref])
    # A later thought cannot be retroactively assigned to an earlier answer.
    newer = app.states.create(TemporaryEntry(text="后来的想法", origin_kind="generated_idea", origin_refs=["idea@1"]), entry_id="future")
    invalid["expressions"][0].update(intent_ref=newer.ref, quote="离线演示")
    gateway = Gateway(FixtureProvider([{"content": json.dumps(invalid, ensure_ascii=False)}]))
    with pytest.raises((ValueError, KeyError)):
        await AttributionAgent(app.store, gateway).propose([newer.ref, answer.ref])
    assert app.store.list_records("behavior_attempt") == []


async def test_expression_result_replay_after_state_closed_remains_historical(tmp_path):
    app = Application(tmp_path, provider=AttributionFixture())
    state = seed_intent(app)
    answer = await app.conversation.respond("安排变了", message_id="turn")
    proposal = await AttributionAgent(app.store, app.gateway).propose([state.ref, answer.ref])
    app.states.review("intent", base_revision=1, status="discarded", reason="生成结果已保存，提交之前决定放下")
    # The original context proves the earlier expression even though it is now
    # retired. Recording that history must never reopen the intention.
    Committer(app.store).submit_proposal(proposal)
    Committer(app.store).submit_proposal(proposal)
    assert len(app.store.list_records("behavior_attempt")) == 1
    assert app.store.get_record("intent").payload["status"] == "discarded"
    assert app.persona.read_state().revision == 1


async def test_feedback_plans_ignored_and_many_attempts_batched_with_event(tmp_path):
    app = Application(tmp_path)
    state = seed_intent(app)
    app.states.record_attempt_feedback(BehaviorAttempt(intent_ref=state.ref, decision_status="planned"), attempt_id="plan")
    answer = await app.conversation.respond("安排变了", message_id="first")
    attempts = []
    for index in range(17):
        attempts.append(app.states.record_attempt_feedback(BehaviorAttempt(intent_ref=state.ref, decision_status="expressed",
            action_refs=[answer.ref], occurred_at=answer.created_at), attempt_id=f"existing_{index}"))
    raw = app.store.append_message("user", "我觉得先问清期待是有帮助的", "feedback_raw")
    event = Event(fact_summary=raw.body_markdown, event_fingerprint="feedback", source_spans=[
        SourceSpan(message_ref=raw.ref, start=0, end=len(raw.body_markdown), quote=raw.body_markdown)])
    record = Record(record_id="feedback_event", record_kind="event", source_refs=[raw.ref],
                    body_markdown=raw.body_markdown, payload=event.model_dump())
    app.store.commit([record], "feedback_event")
    app.enqueue_feedback([record.ref])
    specs = [JobSpec.model_validate_json(job["payload"]) for job in app.queue.list_jobs() if job["role"] == "attribution" and record.ref in json.loads(job["payload"])["input_refs"]]
    assert len(specs) == 5
    assert set(ref for spec in specs for ref in spec.input_refs if ref != record.ref) == {r.ref for r in attempts}
    assert all(len(spec.input_refs) <= 5 and "plan@1" not in spec.input_refs for spec in specs)
    # Even a direct overfull API request must show the required event first.
    provider = FixtureProvider()
    from myatri.providers import Gateway
    proposal = await AttributionAgent(app.store, Gateway(provider)).propose([record.ref, *[r.ref for r in attempts]])
    shown = json.loads(provider.requests[0].messages[-1]["content"])
    assert shown[0]["kind"] == "event"
    assert proposal.records[0].payload["omitted_count"] > 0


async def test_duplicate_expression_rows_are_idempotent_inside_proposal(tmp_path):
    app = Application(tmp_path)
    state = seed_intent(app)
    answer = await app.conversation.respond("安排变了", message_id="turn")
    expression = {"intent_ref": state.ref, "action_ref": answer.ref, "quote": "离线演示"}
    output = {"decision": "propose", "reason": "重复输出", "expressions": [expression, expression], "feedback": []}
    from myatri.providers import Gateway
    proposal = await AttributionAgent(app.store, Gateway(FixtureProvider([{"content": json.dumps(output, ensure_ascii=False)}]))).propose([state.ref, answer.ref])
    Committer(app.store).submit_proposal(proposal)
    assert len(app.store.list_records("behavior_attempt")) == 1


async def test_concurrent_late_feedback_is_unioned_without_model_regeneration(tmp_path):
    app = Application(tmp_path, provider=AttributionFixture())
    seed_intent(app)
    await app.conversation.respond("安排变了", message_id="turn")
    await app.drain()
    original = app.store.list_records("behavior_attempt")[0]
    feedback = []
    for index in range(2):
        raw = app.store.append_message("user", f"反馈{index}：有时需要先确认", f"feedback{index}")
        event = Event(fact_summary=raw.body_markdown, event_fingerprint=f"f{index}", source_spans=[
            SourceSpan(message_ref=raw.ref, start=0, end=len(raw.body_markdown), quote=raw.body_markdown)])
        record = Record(record_id=f"event_feedback{index}", record_kind="event", source_refs=[raw.ref],
                        body_markdown=raw.body_markdown, payload=event.model_dump())
        app.store.commit([record], record.record_id)
        feedback.append(record)
    saved = await AttributionAgent(app.store, app.gateway).propose([original.ref, feedback[0].ref])
    # Another worker adds different, independently observed feedback before the
    # saved result publishes. Rebase must retain both without a second API call.
    concurrent = BehaviorAttempt.model_validate({**original.payload, "observed_feedback_refs": [feedback[1].ref], "outcome_unknown": False})
    app.states.record_attempt_feedback(concurrent, attempt_id=original.record_id, base_revision=1)
    calls = len(app.gateway.provider.requests)
    app._submit_attribution(saved)
    app._submit_attribution(saved)
    current = app.store.get_record(original.record_id)
    assert current.revision == 3
    assert set(current.payload["observed_feedback_refs"]) == {r.ref for r in feedback}
    assert len(app.gateway.provider.requests) == calls
    assert app.store.verify_archive() == []
