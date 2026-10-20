import pytest

from myatri.contracts import TemporaryEntry
from myatri.conversation.budget import TokenBudget
from myatri.conversation.compaction import Compactor
from myatri.conversation.context import ContextBuilder, RUNNING_RULES
from myatri.persona.activation import ActivationSelector
from myatri.persona.state import PersonaState
from myatri.persona.temporary import TemporaryStates
from myatri.providers import BudgetExceeded
from myatri.providers.gateway import ProviderError
from myatri.retrieval import RecallService
from myatri.storage import ArchiveStore

from test_persona_lifecycle import setup_state


def test_compaction_restart_preserves_sources_but_never_revives_discarded_state(tmp_path):
    store, persona, event, states, state = setup_state(tmp_path)
    important = store.append_message("user", "我答应周末先说明安排。" + "这是必须可恢复的完整原文。" * 30, "important")
    other = store.append_message("user", "一般聊天内容。" * 50, "other")
    summary = Compactor(store).compact(preserve_ids=[important.record_id])
    assert next(row for row in summary.payload["excerpts"] if row["ref"] == important.ref)["text"] == important.body_markdown
    assert next(row for row in summary.payload["excerpts"] if row["ref"] == other.ref)["truncated"]
    assert Compactor(store).current().ref == summary.ref
    states.review(state.record_id, base_revision=1, status="discarded", reason="不继续确认这件事", evidence_refs=[event.ref])
    assert Compactor(store).current() is None
    reopened = ArchiveStore(tmp_path)
    fresh = Compactor(reopened).compact(preserve_ids=[important.ref])
    assert state.ref not in fresh.payload["state_refs"]
    assert reopened.get_record(important.record_id).body_markdown == important.body_markdown
    builder = ContextBuilder(reopened, RecallService(reopened))
    messages, snapshot = builder.build_context("散步期待")
    explanation = builder.explain_context()
    assert state.ref not in explanation["active_state_refs"]
    assert explanation["summary_ref"] == fresh.ref
    assert explanation["persona_ref"] == persona.ref
    assert RUNNING_RULES in messages[0]["content"]
    assert "当前暂定状态，可采用、调整、暂缓或不采用" in messages[1]["content"]
    assert "expectation@1" not in messages[1]["content"]
    assert RecallService(reopened).read_record(important.ref).body_markdown == important.body_markdown


def test_automatic_compaction_has_recoverable_source_pointers(tmp_path):
    store = ArchiveStore(tmp_path)
    PersonaState(store).initialize()
    for index in range(20):
        store.append_message("user" if index % 2 == 0 else "assistant", f"第{index}轮，" + "普通对话内容持续保存。" * 14, f"turn_{index}")
    builder = ContextBuilder(store, RecallService(store), budget=TokenBudget(limit=11000, output_reserve=512, safety=512))
    messages, snapshot = builder.build_context("别的话题")
    explanation = builder.explain_context()
    assert explanation["summary_ref"] is not None
    assert len(explanation["history_refs"]) <= 6
    assert len(store.list_records("raw_message")) == 20
    assert "第0轮" in RecallService(store).read_record("turn_0@1").body_markdown
    assert RUNNING_RULES in messages[0]["content"]
    assert builder.budget.fits(messages)


def test_fixed_context_overflow_is_explicit_and_does_not_drop_rules(tmp_path):
    store = ArchiveStore(tmp_path)
    PersonaState(store).initialize({"P01": "不能截断的角色基础。" * 400})
    builder = ContextBuilder(store, RecallService(store), budget=TokenBudget(limit=1500, output_reserve=256, safety=128))
    with pytest.raises(BudgetExceeded):
        builder.build_context("你好")
    assert store.list_records("raw_message") == []
    assert store.get_record("persona").body_markdown.count("不能截断") == 400


def test_unfinished_tool_protocol_cannot_be_compacted(tmp_path):
    store = ArchiveStore(tmp_path)
    PersonaState(store).initialize()
    store.append_message("user", "检索一下散步", "raw")
    incomplete = [{"role": "user", "content": "检索"}, {"role": "assistant", "content": "", "tool_calls": [{"id": "call_1", "type": "function", "function": {"name": "recall", "arguments": '{"query":"散步"}'}}]}]
    with pytest.raises(ProviderError, match="unfinished"):
        Compactor(store).compact(protocol_messages=incomplete)
    assert store.list_records("summary") == []


def test_sync_existing_summary_compacts_again_after_history_growth(tmp_path):
    store = ArchiveStore(tmp_path)
    PersonaState(store).initialize()
    builder = ContextBuilder(store, RecallService(store), budget=TokenBudget(limit=11000, output_reserve=512, safety=512))
    summaries = []
    for cycle in range(3):
        for index in range(cycle * 20, (cycle + 1) * 20):
            store.append_message("user" if index % 2 else "assistant", "普通话题。" * 40, f"growth_{index}")
        messages, _ = builder.build_context("另外的话题")
        assert builder.budget.fits(messages)
        summaries.append(builder.explain_context()["summary_ref"])
    assert len(set(summaries)) == 3


def test_no_progress_compaction_stops_without_recursion_or_repeated_publication(tmp_path):
    store = ArchiveStore(tmp_path)
    PersonaState(store).initialize({"P01": "无法截断的角色设定。" * 200})
    for index in range(10):
        store.append_message("user", "对话正文" * 30, f"overflow_{index}")
    builder = ContextBuilder(store, RecallService(store), budget=TokenBudget(limit=2000, output_reserve=256, safety=128))
    with pytest.raises(BudgetExceeded):
        builder.build_context("你好")
    assert len(store.list_records("summary")) <= 2
    assert any("no raw coverage progress" in row for row in builder.explain_context()["limitations"])


def test_conflicting_tentative_states_can_coexist_without_persona_mutation(tmp_path):
    store, persona, event, states, first = setup_state(tmp_path)
    second = states.create(TemporaryEntry(text="这次散步期待先不表达，想继续观察", origin_refs=[event.ref], scope="共同安排"), entry_id="opposite")
    selected, activation = ActivationSelector(store).select_active_entries("这次散步期待", budget=1000)
    assert {first.ref, second.ref} <= set(activation.selected_refs)
    assert {record.payload["status"] for record in states.list()} == {"open"}
    assert store.get_record("persona").ref == persona.ref
