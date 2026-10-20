"""Compatibility checks for the production A-MEM linked-memory code port."""
import random

import myatri.memory.graph as graph_module
from myatri._vendor.amem import iter_unique_neighbors
from myatri.contracts import Edge, Event, Record, SourceSpan
from myatri.memory import MemoryGraph
from myatri.retrieval import RecallService
from myatri.storage import ArchiveStore


def _previous_subgraph(edges, seeds, *, depth=1, types=None, limit=30):
    """Frozen pre-port traversal, including incident-edge multiplicity/order."""
    accepted = types or {"follows_up", "reinterprets", "supports", "contradicts"}
    visited, frontier, selected, paths = set(seeds), list(seeds), [], [[ref] for ref in seeds]
    path_map = {ref: [ref] for ref in seeds}
    for _ in range(depth):
        next_frontier = []
        for edge in edges:
            if edge["type"] not in accepted:
                continue
            left, right = edge["from_ref"], edge["to_ref"]
            for origin, target in ((left, right), (right, left)):
                if origin in frontier:
                    selected.append(edge)
                    if target not in visited and len(visited) < limit:
                        visited.add(target)
                        next_frontier.append(target)
                        path_map[target] = path_map[origin] + [target]
                        paths.append(path_map[target])
        frontier = next_frontier
    return {"nodes": sorted(visited), "edges": selected, "paths": paths}


def _edge(name, left, right, kind="supports"):
    return {"edge_id": name, "from_ref": left, "to_ref": right, "type": kind}


def test_order_limits_paths_and_edge_multiplicity_match_pre_port():
    edges = [_edge("reverse", "b", "a"), _edge("late", "a", "c"),
             _edge("cycle", "c", "b", "contradicts"), _edge("loop", "a", "a"),
             _edge("duplicate", "b", "a"), _edge("deep", "c", "d", "follows_up"),
             _edge("algorithm", "a", "x", "similar"), _edge("invalid", "a", "z", "unknown")]
    graph = MemoryGraph(list("abcdxz"), edges)
    for seeds in ([], ["a"], ["b", "a"], ["a", "a"], ["missing", "c"]):
        for depth in (-1, 0, 1, 2, 5):
            for limit in (-1, 0, 1, 2, 4, 20):
                for types in (None, set(), {"supports"}, {"contradicts"}, {"unknown"}):
                    options = {"depth": depth, "limit": limit, "types": types}
                    assert graph.get_subgraph(seeds, **options) == _previous_subgraph(edges, seeds, **options)


def test_randomized_graphs_match_frozen_pre_port_traversal():
    rng = random.Random(20261020)
    nodes = [f"node_{i}" for i in range(12)]
    kinds = ["supports", "contradicts", "reinterprets", "follows_up", "similar", "unknown"]
    for case in range(120):
        edges = [_edge(f"edge_{i}", rng.choice(nodes), rng.choice(nodes), rng.choice(kinds))
                 for i in range(rng.randrange(35))]
        seeds = [rng.choice(nodes) for _ in range(rng.randrange(5))]
        options = {"depth": rng.randrange(5), "limit": rng.randrange(15),
                   "types": rng.choice([None, set(), {"supports"}, {"supports", "contradicts"}])}
        assert MemoryGraph(nodes, edges).get_subgraph(seeds, **options) == _previous_subgraph(edges, seeds, **options), case


def test_upstream_port_keeps_new_neighbors_and_consumes_incident_candidates():
    consumed = []

    def candidates():
        for pair in [("seed", "seed"), ("seed", "new"), ("seed", "new"), ("seed", "later")]:
            consumed.append(pair)
            yield pair

    seen = {"seed"}
    assert list(iter_unique_neighbors(candidates(), seen, 1)) == [("seed", "new")]
    assert seen == {"seed", "new"}
    assert len(consumed) == 4
    # The old complete search_agentic sliced away all linked neighbors once
    # seed results filled k. The extracted kernel must preserve expansion.
    assert MemoryGraph(["seed", "new"], [_edge("link", "seed", "new")]).get_subgraph(["seed"], limit=2)["paths"] == [["seed"], ["seed", "new"]]


def test_recall_service_calls_port_and_preserves_typed_source_paths(tmp_path, monkeypatch):
    store = ArchiveStore(tmp_path)
    for name, text in [("seed", "天文望远镜"), ("linked", "山谷清泉")]:
        raw = store.append_message("user", text, f"raw_{name}")
        event = Event(fact_summary=text, event_fingerprint=name,
                      source_spans=[SourceSpan(message_ref=raw.ref, start=0, end=len(text), quote=text)])
        store.commit([Record(record_id=name, record_kind="event", source_refs=[raw.ref],
                             body_markdown=text, payload=event.model_dump(mode="json"))], name)
    relation = Edge(edge_id="follow", from_ref="seed@1", to_ref="linked@1", type="follows_up",
                    evidence_refs=["seed@1", "linked@1"])
    store.commit([Record(record_id="follow", record_kind="edge", source_refs=relation.evidence_refs,
                         payload=relation.model_dump(mode="json"))], "follow")
    calls = []
    original = graph_module.iter_unique_neighbors

    def traced(candidates, seen_ids, k):
        selected = list(original(candidates, seen_ids, k))
        calls.append(selected)
        yield from selected

    monkeypatch.setattr(graph_module, "iter_unique_neighbors", traced)
    bundle = RecallService(store).recall("天文望远镜", filters={"kinds": ["event"]}, budget=12000)
    assert any(("seed@1", "linked@1") in selected for selected in calls)
    assert {"seed@1", "linked@1", "raw_seed@1", "raw_linked@1"} <= {record.ref for record in bundle.records}
    assert ["seed@1", "linked@1"] in bundle.paths
    assert "typed graph expansion" in bundle.reasons["linked@1"]
