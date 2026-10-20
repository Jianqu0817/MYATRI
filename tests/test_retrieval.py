import asyncio
import json
from pathlib import Path

import pytest

from myatri.contracts import Edge, Event, Record, SourceSpan, digest
from myatri.memory import MemoryIndex
from myatri.retrieval import RecallService
from myatri.storage import ArchiveStore


def populated(tmp_path):
    store = ArchiveStore(tmp_path)
    fixture = json.loads((Path(__file__).parent / "scenarios/recall/reversal.json").read_text(encoding="utf-8"))
    for row in fixture["events"]:
        raw = store.append_message("user", row["text"], f"raw_{row['id']}")
        payload = Event(occurred_at=f"{row['date']}T08:00:00+00:00", time_precision="day", participants=[row["person"]], fact_summary=row["text"],
                        source_spans=[SourceSpan(message_ref=raw.ref, start=0, end=len(row["text"]), quote=row["text"])], event_fingerprint=digest(row))
        store.commit([Record(record_id=row["id"], record_kind="event", source_refs=[raw.ref], body_markdown=row["text"], payload=payload.model_dump(mode="json"))], row["id"])
    edge = Edge(edge_id="renew_counter", from_ref="cancel@1", to_ref="renew@1", type="contradicts", evidence_refs=["cancel@1", "renew@1"])
    store.commit([Record(record_id="edge_counter", record_kind="edge", source_refs=edge.evidence_refs, payload=edge.model_dump(mode="json"))], "edge")
    index = MemoryIndex(store)
    asyncio.run(index.rebuild())
    return store, index, fixture


def test_chinese_time_person_source_and_negation_reversal(tmp_path):
    store, index, fixture = populated(tmp_path)
    recall = RecallService(store, index)
    dated = recall.recall(fixture["queries"][0]["query"], budget=12000)
    refs = {r.ref for r in dated.records}
    assert set(fixture["queries"][0]["required"]).issubset(refs)
    assert not set(fixture["queries"][0]["excluded"]) & refs
    assert ["cancel@1", "raw_cancel@1"] in dated.paths
    raw = next(record for record in dated.records if record.ref == "raw_cancel@1")
    event = next(record for record in dated.records if record.ref == "cancel@1")
    span = event.payload["source_spans"][0]
    assert raw.body_markdown[span["start"]:span["end"]] == span["quote"]
    reversal = recall.recall(fixture["queries"][1]["query"], budget=12000)
    assert {"cancel@1", "renew@1"}.issubset(reversal.counter_refs)
    assert any("Chinese trigram FTS" in reason for reasons in reversal.reasons.values() for reason in reasons)
    assert "不代表不想见面" in next(r.body_markdown for r in reversal.records if r.ref == "raw_renew@1")


def test_index_lag_snapshot_and_archive_fallback(tmp_path):
    store, index, _ = populated(tmp_path)
    old = store.snapshot()
    fresh = store.append_message("user", "全新的火星基地计划", "mars")
    service = RecallService(store, index)
    current = service.recall("火星基地", budget=6000)
    assert fresh.ref in {r.ref for r in current.records}
    assert any("水位" in message for message in current.limitations)
    historical = service.recall("火星基地", snapshot=old, budget=6000)
    assert fresh.ref not in {r.ref for r in historical.records}
    assert historical.snapshot == old
    no_index = RecallService(store).recall("火星基地", budget=6000)
    assert fresh.ref in {r.ref for r in no_index.records}
    assert any("未建立" in message for message in no_index.limitations)


def test_isolation_budget_and_short_chinese_query(tmp_path):
    store, index, _ = populated(tmp_path)
    private = ArchiveStore(tmp_path, user_id="private")
    private.append_message("user", "绝密火星基地", "secret")
    public = RecallService(store, index).recall("绝密火星基地", budget=12000)
    assert "secret@1" not in {r.ref for r in public.records}
    own = RecallService(private).recall("绝密", budget=1000)
    assert "secret@1" in {r.ref for r in own.records}
    tiny = RecallService(store, index).recall("海边散步", budget=1)
    assert tiny.records == []
    assert any("预算" in message for message in tiny.limitations)


def test_historical_thought_retraction_and_feedback(tmp_path):
    store = ArchiveStore(tmp_path)
    raw = store.append_message("user", "周末散步先不谈了", "raw")
    first = Record(record_id="thought", record_kind="temporary_state", source_refs=[raw.ref], body_markdown="想继续约周末散步", payload={"text": "想继续约周末散步", "status": "open"})
    store.commit([first], "thought")
    discarded = Record(record_id="thought", revision=2, supersedes_revision=1, record_kind="temporary_state", source_refs=[raw.ref], body_markdown="散步念头撤回，对方明确不想谈", payload={"text": "散步念头撤回", "status": "discarded", "reason": "对方明确不想谈"})
    feedback = Record(record_id="feedback", record_kind="behavior_attempt", source_refs=[raw.ref, first.ref], body_markdown="只提出散步草稿，没有实际发送或实践", payload={"decision_status": "draft", "outcome_unknown": True})
    store.commit([discarded, feedback], "discard_feedback", expected={"thought": 1})
    service = RecallService(store)
    current = service.recall("散步", budget=10000)
    assert "thought@2" not in {r.ref for r in current.records}
    history = service.recall("散步", filters={"include_historical": True}, budget=10000)
    assert {"thought@1", "thought@2", "feedback@1"}.issubset({r.ref for r in history.records})
    assert any("historical revision" in reason for reason in history.reasons["thought@1"])
    assert any("discarded" in reason for reason in history.reasons["thought@2"])
    assert service.read_record("thought@1").body_markdown == first.body_markdown


def test_unknown_event_date_is_not_archive_creation_date(tmp_path):
    store = ArchiveStore(tmp_path)
    raw = store.append_message("user", "某天我们去海边散步，具体日期不记得", "undated_raw")
    event = Event(fact_summary="日期不详的海边散步", source_spans=[SourceSpan(message_ref=raw.ref, start=0, end=len(raw.body_markdown), quote=raw.body_markdown)], event_fingerprint="undated")
    store.commit([Record(record_id="undated", record_kind="event", source_refs=[raw.ref], body_markdown="日期不详的海边散步", payload=event.model_dump(mode="json"))], "undated")
    recall = RecallService(store).recall("海边散步", filters={"kinds": ["event"], "date_from": raw.created_at[:10], "date_to": raw.created_at[:10]})
    assert recall.records == []


def test_absent_filters_do_not_recall_unrelated_logs_or_persona(tmp_path):
    store = ArchiveStore(tmp_path)
    store.commit([Record(record_id="persona", record_kind="persona_version", body_markdown="电影只是人格模板关键词"),
                  Record(record_id="audit_run", record_kind="cognitive_run", body_markdown="电影只是运行审计关键词")], "internal")
    movie = store.append_message("user", "今天约好一起看电影", "movie")
    store.append_message("user", "完全不相关的珊瑚潜泳", "unrelated")
    recall = RecallService(store).recall("电影", filters={"date_from": None, "date_to": None, "person": None, "participants": []})
    assert {record.ref for record in recall.records} == {movie.ref}
    assert all("explicit time/person filter" not in reasons for reasons in recall.reasons.values())
    explicit = RecallService(store).recall("电影", filters={"kinds": ["cognitive_run"]})
    assert {record.ref for record in explicit.records} == {"audit_run@1"}


def test_persona_change_survives_large_transitive_run_source_graph(tmp_path):
    store, index, _ = populated(tmp_path)
    long_sources = [store.append_message("user", f"历史无关原文{number}：" + "很长的背景材料" * 1000, f"long_{number}") for number in range(6)]
    run = Record(record_id="huge_review", record_kind="cognitive_run", source_refs=["cancel@1", *[r.ref for r in long_sources]], payload={"role": "reviewer", "review": {"decision": "accept"}})
    change = Record(record_id="bounded_change", record_kind="persona_change", source_refs=["cancel@1", run.ref],
                    body_markdown="共同安排变化后，我更愿意在特别期待时先说清期待。", payload={"event_roots": ["cancel@1"], "diff": {"P03": {"before": "先迁就", "after": "有范围地表达期待"}}})
    store.commit([run, change], "large_provenance")
    result = RecallService(store, index).recall("共同安排变化", filters={"kinds": ["persona_change"]}, budget=1800)
    refs = {record.ref for record in result.records}
    assert {change.ref, "cancel@1", "raw_cancel@1"} <= refs
    assert not {record.ref for record in long_sources} & refs
    assert any("未展开" in limitation and run.ref in limitation and "read_record" in limitation for limitation in result.limitations)
    assert RecallService(store).read_record(run.ref).source_refs == run.source_refs


def test_persona_change_edited_wording_is_recalled_even_when_rationale_uses_other_words(tmp_path):
    store, index, _ = populated(tmp_path)
    change = Record(record_id="wording_change", record_kind="persona_change", source_refs=["cancel@1"],
                    body_markdown="失落与沟通反馈支持缩小范围后的调整，保留反例。", payload={"event_roots": ["cancel@1"],
                        "patch": {"entry_id": "P03", "replacement": "仍愿意体谅对方，但共同安排中更愿意表达期待。", "scope": "共同安排"},
                        "diff": {"P03": {"before": "通常先迁就", "after": "共同安排中更愿意表达期待"}}})
    store.commit([change], "structured_wording")
    asyncio.run(index.update())
    service = RecallService(store, index)
    for filters in ({"kinds": ["persona_change"]}, {"kinds": ["persona_change", "event"]}):
        bundle = service.recall("表达期待", filters=filters, budget=5000)
        assert change.ref in {record.ref for record in bundle.records}
    why = service.recall("为什么更愿意表达期待", budget=5000)
    assert why.records[0].ref == change.ref
    assert "persona change history" in why.reasons[change.ref]
    assert index.query("更愿意表达期待")[0]["ref"] == change.ref


@pytest.mark.parametrize("date", ["2026-13-40", "2026-02-30", "0000年1月1日"])
def test_invalid_date_in_query_remains_searchable_prose(tmp_path, date):
    store = ArchiveStore(tmp_path)
    message = store.append_message("user", f"原始记录写着{date}，日期需要核对", "raw")
    result = RecallService(store).recall(f"{date}，日期需要核对")
    assert message.ref in {row.ref for row in result.records}
    assert any("无效日历日期" in limitation for limitation in result.limitations)


@pytest.mark.asyncio
async def test_invalid_date_does_not_abort_foreground_or_next_turn(tmp_path):
    from myatri.app import Application
    app = Application(tmp_path, mode="offline")
    first = await app.conversation.respond("我想查询2026-13-40那天的事情", message_id="invalid_date")
    assert first.payload["role"] == "assistant"
    assert app.store.get_record("invalid_date").body_markdown == "我想查询2026-13-40那天的事情"
    following = await app.conversation.respond("接着聊聊别的事情", message_id="following")
    assert following.payload["role"] == "assistant"
