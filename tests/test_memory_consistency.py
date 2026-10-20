"""Default-collected regressions for the previously failing memory audits.

The concurrency wrapper only controls scheduling; TF-IDF/Leiden still execute.
"""
import asyncio
import json
import threading

import pytest

from myatri.contracts import Edge, EmbeddingBatch, Event, Record, SourceSpan, TemporaryEntry, digest
from myatri.memory import LocalTfidfEmbeddingProvider, MemoryIndex
from myatri.retrieval import RecallService
from myatri.storage import ArchiveStore

OBSERVATIONS = {}


def external(store, name, text):
    raw = store.append_message("user", text, f"raw_{name}")
    event = Event(fact_summary=text, source_spans=[SourceSpan(message_ref=raw.ref, start=0, end=len(text), quote=text)], event_fingerprint=digest([name, text]))
    record = Record(record_id=name, record_kind="event", source_refs=[raw.ref], body_markdown=text, payload=event.model_dump(mode="json"))
    store.commit([record], name)
    return record


def test_historical_snapshot_must_not_use_future_semantic_edges(tmp_path):
    store = ArchiveStore(tmp_path)
    left = external(store, "a", "珊瑚海底潜泳")
    right = external(store, "b", "程序编译故障")
    past = store.snapshot()
    edge = Edge(edge_id="future_relation", from_ref=left.ref, to_ref=right.ref, type="contradicts", evidence_refs=[left.ref, right.ref])
    store.commit([Record(record_id=edge.edge_id, record_kind="edge", source_refs=edge.evidence_refs, payload=edge.model_dump(mode="json"))], "future_relation")
    index = MemoryIndex(store)
    asyncio.run(index.rebuild())
    bundle = RecallService(store, index).recall("珊瑚潜泳", snapshot=past, filters={"kinds": ["event"]}, budget=5000)
    assert store.list_records("edge", snapshot=past) == []
    OBSERVATIONS["historical_graph"] = {"requested_snapshot": past, "index_watermark": index.watermark,
                                        "edges_in_requested_snapshot": 0, "actual_counter_refs": bundle.counter_refs,
                                        "without_index_counter_refs": RecallService(store).recall("珊瑚潜泳", snapshot=past, filters={"kinds": ["event"]}, budget=5000).counter_refs,
                                        "actual_record_refs": [r.ref for r in bundle.records], "limitations": bundle.limitations}
    assert not bundle.counter_refs, {"counter_refs": bundle.counter_refs, "reasons": bundle.reasons, "snapshot": past}


@pytest.mark.parametrize("shared_instance", [False, True])
def test_slow_older_rebuild_must_not_regress_current_watermark(tmp_path, monkeypatch, shared_instance):
    store = ArchiveStore(tmp_path)
    store.append_message("user", "最早的共同安排", "first")
    original = LocalTfidfEmbeddingProvider.embed

    async def exercise():
        paused, release = asyncio.Event(), asyncio.Event()
        async def scheduled_embed(provider, texts, space_id):
            if asyncio.current_task().get_name() == "audit-older-build" and not paused.is_set():
                paused.set()
                await release.wait()
            return await original(provider, texts, space_id)
        monkeypatch.setattr(LocalTfidfEmbeddingProvider, "embed", scheduled_embed)
        older = MemoryIndex(store)
        task = asyncio.create_task(older.rebuild(), name="audit-older-build")
        await paused.wait()
        store.append_message("user", "后来的独立新安排", "second")
        newer = older if shared_instance else MemoryIndex(store)
        await newer.rebuild()
        newest_watermark = newer.watermark
        assert newest_watermark == store.snapshot()
        release.set()
        await task
        reopened = MemoryIndex(store)
        OBSERVATIONS["out_of_order_publish"] = {"newer_watermark": newest_watermark, "actual_current_watermark": reopened.watermark,
                                                 "archive_watermark": store.snapshot(), "current_vector_refs": [r["ref"] for r in reopened.indexes["event"].rows],
                                                 "missing_newer_vector": "second@1" not in {r["ref"] for r in reopened.indexes["event"].rows}}
        assert reopened.watermark == newest_watermark, {"published": reopened.watermark, "expected": newest_watermark,
                                                         "refs": [r["ref"] for r in reopened.indexes["event"].rows]}
    asyncio.run(exercise())


def test_legacy_saved_generation_and_pointer_still_load_and_rollback(tmp_path):
    from myatri.storage.archive import _atomic_write, _json
    store = ArchiveStore(tmp_path)
    store.append_message("user", "旧版档案", "old")
    index = MemoryIndex(store)
    older = asyncio.run(index.rebuild())
    envelope_path = index.path / "generations" / f"{older}.json"
    state = json.loads(envelope_path.read_text(encoding="utf-8"))["data"]
    state.pop("archive_sequence")
    checksum = digest(state)
    _atomic_write(envelope_path, _json({"data": state, "sha256": checksum}))
    _atomic_write(index.path / "current.json", _json({"generation": older, "sha256": checksum}))
    restored = MemoryIndex(store)
    assert restored.query("旧版档案")[0]["ref"] == "old@1"
    store.append_message("user", "新增经历", "new")
    newer = asyncio.run(restored.update())
    assert newer != older
    assert restored.watermark == store.snapshot()
    restored.rollback(older)
    assert restored.generation == older
    assert MemoryIndex(store).generation == older


def test_historical_evidence_revision_remains_valid_after_state_review(tmp_path):
    from myatri.cognition.association import AssociationAgent
    from myatri.persona.temporary import TemporaryStates
    from myatri.providers import FixtureProvider, Gateway
    from myatri.runtime.commit import Committer

    async def exercise():
        store = ArchiveStore(tmp_path)
        left = external(store, "a", "一起约好周末散步")
        right = external(store, "b", "后来对方取消周末散步")
        states = TemporaryStates(store)
        thought = states.create(TemporaryEntry(text="这次取消令人失落",
            origin_refs=[left.ref, right.ref]), entry_id="thought")
        edge = Edge(edge_id="relation", from_ref=left.ref, to_ref=right.ref,
                    type="contradicts", evidence_refs=[left.ref, right.ref, thought.ref])
        provider = FixtureProvider([{"content": json.dumps({"decision": "propose",
            "reason": "synthetic test", "edges": [edge.model_dump()]})}])
        index = MemoryIndex(store)
        await index.rebuild()
        proposal = await AssociationAgent(store, Gateway(provider), index).propose(
            [left.ref, right.ref, thought.ref])
        Committer(store).submit_proposal(proposal)
        await index.update()
        states.review("thought", base_revision=1, status="settled", reason="已有理解")
        fresh = external(store, "c", "一条后来的新经历")
        await index.update()
        assert index.watermark == store.snapshot()
        assert fresh.ref in {row["ref"] for row in index.indexes["event"].rows}
        assert [row["ref"] for row in index.indexes["temporary_state"].rows] == ["thought@2"]
        retained = next(row for row in index.graph.edges if row.get("record_ref") == "relation@1")
        assert retained["evidence_refs"] == edge.evidence_refs
        assert retained["type"] == "contradicts"
        assert store.get_record("thought", 1).ref == thought.ref
        assert store.verify_archive() == []
    asyncio.run(exercise())


def test_mismatched_index_uses_relation_versions_in_requested_snapshot(tmp_path):
    store = ArchiveStore(tmp_path)
    left = external(store, "a", "珊瑚海底潜泳")
    right = external(store, "b", "程序编译故障")
    edge = Edge(edge_id="relation", from_ref=left.ref, to_ref=right.ref,
                type="contradicts", evidence_refs=[left.ref, right.ref])
    original = Record(record_id="relation", record_kind="edge", source_refs=edge.evidence_refs,
                      payload=edge.model_dump())
    past = store.commit([original], "relation_v1")
    index = MemoryIndex(store)
    asyncio.run(index.rebuild())
    revised = edge.model_copy(update={"type": "follows_up"})
    store.commit([Record(record_id="relation", revision=2, supersedes_revision=1,
        record_kind="edge", source_refs=edge.evidence_refs, payload=revised.model_dump())], "relation_v2")
    current = RecallService(store, index).recall("珊瑚潜泳", filters={"kinds": ["event"]}, budget=5000)
    assert not current.counter_refs
    assert right.ref in {row.ref for row in current.records}  # typed edge still expands
    asyncio.run(index.update())
    historical = RecallService(store, index).recall("珊瑚潜泳", snapshot=past,
        filters={"kinds": ["event"]}, budget=5000)
    assert set(historical.counter_refs) == {left.ref, right.ref}
    assert all(not reason.startswith("vector:") and reason != "theme membership"
               for reasons in historical.reasons.values() for reason in reasons)


def test_future_theme_summary_cannot_recall_old_events_in_past(tmp_path):
    store = ArchiveStore(tmp_path)
    row = external(store, "a", "珊瑚海底潜泳")
    past = store.snapshot()
    index = MemoryIndex(store)
    asyncio.run(index.rebuild())
    theme_id, theme = next(iter(index.themes.items()))
    store.commit([Record(record_id=theme_id, record_kind="theme", source_refs=[row.ref],
        body_markdown="未来专属量子钥匙XYZ", payload={"name": "未来专属量子钥匙XYZ",
            "material_hash": theme["material_hash"]})], "future_summary")
    asyncio.run(index.update())
    service = RecallService(store, index)
    assert row.ref in {r.ref for r in service.recall("量子钥匙XYZ", filters={"kinds": ["event"]}).records}
    historical = service.recall("量子钥匙XYZ", snapshot=past, filters={"kinds": ["event"]})
    assert historical.records == []
    assert any("跳过该世代" in limitation for limitation in historical.limitations)


def test_recall_pins_generation_during_concurrent_install(tmp_path, monkeypatch):
    store = ArchiveStore(tmp_path)
    left = external(store, "a", "珊瑚海底潜泳")
    right = external(store, "b", "程序编译故障")
    past = store.snapshot()
    index = MemoryIndex(store)
    older = asyncio.run(index.rebuild())
    edge = Edge(edge_id="future", from_ref=left.ref, to_ref=right.ref,
                type="contradicts", evidence_refs=[left.ref, right.ref])
    store.commit([Record(record_id="future", record_kind="edge", source_refs=edge.evidence_refs,
                        payload=edge.model_dump())], "future")
    newer = asyncio.run(index.update())
    index.load(older)
    original_query = index.query
    swapped = False
    def query_and_swap(*args, **kwargs):
        nonlocal swapped
        if not swapped:
            swapped = True
            index.load(newer)
        return original_query(*args, **kwargs)
    monkeypatch.setattr(index, "query", query_and_swap)
    result = RecallService(store, index).recall("珊瑚潜泳", snapshot=past,
        filters={"kinds": ["event"]}, budget=5000)
    assert swapped
    assert not result.counter_refs
    assert right.ref not in {row.ref for row in result.records}
    assert result.index_watermark == past


@pytest.mark.asyncio
async def test_index_work_does_not_block_foreground_during_clustering(tmp_path, monkeypatch):
    import myatri.memory.index as index_module
    from myatri.app import Application

    app = Application(tmp_path, mode="offline")
    external(app.store, "a", "周末海边散步")
    main_thread = threading.get_ident()
    loop = asyncio.get_running_loop()
    entered = asyncio.Event()
    release = threading.Event()
    original_cluster = index_module.cluster
    original_snapshot = index_module.read_snapshot
    original_fit = LocalTfidfEmbeddingProvider.fit
    original_transform = LocalTfidfEmbeddingProvider.transform
    original_write = index_module._atomic_write
    phases = set()
    def off_loop(name, function):
        def wrapped(*args, **kwargs):
            assert threading.get_ident() != main_thread, name
            phases.add(name)
            return function(*args, **kwargs)
        return wrapped
    def controlled_cluster(*args, **kwargs):
        assert threading.get_ident() != main_thread
        phases.add("cluster")
        loop.call_soon_threadsafe(entered.set)
        if not release.wait(5):
            raise AssertionError("foreground event loop could not release clustering")
        return original_cluster(*args, **kwargs)
    monkeypatch.setattr(index_module, "read_snapshot", off_loop("archive", original_snapshot))
    monkeypatch.setattr(LocalTfidfEmbeddingProvider, "fit", off_loop("fit", original_fit))
    monkeypatch.setattr(LocalTfidfEmbeddingProvider, "transform", off_loop("embed", original_transform))
    monkeypatch.setattr(index_module, "cluster", controlled_cluster)
    monkeypatch.setattr(index_module, "_atomic_write", off_loop("publish", original_write))
    building = asyncio.create_task(app.index.rebuild())
    try:
        await asyncio.wait_for(entered.wait(), 3)
        answer = await asyncio.wait_for(app.conversation.respond("先聊聊新的安排"), 3)
        assert answer.payload["role"] == "assistant"
        assert not building.done()
    finally:
        release.set()
        await building
    assert phases == {"archive", "fit", "embed", "cluster", "publish"}


@pytest.mark.asyncio
async def test_external_async_embedding_keeps_callers_event_loop(tmp_path):
    owner_loop = asyncio.get_running_loop()
    owner_thread = threading.get_ident()
    class LoopBoundProvider:
        space_id, model, model_revision = "test_space", "fixture", "pinned_1"
        dimension, normalization = 2, "l2"
        async def embed(self, texts, space_id):
            assert asyncio.get_running_loop() is owner_loop
            assert threading.get_ident() == owner_thread
            await asyncio.sleep(0)
            return EmbeddingBatch(vectors=[[1.0, 0.0] for _ in texts], space_id=space_id,
                model=self.model, model_revision=self.model_revision,
                dimension=self.dimension, normalization=self.normalization)
    store = ArchiveStore(tmp_path)
    raw = store.append_message("user", "测试外部异步提供者", "raw")
    index = MemoryIndex(store, LoopBoundProvider())
    await index.rebuild()
    assert (await index.aquery("测试"))[0]["ref"] == raw.ref


@pytest.mark.asyncio
async def test_delayed_snapshot_cannot_copy_future_theme_summary_into_saved_generation(tmp_path, monkeypatch):
    import myatri.memory.index as index_module

    store = ArchiveStore(tmp_path)
    event = external(store, "a", "周末海边散步")
    index = MemoryIndex(store)
    await index.rebuild()
    past = index.watermark
    theme_id, theme = next(iter(index.themes.items()))
    original_snapshot = index_module.read_snapshot
    loop = asyncio.get_running_loop()
    entered, release = asyncio.Event(), threading.Event()
    call_lock = threading.Lock()
    calls = 0

    def controlled_snapshot(*args, **kwargs):
        nonlocal calls
        with call_lock:
            calls += 1
            pause = calls == 1
        snapshot = original_snapshot(*args, **kwargs)
        if pause:
            loop.call_soon_threadsafe(entered.set)
            if not release.wait(5):
                raise AssertionError("newer build did not release the older snapshot")
        return snapshot

    monkeypatch.setattr(index_module, "read_snapshot", controlled_snapshot)
    older_build = asyncio.create_task(index.rebuild())
    try:
        await asyncio.wait_for(entered.wait(), 3)
        store.commit([Record(record_id=theme_id, record_kind="theme", source_refs=[event.ref],
            body_markdown="仅在未来出现的量子钥匙XYZ", payload={"name": "未来专属名称",
                "material_hash": theme["material_hash"]})], "future_summary")
        newest = await index.rebuild()
        assert index.themes[theme_id]["summary"] == "仅在未来出现的量子钥匙XYZ"
    finally:
        release.set()
        await older_build
    assert index.generation == newest
    assert MemoryIndex(store).generation == newest
    # Rejected generations remain explicit load/rollback targets. Their
    # archive watermark must describe all of their contents, not just vectors.
    older_states = [json.loads(path.read_text(encoding="utf-8"))["data"]
                    for path in (index.path / "generations").glob("*.json")]
    older_states = [state for state in older_states if state["watermark"] == past]
    assert len(older_states) == 2
    assert all("量子钥匙XYZ" not in json.dumps(state["themes"], ensure_ascii=False)
               and "未来专属名称" not in json.dumps(state["themes"], ensure_ascii=False)
               for state in older_states)
