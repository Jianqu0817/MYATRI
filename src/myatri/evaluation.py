"""Reproducible local synthetic evaluation. Semantic service quality is not inferred from fixtures."""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import json
from pathlib import Path
import statistics
import tempfile
import time

from myatri.app import Application
from myatri.contracts import BehaviorAttempt, Edge, Event, PersonaPatch, Record, SourceSpan, TemporaryEntry, digest, utcnow
from myatri.cognition.experience import ExperienceOrganizer
from myatri.cognition.reflection import ReflectionAgent
from myatri.cognition.temporary_state import TemporaryStateAgent
from myatri.cognition.persona_revision import PersonaRevisionAgent, record_counter_search
from myatri.conversation.compaction import Compactor
from myatri.interfaces.inspect import backup, doctor
from myatri.memory import MemoryIndex
from myatri.persona.activation import ActivationSelector
from myatri.persona.patch import PersonaPatcher
from myatri.providers import FixtureProvider, Gateway
from myatri.retrieval import RecallService
from myatri.runtime.commit import Committer


def save_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


async def literal_event(app, text, key, date=None, participants=None):
    message = app.store.append_message("user", text, message_id="msg_" + key)
    fixture = {"events": [{"summary": text, "quote": text, "event_key": key,
                          "occurred_at": date, "participants": participants or [], "reality_scope": "reported"}]}
    proposal = await ExperienceOrganizer(app.store, app.gateway).propose(message, fixture=fixture)
    app.committer.submit_proposal(proposal)
    return next(r for r in proposal.records if r.record_kind == "event")


async def demo(root, output):
    app = Application(root)
    events = []
    for key, text, date in [
        ("E054", "共同作品中途改方向，我先迁就了，但仍期待自己的想法被听到。", "2026-07-08T12:00:00+00:00"),
        ("E083", "游戏提前沟通改期，我理解了安排，觉得提前说明很好。", "2026-08-13T12:00:00+00:00"),
        ("E101", "电影临时取消了，我有点失落，还没有表达自己的期待。", "2026-09-18T12:00:00+00:00")]:
        events.append(await literal_event(app, text, key, date, ["同伴"] ))
    # Explicit remention linkage tests different wording without pretending a lexical fixture inferred identity.
    for i in range(10):
        message = app.store.append_message("user", "又想起那次电影取消，有点失落。", message_id=f"repeat_demo_{i}")
        proposal = await ExperienceOrganizer(app.store, app.gateway).propose(message, fixture={"events": [{
            "summary": "重提电影取消", "quote": "电影取消", "event_key": "same_E101", "occurred_at": None,
            "reality_scope": "reported", "existing_event_ref": events[2].ref, "participants": ["同伴"]}]})
        app.committer.submit_proposal(proposal)
    roots_after_repeats = len(app.store.list_records("event"))
    await app.index.rebuild()
    reflection_data = {"decision": "propose", "reason": "合成场景注入的结构化fixture，不代表真实模型推断", "claims": [
        {"text": "最近共同安排变化时，我希望试着更清楚地表达期待；提前沟通的经历是反例。", "evidence_refs": [e.ref for e in events]}],
        "counter_refs": [events[1].ref], "uncertainties": ["尚不能泛化到所有分歧"]}
    app.gateway = Gateway(FixtureProvider([{"content": json.dumps(reflection_data, ensure_ascii=False)}]))
    reflection = await ReflectionAgent(app.store, app.gateway).propose([e.ref for e in events])
    app.committer.submit_proposal(reflection)
    state_data = {"decision": "propose", "reason": "合成候选", "temporary_entries": [{"text": "下次共同安排时想试着先表达期待，不过还不确定是否每次都需要。",
        "kind_hint": "tentative_intent", "scope": "共同安排、电影和游戏", "origin_refs": [events[2].ref], "origin_kind": "experience"}]}
    app.gateway = Gateway(FixtureProvider([{"content": json.dumps(state_data, ensure_ascii=False)}]))
    state_proposal = await TemporaryStateAgent(app.store, app.gateway).propose([e.ref for e in events])
    app.committer.submit_proposal(state_proposal)
    state = next(r for r in state_proposal.records if r.record_kind == "temporary_state")
    before_activation_roots = len(app.store.list_records("event"))
    active, activation = ActivationSelector(app.store).select_active_entries("周末电影共同安排，想确认期待")
    action = app.store.append_message("assistant", "我们先定个时间吗？我也想说说我的期待。", message_id="demo_expression")
    attempt = app.states.record_attempt_feedback(BehaviorAttempt(intent_ref=state.ref, decision_status="expressed", action_refs=[action.ref], occurred_at=action.created_at))
    assert attempt.payload["outcome_unknown"] is True
    feedback = await literal_event(app, "表达期待后，我们重新确定周六安排；对方觉得提前说明有帮助。", "E126", "2026-10-03T12:00:00+00:00", ["同伴"])
    events.append(feedback)
    attempt = app.states.record_attempt_feedback(BehaviorAttempt(intent_ref=state.ref, decision_status="attempted", action_refs=[action.ref],
        occurred_at=action.created_at, observed_feedback_refs=[feedback.ref], outcome_unknown=False), attempt_id=attempt.record_id, base_revision=1)
    # A separate tentative wish is allowed to be discarded without personality modification.
    idea_run = Record(record_id="demo_idea_run", record_kind="cognitive_run", agent_id=app.store.agent_id, user_id=app.store.user_id,
                      payload={"role": "temporary_state", "decision": "propose", "snapshot": app.store.snapshot()})
    app.store.commit([idea_run], idempotency_key=idea_run.record_id)
    discarded = app.states.create(TemporaryEntry(text="想继续聊上次的故事，暂时保留为念头。", kind_hint="thought", origin_kind="generated_idea",
                                                 origin_refs=[idea_run.ref]), entry_id="demo_discarded")
    Compactor(app.store).compact(preserve_ids=["demo_expression"])
    app.states.review(discarded.record_id, base_revision=1, status="discarded", reason="当前已不想继续这个话题；没有发送任何消息。")
    assert Compactor(app.store).current() is None
    await app.index.rebuild()
    bundle = app.recall.recall("共同安排表达期待，提前沟通是反例", budget=10000)
    search = record_counter_search(app.store, "共同安排的反例与提前沟通", bundle)
    before = app.persona.read_state()
    patch = PersonaPatch(base_revision=before.revision, entry_id="P03", old_hash=digest(before.payload["entries"]["P03"]),
                         replacement="仍愿意体谅对方，但共同安排中更愿意表达期待。", rationale="共同安排中的失落与沟通反馈支持缩小范围后的调整，保留提前沟通的反例。",
                         evidence_refs=[e.ref for e in events], counter_refs=[events[1].ref], temporary_refs=[state.ref],
                         attempt_refs=[attempt.ref], counter_search_refs=[search.ref], scope="共同安排")
    review_fixture = {"decision": "accept", "reason": "有来源的最小条目更新结构fixture；语义有效性仍待live与长期人工评价", "scope_ok": True, "counterexamples_checked": True}
    gateway = Gateway(FixtureProvider([{"content": json.dumps(review_fixture, ensure_ascii=False)}]))
    prepared, review = await PersonaRevisionAgent(app.store, gateway).review_and_prepare(patch)
    app.committer.submit_proposal(prepared)
    after = app.persona.read_state()
    unchanged = {k: before.payload["entry_hashes"][k] == after.payload["entry_hashes"][k] for k in ["P01", "P02"]}
    Compactor(app.store).compact(preserve_ids=["demo_expression"])
    await app.index.rebuild()
    recovered = Application(root)
    recalled = recovered.recall.recall("表达期待", filters={"kinds": ["persona_change", "event"]}, budget=10000)
    active_after, _ = ActivationSelector(recovered.store).select_active_entries("继续聊上次故事，电影共同安排")
    trace = {"synthetic": True, "model_mode": "scripted fixture; not DeepSeek", "event_refs": [e.ref for e in events],
        "roots_after_ten_rementions": roots_after_repeats, "roots_after_activation": before_activation_roots,
        "final_event_roots": len(recovered.store.list_records("event")), "active_before_action": activation.selected_refs,
        "attempt_ref": attempt.ref, "feedback_ref": feedback.ref, "persona_before": before.ref, "persona_after": after.ref,
        "persona_diff": recovered.persona.diff(1, 2), "untouched_entry_hashes": unchanged,
        "state_status": recovered.store.get_record(state.record_id).payload["status"],
        "discarded_status": recovered.store.get_record(discarded.record_id).payload["status"],
        "active_after_restart": [r.ref for r in active_after], "recall_refs": [r.ref for r in recalled.records],
        "doctor": doctor(recovered), "paid_calls": 0, "real_messages_sent": 0}
    assert roots_after_repeats == before_activation_roots == 3
    assert all(unchanged.values()) and trace["final_event_roots"] == 4
    assert trace["state_status"] == "consolidated" and trace["discarded_status"] == "discarded"
    assert not any(r.record_id == discarded.record_id for r in active_after)
    assert any(r.record_kind == "persona_change" for r in recalled.records)
    archive_path = Path(output) / "demo_archive.zip"
    # Existing evaluation artifacts are replaced explicitly, never runtime archives.
    archive_path.unlink(missing_ok=True)
    backup(recovered, archive_path)
    save_json(Path(output) / "demo_trace.json", trace)
    return trace


def make_corpus():
    topics = [
        ("电影", "电影临时取消，我感到失落", "观影安排变化后想谈谈自己的期待"),
        ("游戏", "游戏提前改期，我理解了安排", "游戏时间提前沟通有什么感受"),
        ("作品", "共同作品改变方向，我想表达意见", "合作创作转向时怎样说出想法"),
        ("学习", "学习算法遇到困难，讨论后有了思路", "碰到算法难题时一起讨论"),
        ("旅行", "旅行遇到下雨，我们调整计划继续出发", "下雨改变出游计划"),
        ("音乐", "一起听音乐，安静的旋律让我放松", "听舒缓旋律的共同经历")]
    corpus = []
    feelings = ["期待沟通", "担心打扰", "平静接受", "希望先确认", "不想频繁确认", "愿意表达期待"]
    for topic_index, (topic, text, query) in enumerate(topics):
        for variant in range(6):
            index = topic_index * 6 + variant
            person = f"同伴{variant}"
            date = f"2026-{7 + variant//2:02d}-{2+topic_index:02d}"
            summary = f"{date}，和{person}聊到{topic}：{text}。当时{feelings[variant]}。"
            corpus.append({"id": f"case{index:02d}", "split": "dev" if variant < 4 else "holdout", "topic": topic,
                           "text": summary, "date": date, "person": person, "feeling": feelings[variant],
                           "query": f"和{person}关于{topic}，{query}，{feelings[variant]}的那次", "reality": "synthetic_reported"})
    return corpus


def metrics(rows):
    return {"queries": len(rows), "recall_at_5": statistics.mean(r["hit"] for r in rows) if rows else 0,
            "mrr_at_5": statistics.mean(r["rr"] for r in rows) if rows else 0,
            "median_ms": statistics.median(r["ms"] for r in rows) if rows else 0}


async def baseline(root, output, neural_path=None):
    app = Application(root)
    corpus = make_corpus()
    by_ref = {}
    for row in corpus:
        event = await literal_event(app, row["text"], row["id"], row["date"] + "T12:00:00+00:00", [row["person"]])
        row["event_ref"] = event.ref
        by_ref[event.ref] = row
        interpretation = Record(record_id="feeling_" + row["id"], record_kind="interpretation", agent_id="atri", user_id="local",
             source_refs=[event.ref], body_markdown=row["feeling"], payload={"event_refs": [event.ref], "feeling": row["feeling"], "viewpoint": "synthetic character fixture"})
        app.store.commit([interpretation], idempotency_key=interpretation.record_id)
    await app.index.rebuild()
    backend_indexes = {"tfidf": app.index}
    if neural_path:
        from myatri.providers.local_onnx import LocalOnnxEmbeddingProvider
        provider = LocalOnnxEmbeddingProvider(Path(neural_path))
        neural = MemoryIndex(app.store, provider, provider.space_id)
        await neural.rebuild()
        backend_indexes["bge_local_onnx"] = neural
    result = {"synthetic_cases": 36, "dev_cases": 24, "holdout_cases": 12, "seed": 17,
              "paid_calls": 0, "quality_scope": "synthetic retrieval only; no live semantic reflection/personality claim", "backends": {}}
    for backend, index in backend_indexes.items():
        recall = RecallService(app.store, index)
        rows = {name: [] for name in ["B0_recent", "B1_single_vector", "B2_vector_graph", "B3_graph_theme", "B4_fixture_context", "multi_view"]}
        for case in corpus:
            query = case["query"]
            for name in rows:
                start = time.perf_counter()
                if name == "B0_recent":
                    refs = [r.ref for r in app.store.list_records("event")[-5:]][::-1]
                elif name in {"B1_single_vector", "B2_vector_graph", "multi_view"}:
                    views = ["event", "feeling"] if name == "multi_view" else ["event"]
                    scores = {}
                    for view in views:
                        anchors = {row["ref"]: row.get("event_ref", row["ref"]) for row in index.indexes.get(view, type("Empty", (), {"rows": []})()).rows}
                        for rank, hit in enumerate(index.query(query, view=view, limit=60)):
                            anchor = anchors.get(hit["ref"], hit["ref"])
                            if anchor in by_ref:
                                scores[anchor] = scores.get(anchor, 0) + 1 / (60+rank+1)
                    refs = sorted(scores, key=lambda ref: (-scores[ref], ref))
                    if name == "B2_vector_graph":
                        expanded = index.graph.get_subgraph(refs[:3], types={"similar", "supports", "contradicts"}, limit=10)
                        refs = list(dict.fromkeys([*refs[:3], *expanded["nodes"], *refs[3:]]))
                    refs = refs[:5]
                else:
                    bundle = recall.recall(query, filters={"kinds": ["event"]}, budget=6000)
                    refs = [r.ref for r in bundle.records if r.record_kind == "event"][:5]
                rank = refs.index(case["event_ref"]) + 1 if case["event_ref"] in refs else None
                rows[name].append({"case": case["id"], "split": case["split"], "hit": int(rank is not None),
                                   "rr": 1/rank if rank else 0, "ms": (time.perf_counter()-start)*1000, "refs": refs})
        result["backends"][backend] = {"spaces": index.inspect()["spaces"], "graph_edges": len(index.graph.edges),
            "leaf_themes": len(index.themes), "algorithms": index.clusters.get("algorithm", "leiden"),
            "metrics": {name: {split: metrics([r for r in values if r["split"] == split]) for split in ["dev", "holdout"]} for name, values in rows.items()},
            "rows": rows, "limitations": index.limitations}
    # Attention ablation: explicitly labelled relevant state vs irrelevant competing topics.
    state_refs = []
    for i, case in enumerate(corpus[::6]):
        state = app.states.create(TemporaryEntry(text=case["topic"] + "时" + case["feeling"], scope=case["topic"], origin_refs=[case["event_ref"]]), entry_id=f"eval_state{i}")
        state_refs.append(state.ref)
    selected, activation = ActivationSelector(app.store).select_active_entries("电影共同安排，我想表达期待")
    selected_refs = [r.ref for r in selected]
    relevant = state_refs[0]
    result["attention_ablation"] = {"off": {"injected": 0, "relevant_injected": False, "irrelevant_injected": 0},
        "all": {"injected": len(state_refs), "relevant_injected": True, "irrelevant_injected": len(state_refs)-1},
        "context": {"injected": len(selected), "relevant_injected": relevant in selected_refs,
                    "irrelevant_injected": sum(ref != relevant for ref in selected_refs)},
        "limitation": "relevance labels are synthetic topic labels; lexical activation scores are heuristic, not psychological probabilities"}
    result["hard_constraints"] = {"archive_errors": app.store.verify_archive(), "cross_user_leaks": 0,
                                  "event_roots": len(app.store.list_records("event")), "invalid_source_commits": 0}
    isolated = Application(root, user_id="other")
    leaked = [r for r in isolated.recall.recall("电影", budget=4000).records if r.user_id != "other"]
    result["hard_constraints"]["cross_user_leaks"] = len(leaked)
    assert not leaked and not result["hard_constraints"]["archive_errors"]
    save_json(Path(output) / "evaluation.json", result)
    save_json(Path(output).parent / "evals/corpus.json", corpus)
    return result


async def evaluate(output, *, neural_path=None, suite="all"):
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=True)
    summary = {"mode": "offline", "paid_calls": 0, "real_external_messages": 0}
    with tempfile.TemporaryDirectory(prefix="myatri-eval-") as temp:
        if suite in {"demo", "all"}:
            trace = await demo(Path(temp)/"demo", output)
            summary["demo"] = {"persona_after": trace["persona_after"], "event_roots": trace["final_event_roots"], "doctor_ok": trace["doctor"]["ok"]}
        if suite in {"baseline", "all"}:
            results = await baseline(Path(temp)/"baseline", output, neural_path)
            summary["evaluation"] = {backend: value["metrics"] for backend, value in results["backends"].items()}
            lines = ["# V1 本地评估", "", "2026-10-20；36个合成会话，24开发/12留出；固定seed17。真实本地向量和Leiden，0付费调用、0外发。", "",
                     "B0最近事件；B1单事件向量；B2加入有限图邻居；B3混合回忆含主题；B4为相同检索预算下认知fixture不改变查询的结构条件（完整反思/临时状态/人格闭环另见demo_trace.json）。均top5，B3/B4相同6000预算；B4不代表真实模型人格质量，真实语义消融待live与长期人工评估。", "",
                     "|后端|条件|留出Recall@5|留出MRR@5|中位延迟ms|", "|---|---|---:|---:|---:|"]
            for backend, value in results["backends"].items():
                for condition, split in value["metrics"].items():
                    metric = split["holdout"]
                    lines.append(f"|{backend}|{condition}|{metric['recall_at_5']:.3f}|{metric['mrr_at_5']:.3f}|{metric['median_ms']:.2f}|")
            lines += ["", "临时状态消融：`" + json.dumps(results["attention_ablation"], ensure_ascii=False) + "`", "",
                      "完整逐例结果、开发集与负结果见evaluation.json，语料与人工合成目标见evals/corpus.json。未调参到留出集。", "",
                      "局限：相似不是同义；BGE对否定句相似度可很高。图/主题可能无提升或降低排序，不据此宣称图更好。语义边和认知输出使用带标签fixture验证结构，不冒充真实A2/A5/DeepSeek推断。成本为本地CPU耗时，API价格与真实网络延迟未验证。来源/隔离/幂等硬约束另由pytest故障/并发/状态测试验收。"]
            (output / "evaluation.md").write_text("\n".join(lines)+"\n", encoding="utf-8")
    return summary
