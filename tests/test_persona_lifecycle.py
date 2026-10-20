import asyncio
import json

import pytest

from myatri.cognition.persona_revision import PersonaRevisionAgent, record_counter_search
from myatri.cognition.reflection import ReflectionAgent
from myatri.contracts import BehaviorAttempt, Event, PersonaPatch, Record, SourceSpan, TemporaryEntry, digest, utcnow
from myatri.persona.activation import ActivationSelector
from myatri.persona.patch import PersonaPatcher
from myatri.persona.state import PersonaState
from myatri.persona.temporary import TemporaryStates, event_roots
from myatri.providers import FixtureProvider, Gateway
from myatri.retrieval import RecallService
from myatri.runtime.commit import Committer
from myatri.storage import ArchiveStore


def external(store, record_id, text):
    raw = store.append_message("user", text, f"raw_{record_id}")
    event = Event(fact_summary=text, source_spans=[SourceSpan(message_ref=raw.ref, start=0, end=len(text), quote=text)], event_fingerprint=digest([record_id, text]))
    record = Record(record_id=record_id, record_kind="event", source_refs=[raw.ref], body_markdown=text, payload=event.model_dump(mode="json"))
    store.commit([record], record_id)
    return record


def setup_state(tmp_path):
    store = ArchiveStore(tmp_path)
    persona = PersonaState(store).initialize()
    first = external(store, "cancel", "我临时取消了安排，应该提前告诉你。")
    states = TemporaryStates(store)
    state = states.create(TemporaryEntry(text="对特别期待的散步先说清期待，不过仍不确定", origin_refs=[first.ref], scope="共同安排"), entry_id="expectation")
    return store, persona, first, states, state


def test_activation_expression_unknown_feedback_adjustment_and_discard(tmp_path):
    store, persona, first, states, state = setup_state(tmp_path)
    selected, attention = ActivationSelector(store).select_active_entries("这次散步的期待是什么")
    assert state.ref in attention.selected_refs
    assert states.list()[0].payload["status"] == "open"
    assert store.list_records("behavior_attempt") == []
    assert PersonaState(store).read_state().ref == persona.ref
    with pytest.raises(ValueError, match="persisted assistant"):
        states.record_attempt_feedback(BehaviorAttempt(intent_ref=state.ref, decision_status="expressed", action_refs=["raw_cancel@1"], occurred_at=utcnow()))
    action = store.append_message("assistant", "这次散步我很期待，我们先确认一下吗？", "spoken")
    attempt = states.record_attempt_feedback(BehaviorAttempt(intent_ref=state.ref, decision_status="expressed", action_refs=[action.ref], occurred_at=utcnow(), outcome_unknown=True), attempt_id="attempt")
    assert attempt.payload["outcome_unknown"] is True
    assert attempt.payload["observed_feedback_refs"] == []
    feedback = external(store, "feedback", "提前确认有帮助，不过每次都问会让我有压力。")
    known = states.record_attempt_feedback(BehaviorAttempt(intent_ref=state.ref, decision_status="expressed", action_refs=[action.ref], occurred_at=attempt.payload["occurred_at"], observed_feedback_refs=[feedback.ref], outcome_unknown=False), attempt_id="attempt", base_revision=1)
    assert known.revision == 2
    adjusted = states.review(state.record_id, base_revision=1, text="只在特别期待的散步表达期待", reason="反馈提示频繁确认有压力", evidence_refs=[feedback.ref])
    retired = states.review(state.record_id, base_revision=2, status="discarded", reason="这次暂时放下，不把确认变成义务", evidence_refs=[feedback.ref])
    assert retired.revision == 3
    assert store.get_record(state.record_id, 1).body_markdown == state.body_markdown
    with pytest.raises(ValueError, match="reactivate"):
        states.review(state.record_id, base_revision=3, status="open", reason="旧摘要不能复活")
    reopened = ArchiveStore(tmp_path)
    selected, activation = ActivationSelector(reopened).select_active_entries("散步期待")
    assert selected == []
    assert state.ref not in activation.selected_refs
    assert PersonaState(reopened).read_state().ref == persona.ref
    assert len(event_roots(reopened, [first.ref, feedback.ref])) == 2
    history = RecallService(reopened).recall("期待散步", filters={"include_historical": True}, budget=20000)
    assert {"expectation@1", "expectation@2", "expectation@3", "attempt@2"} <= {record.ref for record in history.records}


def test_generated_ideas_and_repeated_reflections_never_add_external_roots(tmp_path):
    store, persona, original, states, state = setup_state(tmp_path)
    run = Record(record_id="idea_run", record_kind="cognitive_run", payload={"role": "temporary_state"})
    store.commit([run], "idea_run")
    idea = states.create(TemporaryEntry(text="想读一个新的虚构故事", origin_kind="generated_idea", origin_refs=[run.ref]), entry_id="idea")
    assert event_roots(store, [idea.ref]) == []
    assert event_roots(store, [state.ref]) == [original.ref]
    responses = [{"content": json.dumps({"decision": "propose", "reason": "离线结构fixture", "claims": [{"text": "暂定理解，不是新的外部经历", "evidence_refs": [original.ref]}]}, ensure_ascii=False)} for _ in range(10)]
    gateway = Gateway(FixtureProvider(responses))
    async def reflect_ten():
        for _ in range(10):
            proposal = await ReflectionAgent(store, gateway).propose([original.ref])
            Committer(store).submit_proposal(proposal)
    asyncio.run(reflect_ten())
    assert len(store.list_records("reflection")) == 10
    assert [r.ref for r in store.list_records("event")] == [original.ref]
    assert event_roots(store, [r.ref for r in store.list_records("reflection")]) == []
    assert PersonaState(store).read_state().ref == persona.ref
    with pytest.raises(ValueError, match="only atomic"):
        states.review(state.record_id, base_revision=1, status="consolidated", reason="不能由反思次数巩固")


def test_late_feedback_updates_existing_action_without_reactivating_intent(tmp_path):
    store, persona, original, states, state = setup_state(tmp_path)
    action = store.append_message("assistant", "你愿意确认这次散步安排吗？", "late_action")
    initial = states.record_attempt_feedback(BehaviorAttempt(intent_ref=state.ref, decision_status="expressed", action_refs=[action.ref], occurred_at=utcnow()), attempt_id="late_attempt")
    discarded = states.review(state.record_id, base_revision=1, status="discarded", reason="先放下这个念头")
    feedback = external(store, "late_feedback", "刚看到，提前确认其实有帮助。")
    late = states.record_attempt_feedback(BehaviorAttempt(intent_ref=state.ref, decision_status="expressed", action_refs=[action.ref], occurred_at=initial.payload["occurred_at"], observed_feedback_refs=[feedback.ref], outcome_unknown=False), attempt_id=initial.record_id, base_revision=1)
    assert late.revision == 2
    assert late.payload["observed_feedback_refs"] == [feedback.ref]
    assert store.get_record(state.record_id).ref == discarded.ref
    assert store.get_record(state.record_id).payload["status"] == "discarded"
    assert ActivationSelector(store).select_active_entries("散步安排")[0] == []
    with pytest.raises(ValueError):
        states.record_attempt_feedback(BehaviorAttempt(intent_ref=state.ref, decision_status="expressed", action_refs=[action.ref], occurred_at=utcnow()), attempt_id="new_action_after_discard")


def test_exact_a7_bound_local_patch_atomic_consolidation_restore_and_recall(tmp_path):
    store, initial, first, states, state = setup_state(tmp_path)
    second = external(store, "benefit", "这次你提前说清期待很有帮助，我愿意认真协调。")
    counter = external(store, "pressure", "频繁地确认小事让我有压力，不必每次都确认。")
    action = store.append_message("assistant", "这件事我很期待，愿意和我确认安排吗？", "spoken")
    attempt = states.record_attempt_feedback(BehaviorAttempt(intent_ref=state.ref, decision_status="expressed", action_refs=[action.ref], occurred_at=utcnow(), observed_feedback_refs=[second.ref, counter.ref], outcome_unknown=False), attempt_id="attempt")
    bundle = RecallService(store).recall("期待确认安排压力", budget=20000)
    search = record_counter_search(store, "寻找频繁确认造成压力的反例", bundle)
    assert counter.ref in search.payload["searched_refs"]
    patch = PersonaPatch(base_revision=1, entry_id="P03", old_hash=initial.payload["entry_hashes"]["P03"],
                         replacement="只在特别期待的共同安排上更愿意先说清期待，也尊重对方不需要频繁确认。",
                         rationale="两次独立交流与压力反例支持缩小表达范围。", evidence_refs=[first.ref, second.ref], counter_refs=[counter.ref],
                         temporary_refs=[state.ref], attempt_refs=[attempt.ref], counter_search_refs=[search.ref])
    gateway = Gateway(FixtureProvider([{"content": json.dumps({"decision": "accept", "reason": "离线A7接口检查通过，局部范围明确", "scope_ok": True, "counterexamples_checked": True}, ensure_ascii=False)}]))
    proposal, review = asyncio.run(PersonaRevisionAgent(store, gateway).review_and_prepare(patch))
    assert review["decision"] == "accept"
    assert PersonaState(store).read_state().revision == 1
    review_ref = proposal.records[0].payload["review_ref"]
    changed_patch = PersonaPatch(**{**patch.model_dump(), "replacement": "未经A7审查的不同内容"})
    with pytest.raises(ValueError, match="not bound"):
        PersonaPatcher(store).validate_persona_patch(changed_patch, review_ref)
    Committer(store).submit_proposal(proposal)
    updated = PersonaState(store).read_state()
    assert updated.revision == 2
    assert PersonaState(store).diff(1, 2).keys() == {"P03"}
    assert updated.payload["entry_hashes"]["P01"] == initial.payload["entry_hashes"]["P01"]
    assert updated.payload["entry_hashes"]["P02"] == initial.payload["entry_hashes"]["P02"]
    consolidated = store.get_record(state.record_id)
    assert consolidated.payload["status"] == "consolidated"
    assert store.get_record(consolidated.payload["persona_change_ref"].split("@")[0]).record_kind == "persona_change"
    with pytest.raises(ValueError, match="stale persona"):
        PersonaPatcher(store).propose(patch, review_ref)
    change = store.get_record(updated.payload["change_ref"].split("@")[0])
    remembered = RecallService(store).recall("独立交流压力反例", filters={"kinds": ["persona_change"]}, budget=20000)
    assert {change.ref, "raw_cancel@1", "raw_benefit@1", "raw_pressure@1"} <= {record.ref for record in remembered.records}
    restored = PersonaPatcher(store).restore(1)
    assert restored.revision == 3
    assert restored.payload["entries"] == initial.payload["entries"]
    assert store.get_record("persona", 2).payload["entries"]["P03"] == patch.replacement
    assert ArchiveStore(tmp_path).get_record(state.record_id).payload["status"] == "consolidated"
