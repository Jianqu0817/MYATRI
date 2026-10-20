import asyncio
import json

import numpy as np
import pytest

from myatri.contracts import ClusterSnapshot, Edge, Event, Record, SourceSpan, digest
from myatri.memory import ExactVectorIndex, LocalTfidfEmbeddingProvider, MemoryGraph, MemoryIndex
from myatri.memory.themes import build_themes
from myatri.storage import ArchiveStore


def add_event(store, record_id, text, *, day="2026-10-01", person="小林"):
    raw = store.append_message("user", text, f"raw_{record_id}")
    event = Event(occurred_at=f"{day}T10:00:00+00:00", time_precision="day", participants=[person], fact_summary=text,
                  source_spans=[SourceSpan(message_ref=raw.ref, start=0, end=len(text), quote=text)], event_fingerprint=digest([record_id, text]))
    record = Record(record_id=record_id, record_kind="event", source_refs=[raw.ref], body_markdown=text, payload=event.model_dump(mode="json"))
    store.commit([record], f"event_{record_id}")
    return record


def populated(tmp_path):
    store = ArchiveStore(tmp_path)
    rows = [add_event(store, "e1", "小林取消了周末一起散步的约定"),
            add_event(store, "e2", "小林重新约定周末一起散步"),
            add_event(store, "e3", "我和小林一起散步聊约定"),
            add_event(store, "e4", "今天修复代码编译程序错误"),
            add_event(store, "e5", "今天编译代码修复程序测试"),
            add_event(store, "e6", "稀有珊瑚海底潜泳")]
    for event, text in [(rows[0], "被临时取消时有些失落，期待提前说明"), (rows[1], "重新约定以后感到安心，也期待提前说明")]:
        record = Record(record_id=f"feeling_{event.record_id}", record_kind="interpretation", source_refs=[event.ref],
                        body_markdown=text, payload={"feeling": text})
        store.commit([record], record.record_id)
    return store, rows


def test_exact_index_refuses_other_space_and_dimension():
    rows = [{"ref": "a@1", "vector": [1, 0], "space_id": "a", "view": "event"}]
    index = ExactVectorIndex("a", 2, rows)
    assert index.search([1, 0], space_id="a")[0]["ref"] == "a@1"
    with pytest.raises(ValueError, match="space"):
        index.search([1, 0], space_id="b")
    with pytest.raises(ValueError, match="dimension"):
        index.search([1], space_id="a")
    with pytest.raises(ValueError, match="space"):
        ExactVectorIndex("b", 2, rows)


def test_real_tfidf_state_roundtrip_and_migration():
    provider = LocalTfidfEmbeddingProvider().fit(["小林取消散步", "代码编译错误"])
    batch = provider.transform(["取消散步"])
    assert np.linalg.norm(batch.vectors[0]) == pytest.approx(1)
    restored = LocalTfidfEmbeddingProvider.from_state(json.loads(json.dumps(provider.state())))
    assert restored.transform(["取消散步"]).vectors == batch.vectors
    newer = LocalTfidfEmbeddingProvider().fit(["小林取消散步", "代码编译错误", "全新资料"])
    assert newer.space_id != provider.space_id
    with pytest.raises(ValueError):
        restored.transform(["散步"], newer.space_id)


def test_generation_restart_cache_real_leiden_and_rollback(tmp_path):
    store, events = populated(tmp_path)
    index = MemoryIndex(store, k=2, threshold=0.2)
    first = asyncio.run(index.rebuild())
    assert index.query("取消散步")[0]["ref"] in {"e1@1", "raw_e1@1"}
    assert index.clusters["algorithm"] == "leiden"
    assert index.clusters["quality"]["actual_leiden_runs"] > 0
    assert index.clusters["parent"]
    assert "e6@1" in index.clusters["quality"]["isolated_nodes"]
    assert set(index.graph.nodes) == {record.ref for record in events}
    assert "feeling" in index.indexes
    assert any("feeling" in edge.get("views", {}) for edge in index.graph.edges)
    original_space = index.indexes["event"].space_id
    restarted = MemoryIndex(ArchiveStore(tmp_path))
    assert restarted.query("取消散步") == index.query("取消散步")
    asyncio.run(restarted.rebuild())
    assert restarted.cache_hits > 0
    add_event(store, "e7", "额外的全新消息改变拟合语料")
    second = asyncio.run(restarted.update())
    assert second != first
    assert restarted.indexes["event"].space_id != original_space
    with pytest.raises(ValueError):
        restarted.query("散步", space_id=original_space)
    restarted.rollback(first)
    assert restarted.generation == first
    assert restarted.indexes["event"].space_id == original_space
    assert MemoryIndex(store).generation == first


def test_typed_semantic_graph_excludes_contradictions_from_leiden_weights(tmp_path):
    store, events = populated(tmp_path)
    edge = Edge(edge_id="counter", from_ref=events[0].ref, to_ref=events[1].ref, type="contradicts", evidence_refs=[events[0].ref, events[1].ref])
    record = Record(record_id="edge_counter", record_kind="edge", source_refs=edge.evidence_refs, payload=edge.model_dump(mode="json"))
    store.commit([record], "counter")
    index = MemoryIndex(store)
    asyncio.run(index.rebuild())
    assert any(e["type"] == "contradicts" for e in index.graph.edges)
    assert index.clusters["params"]["edge_type"] == "similar"
    subgraph = index.graph.get_subgraph([events[0].ref], types={"contradicts"})
    assert events[1].ref in subgraph["nodes"]
    assert all(e["type"] == "contradicts" for e in subgraph["edges"])


def test_theme_ids_split_merge_and_soft_memberships():
    records = {f"{name}@1": Record(record_id=name, record_kind="persona_version") for name in "abcd"}
    graph = MemoryGraph(list(records), [{"edge_id": "ab", "type": "similar", "from_ref": "a@1", "to_ref": "b@1", "weight": 0.5},
                                       {"edge_id": "bc", "type": "similar", "from_ref": "b@1", "to_ref": "c@1", "weight": 0.4}])
    def snap(groups):
        return ClusterSnapshot(cluster_run_id="test", graph_generation="test", algorithm_version="test", params={}, seed=1,
                               members=groups, quality={"leaf_cluster_ids": list(groups)})
    initial, _ = build_themes(snap({"one": list(records)}), graph, records)
    unchanged, lineage = build_themes(snap({"renamed": list(records)}), graph, records, initial)
    assert set(unchanged) == set(initial)
    assert lineage[0]["type"] == "continued"
    split, lineage = build_themes(snap({"left": ["a@1", "b@1"], "right": ["c@1", "d@1"]}), graph, records, initial)
    assert any(row["type"] == "split" for row in lineage)
    assert sum("b@1" in theme["memberships"] for theme in split.values()) == 2
    merged, lineage = build_themes(snap({"one": list(records)}), graph, records, split)
    assert any(row["type"] == "merged" for row in lineage)
    assert len(merged) == 1


def test_empty_generation_and_tamper_detection(tmp_path):
    store = ArchiveStore(tmp_path)
    index = MemoryIndex(store)
    generation = asyncio.run(index.rebuild())
    assert index.query("空白") == []
    assert index.graph.nodes == []
    path = index.path / "generations" / f"{generation}.json"
    state = json.loads(path.read_text(encoding="utf-8"))
    state["data"]["user_id"] = "other"
    path.write_text(json.dumps(state), encoding="utf-8")
    with pytest.raises(ValueError, match="checksum"):
        MemoryIndex(store)


def test_temporary_state_view_is_separate_and_latest_revision_only(tmp_path):
    store = ArchiveStore(tmp_path)
    raw = store.append_message("user", "我们下次再谈海边散步", "raw")
    first = Record(record_id="thought", record_kind="temporary_state", source_refs=[raw.ref], body_markdown="还想问问海边散步", payload={"text": "还想问问海边散步", "status": "open"})
    store.commit([first], "thought")
    index = MemoryIndex(store)
    asyncio.run(index.rebuild())
    assert index.query("海边散步", view="temporary_state")[0]["ref"] == "thought@1"
    assert "thought@1" not in index.graph.nodes
    second = Record(record_id="thought", revision=2, supersedes_revision=1, record_kind="temporary_state", source_refs=[raw.ref], body_markdown="对方不愿再谈，撤回念头", payload={"text": "对方不愿再谈，撤回念头", "status": "discarded"})
    store.commit([second], "discard", expected={"thought": 1})
    asyncio.run(index.update())
    assert [row["ref"] for row in index.indexes["temporary_state"].rows] == ["thought@2"]


def test_model_theme_overlay_invalidated_when_counter_material_changes(tmp_path):
    store, _ = populated(tmp_path)
    index = MemoryIndex(store)
    asyncio.run(index.rebuild())
    theme_id, theme = next((key, row) for key, row in index.themes.items() if "e1@1" in row["members"])
    model_theme = Record(record_id=theme_id, record_kind="theme", source_refs=theme["members"],
                         author_kind="model", generator={"provider": "fixture", "model": "offline-schema-test", "prompt_version": "v1", "run_id": "test"},
                         body_markdown="仅供接口验证的模型主题摘要", payload={"name": "模型测试标签", "material_hash": theme["material_hash"]})
    store.commit([model_theme], "model_theme")
    asyncio.run(index.update())
    assert index.themes[theme_id]["name"] == "模型测试标签"
    assert index.themes[theme_id]["needs_summary"] is False
    assert index.themes[theme_id]["naming_source"] == "model"
    edge = Edge(edge_id="new_counter", from_ref="e1@1", to_ref="e4@1", type="contradicts", evidence_refs=["e1@1", "e4@1"])
    store.commit([Record(record_id=edge.edge_id, record_kind="edge", source_refs=edge.evidence_refs, payload=edge.model_dump(mode="json"))], "new_counter")
    asyncio.run(index.update())
    assert index.themes[theme_id]["summary"] == ""
    assert index.themes[theme_id]["needs_summary"] is True
    assert index.themes[theme_id]["name"] != "模型测试标签"
    assert "e4@1" in index.theme_materials(theme_id)["counter_refs"]
