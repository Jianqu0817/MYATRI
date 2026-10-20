import json
from types import SimpleNamespace

import pytest

from myatri.app import Application
from myatri.cognition.association import AssociationAgent
from myatri.cognition.experience import ExperienceOrganizer, IngestProgressPending, source_windows
from myatri.cognition.materials import json_bytes, select_materials
from myatri.cognition.persona_revision import PersonaRevisionAgent
from myatri.cognition.reflection import ReflectionAgent
from myatri.cognition.reviewer import Reviewer
from myatri.cognition.tasks import cognitive_call
from myatri.cognition.temporary_state import TemporaryStateAgent
from myatri.cognition.theme import ThemeAgent
from myatri.contracts import Event, PersonaPatch, Record, SourceSpan, digest
from myatri.providers import Gateway
from myatri.runtime.commit import Committer


def seed_events(store, count):
    batch, events = [], []
    for i in range(count):
        text = f"第{i}件独立共同安排。" + "安排改变时也应保存不同意见及反例。" * 24
        raw = Record(record_id=f"raw_{i}", record_kind="raw_message", body_markdown=text, payload={"role": "user"})
        event = Event(fact_summary=text, event_fingerprint=digest(i), reality_scope="reported",
                      source_spans=[SourceSpan(message_ref=raw.ref, start=0, end=len(text), quote=text)])
        record = Record(record_id=f"event_{i}", record_kind="event", source_refs=[raw.ref],
                        body_markdown=text, payload=event.model_dump(mode="json"))
        batch.extend([raw, record])
        events.append(record)
    store.commit(batch, "seed-events")
    return events


class OfflineProvider:
    name = "offline-nonfixture"
    def __init__(self, fail_once_on=None):
        self.requests = []
        self.fail_once_on = fail_once_on

    async def generate(self, request):
        from myatri.contracts import ModelResponse
        self.requests.append(request.model_copy(deep=True))
        if self.fail_once_on == len(self.requests):
            raise RuntimeError("synthetic interruption")
        data = {"decision": "defer", "reason": "材料仅供有限审查，不作自动人格晋升。"}
        if request.role == "association":
            data["edges"] = []
        if request.role == "experience":
            material = json.loads(request.messages[1]["content"])
            text = material["message"]["text"]
            quote = "末尾唯一事件：今天去了海边。"
            data = {"events": ([{"summary": "今天去了海边", "quote": quote, "event_key": "late-seaside",
                                  "occurred_at": None, "reality_scope": "reported"}] if quote in text else [])}
        return ModelResponse(content=json.dumps(data, ensure_ascii=False), provider=self.name, model="offline-v1")


@pytest.mark.parametrize("count", [28, 96])
async def test_a1_and_all_cognitive_roles_enter_provider_with_bounded_pinned_materials(tmp_path, count):
    app = Application(tmp_path)
    events = seed_events(app.store, count)
    refs = [r.ref for r in events]
    provider = OfflineProvider()
    gateway = Gateway(provider, daily_token_limit=10_000_000)
    message = app.store.append_message("user", "新增短消息：今天去了公园。", message_id="new")
    proposal = await ExperienceOrganizer(app.store, gateway).propose(message)
    Committer(app.store).submit_proposal(proposal)
    assert proposal.records[0].payload["source_coverage"]["complete"]
    reflection = await ReflectionAgent(app.store, gateway).propose(refs)
    temporary = await TemporaryStateAgent(app.store, gateway).propose(refs)
    _, revision = await PersonaRevisionAgent(app.store, gateway).propose([app.persona.read_state().ref, *refs])
    graph = SimpleNamespace(edges=[{"from_ref": refs[i], "to_ref": refs[i+1], "type": "similar"} for i in range(count-1)])
    association = await AssociationAgent(app.store, gateway, SimpleNamespace(graph=graph)).propose(refs)
    index = SimpleNamespace(themes={"t": {"members": refs, "material_hash": "seed", "cluster_id": "c", "memberships": {}}},
                            theme_materials=lambda _: {"counter_refs": []})
    theme = await ThemeAgent(app.store, gateway, index).propose("t")
    assert {r.role for r in provider.requests} == {"experience", "reflection", "temporary_state", "persona_revision", "association", "theme"}
    for request in provider.requests:
        assert json_bytes(request.model_dump(mode="json")) + request.max_tokens <= request.budget_tokens
    for result in (reflection, temporary, revision, association, theme):
        run = result.records[0]
        assert len(run.source_refs) <= 12
        assert run.payload["materials"]["omitted_count"] > 0
        assert set(run.source_refs) == set(run.payload["materials"]["selected_refs"])
        for ref in run.source_refs:
            assert ref == app.store.get_record(ref.split("@")[0]).ref


async def test_empty_material_locally_defers_without_model_or_generated_state(tmp_path):
    app = Application(tmp_path)
    provider = OfflineProvider()
    proposal = await TemporaryStateAgent(app.store, Gateway(provider)).propose([])
    assert proposal.records[0].payload["decision"] == "defer"
    assert proposal.records[0].payload["provider"] == "local-policy"
    assert not provider.requests
    assert not app.states.list()


async def test_long_raw_windows_checkpoint_resume_and_keep_absolute_quote_positions(tmp_path):
    app = Application(tmp_path)
    text = "前置说明与旧资料。" * 1600 + "末尾唯一事件：今天去了海边。"
    raw = app.store.append_message("user", text, message_id="long-raw")
    windows = list(source_windows(text))
    assert len(windows) > 8
    assert windows[0][0] == 0 and windows[-1][1] == len(text)
    assert all(left[1] >= right[0] for left, right in zip(windows, windows[1:]))
    provider = OfflineProvider()
    organizer = ExperienceOrganizer(app.store, Gateway(provider, daily_token_limit=10_000_000))
    with pytest.raises(IngestProgressPending) as pending:
        await organizer.propose(raw)
    assert pending.value.reason == "ingest_pending"
    assert len(provider.requests) == 8
    assert not [r for r in app.store.list_records("cognitive_run") if r.payload.get("role") == "A1"]
    assert not app.store.list_records("event")
    # Reconstruct both application and organizer: progress is in the authority,
    # not in process-local state or a remembered provider request list.
    app = Application(tmp_path)
    organizer = ExperienceOrganizer(app.store, Gateway(provider, daily_token_limit=10_000_000))
    proposal = await organizer.propose(raw)
    Committer(app.store).submit_proposal(proposal)
    assert len(provider.requests) == len(windows)
    events = app.store.list_records("event")
    assert len(events) == 1
    span = events[0].payload["source_spans"][0]
    assert span["start"] == text.index("末尾唯一事件：今天去了海边。")
    assert text[span["start"]:span["end"]] == span["quote"]
    assert app.store.get_record(raw.record_id).body_markdown == text
    for request in provider.requests:
        assert json_bytes(request.model_dump(mode="json")) + request.max_tokens <= request.budget_tokens


async def test_a1_interrupted_second_window_does_not_repay_saved_first_window(tmp_path):
    app = Application(tmp_path)
    raw = app.store.append_message("user", "很长的说明。" * 500 + "末尾唯一事件：今天去了海边。", message_id="resume")
    provider = OfflineProvider(fail_once_on=2)
    organizer = ExperienceOrganizer(app.store, Gateway(provider, daily_token_limit=10_000_000))
    with pytest.raises(RuntimeError, match="interruption"):
        await organizer.propose(raw)
    proposal = await organizer.propose(raw)
    Committer(app.store).submit_proposal(proposal)
    starts = [json.loads(request.messages[1]["content"])["source_window"]["start"] for request in provider.requests]
    assert starts.count(0) == 1
    assert len(app.store.list_records("event")) == 1


def test_selection_pins_old_revision_marks_excerpts_and_reserves_counterevidence(tmp_path):
    app = Application(tmp_path)
    events = seed_events(app.store, 28)
    from myatri.contracts import Edge, TemporaryEntry
    state = app.states.create(TemporaryEntry(text="暂时希望再讨论安排", origin_refs=[events[0].ref]), entry_id="intent")
    app.states.review("intent", base_revision=1, text="新的想法", reason="新材料")
    edge = Edge(edge_id="counter", from_ref=events[0].ref, to_ref=events[-1].ref, type="contradicts",
                evidence_refs=[events[0].ref, events[-1].ref])
    app.store.commit([Record(record_id="counter", record_kind="edge", source_refs=edge.evidence_refs,
                             payload=edge.model_dump(mode="json"))], "counter")
    selection = select_materials(app.store, [state.ref, *[r.ref for r in events]], required_refs=[state.ref])
    assert selection.sources[0].ref == "intent@1"
    assert {events[0].ref, events[-1].ref} <= {r.ref for r in selection.sources}
    assert selection.omitted_count > 0 and selection.limitations
    excerpt = select_materials(app.store, [events[0].ref], max_record_bytes=700).material[0]
    assert not excerpt["complete"]
    assert events[0].body_markdown.startswith(excerpt["text"])


async def test_reviewer_never_accepts_when_all_required_evidence_cannot_fit(tmp_path):
    app = Application(tmp_path)
    events = seed_events(app.store, 28)
    persona = app.persona.read_state()
    patch = PersonaPatch(base_revision=1, entry_id="P03", old_hash=digest(persona.payload["entries"]["P03"]),
                         replacement="共同安排中先表达自己的期待", rationale="需要审查",
                         evidence_refs=[r.ref for r in events])
    provider = OfflineProvider()
    data, proposal, _ = await Reviewer(app.store, Gateway(provider)).review(patch)
    assert data["decision"] == "defer"
    assert not data["scope_ok"] and not data["counterexamples_checked"]
    assert proposal.records[0].payload["materials"]["missing_required"]
    assert not provider.requests


async def test_overlapping_source_windows_do_not_create_two_roots_even_if_model_keys_differ(tmp_path):
    app = Application(tmp_path)
    quote = "末尾唯一事件：今天去了海边。"
    text = "铺" * 1130 + quote + "余" * 500
    windows = list(source_windows(text))
    assert sum(quote in fragment for _, _, fragment in windows) == 2

    class OverlapProvider(OfflineProvider):
        async def generate(self, request):
            response = await super().generate(request)
            data = json.loads(response.content)
            for event in data["events"]:
                event["event_key"] = f"window-{len(self.requests)}"
            response.content = json.dumps(data, ensure_ascii=False)
            return response

    raw = app.store.append_message("user", text, message_id="overlapping")
    provider = OverlapProvider()
    proposal = await ExperienceOrganizer(app.store, Gateway(provider)).propose(raw)
    Committer(app.store).submit_proposal(proposal)
    events = app.store.list_records("event")
    assert len(events) == 1
    assert events[0].payload["source_spans"][0]["start"] == text.index(quote)
    assert app.store.verify_archive() == []


async def test_model_key_collision_is_not_global_identity_and_explicit_shown_merge_still_works(tmp_path):
    from myatri.contracts import ModelResponse
    app = Application(tmp_path)

    class KeyProvider(OfflineProvider):
        existing_ref = None

        async def generate(self, request):
            self.requests.append(request.model_copy(deep=True))
            payload = json.loads(request.messages[1]["content"])
            text = payload["message"]["text"]
            value = {"events": [{"summary": text, "quote": text, "event_key": "generic-arrangement",
                                  "occurred_at": None, "reality_scope": "reported",
                                  "existing_event_ref": self.existing_ref}]}
            return ModelResponse(content=json.dumps(value, ensure_ascii=False), provider=self.name, model="keys-v1")

    provider = KeyProvider()
    organizer = ExperienceOrganizer(app.store, Gateway(provider))
    for i, text in enumerate(("今天去了海边。", "后来又去了公园。")):
        raw = app.store.append_message("user", text, message_id=f"collision-{i}")
        Committer(app.store).submit_proposal(await organizer.propose(raw))
    events = app.store.list_records("event")
    assert len(events) == 2
    provider.existing_ref = events[0].ref
    raw = app.store.append_message("user", "再说说那次去了海边。", message_id="explicit-repeat")
    Committer(app.store).submit_proposal(await organizer.propose(raw))
    assert len(app.store.list_records("event")) == 2
    repeated = app.store.list_records("interpretation")
    assert len(repeated) == 1 and repeated[0].payload["event_refs"] == [events[0].ref]
    assert app.store.verify_archive() == []
