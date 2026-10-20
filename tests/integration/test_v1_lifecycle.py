import asyncio
import json

from myatri.app import Application
from myatri.contracts import ModelResponse, PersonaPatch
from myatri.conversation.compaction import Compactor
from myatri.persona.activation import ActivationSelector
from myatri.persona.temporary import event_roots
from myatri.providers import FixtureProvider


def assert_jobs_completed(app):
    jobs = app.queue.list_jobs()
    incomplete = [{key: job[key] for key in ("role", "status", "error")} for job in jobs if job["status"] != "succeeded"]
    assert not incomplete, incomplete
    return jobs


def test_default_offline_respond_drain_real_index_and_restart(tmp_path):
    async def exercise():
        app = Application(tmp_path)
        first = await app.conversation.respond("今天约好一起看电影，因为安排变化取消了。", message_id="movie_cancel")
        second = await app.conversation.respond("后来重新约定一起看电影，你提前确认让我安心。", message_id="movie_renew")
        assert first.payload["role"] == second.payload["role"] == "assistant"
        assert await app.drain() > 0
        jobs = assert_jobs_completed(app)
        roles = {job["role"] for job in jobs}
        assert {"ingest", "index", "cycle", "association", "theme", "reflection", "temporary_state", "persona_revision"} <= roles
        assert len(app.store.list_records("event")) == 2
        assert app.index.indexes["event"].rows
        assert app.index.clusters["quality"]["actual_leiden_runs"] > 0
        assert app.index.clusters["algorithm"] == "leiden"
        bundle = app.recall.recall("取消电影后来重新约定", budget=12000)
        assert {"movie_cancel@1", "movie_renew@1"} <= {r.ref for r in bundle.records}
        assert app.persona.read_state().revision == 1
        assert app.states.list() == []  # Default fixture explicitly defers semantic decisions.
        Compactor(app.store).compact()
        generation, count = app.index.generation, len(jobs)
        restored = Application(tmp_path)
        restored.recover_pending()
        assert await restored.drain() == 0
        assert len(restored.queue.list_jobs()) == count
        assert_jobs_completed(restored)
        assert restored.index.generation == generation
        assert len(event_roots(restored.store, [r.ref for r in restored.store.list_records("event")])) == 2
        assert restored.store.verify_archive() == []
    asyncio.run(exercise())


class ScriptedCognition(FixtureProvider):
    """Protocol fixture for A5/A8/A6/A7; never a live semantic-model claim."""

    async def generate(self, request):
        if request.role not in {"reflection", "temporary_state", "persona_revision", "reviewer"}:
            return await super().generate(request)
        self.requests.append(request.model_copy(deep=True))
        sources = json.loads(request.messages[-1]["content"])
        sources = sources["materials"] if isinstance(sources, dict) else sources
        events = [row for row in sources if row["record_kind"] == "event"]
        if request.role == "reflection":
            value = {"decision": "propose", "reason": "离线脚本比较两次独立原文", "claims": [{"text": "安排变化时，可以有范围地先说期待，不把次数当人格依据。", "evidence_refs": [f"{row['record_id']}@{row['revision']}" for row in events]}]}
        elif request.role == "temporary_state":
            value = {"decision": "propose", "reason": "离线状态结构串联", "temporary_entries": [{"text": "共同电影安排特别期待时想先说清期待", "kind_hint": "tentative_intent", "scope": "特别期待的共同安排", "origin_refs": [f"{events[0]['record_id']}@1"], "origin_kind": "experience", "status": "open"}]}
        elif request.role == "persona_revision":
            persona = next(row for row in sources if row["record_kind"] == "persona_version")
            states = [row for row in sources if row["record_kind"] == "temporary_state"]
            searches = [row for row in sources if row["record_kind"] == "cognitive_run" and row["payload"].get("role") == "counterexample_search"]
            patch = PersonaPatch(base_revision=persona["revision"], entry_id="P03", old_hash=persona["payload"]["entry_hashes"]["P03"],
                                 replacement="只在特别期待的共同安排上，尝试清楚表达期待，并允许对方不同意。",
                                 rationale="独立交流支持小范围尝试，离线fixture仅验证提交协议。", evidence_refs=[f"{row['record_id']}@1" for row in events],
                                 temporary_refs=[f"{row['record_id']}@{row['revision']}" for row in states], counter_search_refs=[f"{row['record_id']}@1" for row in searches])
            value = {"decision": "propose", "reason": "离线局部修订接口串联", "patch": patch.model_dump(mode="json")}
        else:
            value = {"decision": "accept", "reason": "离线结构审查：仅P03且来源齐备", "scope_ok": True, "counterexamples_checked": True}
        return ModelResponse(content=json.dumps(value, ensure_ascii=False), provider="fixture", model="scripted-cognition-v1")


def test_scripted_model_jobs_commit_local_patch_and_persistent_consolidation(tmp_path):
    async def exercise():
        provider = ScriptedCognition()
        app = Application(tmp_path, provider=provider)
        initial = app.persona.read_state()
        await app.conversation.respond("今天约好一起看电影，因为安排变化取消了。", message_id="first")
        await app.conversation.respond("后来重新约定一起看电影，你提前说清期待让我安心。", message_id="second")
        await app.drain()
        assert_jobs_completed(app)
        roles = {request.role for request in provider.requests}
        assert {"reflection", "temporary_state", "persona_revision", "reviewer"} <= roles
        current = app.persona.read_state()
        assert current.revision == 2
        assert app.persona.diff(1, 2).keys() == {"P03"}
        assert current.payload["entry_hashes"]["P01"] == initial.payload["entry_hashes"]["P01"]
        states = app.states.list()
        assert len(states) == 1
        assert states[0].payload["status"] == "consolidated"
        change = app.store.get_record(states[0].payload["persona_change_ref"].split("@")[0])
        assert change.record_kind == "persona_change"
        assert len(change.payload["event_roots"]) == 2
        remembered = app.recall.recall("独立交流小范围尝试", filters={"kinds": ["persona_change"]}, budget=5000)
        assert change.ref in {record.ref for record in remembered.records}
        assert any(record.record_kind == "event" for record in remembered.records)
        assert any(record.record_kind == "raw_message" and record.payload["role"] == "user" for record in remembered.records)
        for kinds in (["persona_change"], ["persona_change", "event"]):
            why = app.recall.recall("为什么更愿意表达期待", filters={"kinds": kinds}, budget=10000)
            assert change.ref in {record.ref for record in why.records}
        Compactor(app.store).compact()
        restored = Application(tmp_path)
        assert restored.persona.read_state().revision == 2
        assert restored.states.list()[0].payload["status"] == "consolidated"
        assert ActivationSelector(restored.store).select_active_entries("共同电影安排期待")[0] == []
        assert len(restored.store.list_records("event")) == 2
        assert restored.store.verify_archive() == []
    asyncio.run(exercise())
