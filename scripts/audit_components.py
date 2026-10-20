"""Read-only application audit using temporary stores and offline providers.

These probes describe current limitations, not successful business acceptance.
No credentials, existing user archives, downloads, or network are accessed.
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import tempfile

from myatri.app import Application
from myatri.cognition.experience import ExperienceOrganizer
from myatri.cognition.reflection import ReflectionAgent
from myatri.contracts import JobSpec, ModelRequest, ModelResponse, TemporaryEntry
from myatri.conversation.context import ContextBuilder
from myatri.persona.state import PersonaState
from myatri.persona.temporary import TemporaryStates
from myatri.providers import BudgetExceeded, FixtureProvider, Gateway
from myatri.retrieval import RecallService
from myatri.runtime.commit import Committer
from myatri.runtime.jobs import JobQueue
from myatri.runtime.scheduler import Scheduler
from myatri.storage import ArchiveStore


async def add_event(store, gateway, text, key, reality="reported"):
    raw = store.append_message("user", text, message_id=key)
    proposal = await ExperienceOrganizer(store, gateway).propose(raw, fixture={"events": [{
        "summary": text, "quote": text, "event_key": key, "occurred_at": None,
        "reality_scope": reality, "participants": []}]})
    Committer(store).submit_proposal(proposal)
    return next(r for r in proposal.records if r.record_kind == "event")


async def audit(root):
    results = []
    # A deterministic application branch probe, not a Leiden quality experiment.
    app = Application(root / "themes")
    app.index.themes = {f"t{i}": {"members": [f"e{i}@1"], "material_hash": str(i),
                                  "needs_summary": i == 8} for i in range(9)}
    scheduled = await app._cycle(JobSpec(role="cycle"))
    themes = [x for x in scheduled["jobs"] if x["role"] == "theme"]
    results.append({"id": "A01", "confirmed": not themes,
                    "observation": {"pending_theme": "t8", "theme_jobs": len(themes)},
                    "method": "controlled branch input; no clustering claim"})

    queue = JobQueue(root / "schedule.sqlite3")
    clock = datetime(2026, 10, 20, tzinfo=timezone.utc)
    scheduler = Scheduler(queue)
    first = scheduler.tick(now=clock, dirty_refs=["e1@1"], review_refs=["s1@1"], last_activity=clock-timedelta(hours=2))
    for _ in first:
        job = queue.lease_job("audit", now=clock.timestamp())
        queue.finish(job["id"], "audit", now=clock.timestamp()+1)
    scheduler.tick(now=clock+timedelta(hours=4), dirty_refs=["e1@1", "e2@1"], review_refs=["s1@1"], last_activity=clock)
    reviews = [j for j in queue.list_jobs() if j["role"] == "temporary_review"]
    old_meta = queue.get_meta("last_scheduled")
    scheduler.tick(now=clock+timedelta(hours=4, seconds=1), dirty_refs=["e1@1", "e2@1"],
                   review_refs=["s1@1"], last_activity=clock)
    results.append({"id": "A02", "confirmed": len(reviews) == 1 and reviews[0]["status"] == "succeeded",
                    "observation": {"reviews_after_new_evidence": len(reviews), "old_review_status": reviews[0]["status"],
                                    "idle_rewrites_schedule_each_tick": old_meta != queue.get_meta("last_scheduled")},
                    "scope": "due-review key unchanged; ordinary new-event cycle can still review states"})

    store = ArchiveStore(root / "context")
    PersonaState(store).initialize()
    fixture = Gateway(FixtureProvider(), daily_token_limit=10_000_000)
    event = await add_event(store, fixture, "明天去月球散步", "fiction", "fictional")
    # In this controlled example the explicit fictional scope is in the typed
    # payload; the literal utterance alone does not repeat that annotation.
    messages, _ = ContextBuilder(store, RecallService(store)).build_context("月球散步")
    material = messages[2]["content"]
    results.append({"id": "A03", "confirmed": event.ref in material and "fictional" not in material,
                    "observation": {"event_recalled": event.ref in material, "reality_scope_in_recall_context": "fictional" in material},
                    "scope": "model could use read_record; primary context projection omits typed payload"})

    entry = TemporaryEntry(text="到期再考虑", origin_refs=[event.ref], origin_kind="experience",
                           review_at="2026-10-20")
    try:
        datetime.fromisoformat(entry.review_at) <= datetime.now(timezone.utc)
        naive_error = False
    except TypeError:
        naive_error = True
    results.append({"id": "A04", "confirmed": naive_error,
                    "observation": {"contract_accepts_naive_review_at": True, "background_due_comparison_raises_TypeError": naive_error}})

    action_app = Application(root / "action", provider=FixtureProvider(responses=[{"content": "我们先定个时间吗？"}]))
    external = await add_event(action_app.store, action_app.gateway, "共同安排常常变动", "arrangement")
    action_app.states.create(TemporaryEntry(text="共同安排先定时间", origin_refs=[external.ref]), entry_id="intent")
    reply = await action_app.conversation.respond("共同安排先定时间", message_id="talk")
    results.append({"id": "A05", "confirmed": not action_app.store.list_records("behavior_attempt"),
                    "observation": {"assistant_persisted": reply.ref, "attempt_records": len(action_app.store.list_records("behavior_attempt"))},
                    "scope": "no assertion that this utterance automatically proves an action; missing attribution stage"})

    large = ArchiveStore(root / "large")
    PersonaState(large).initialize()
    refs = []
    for i in range(28):
        row = await add_event(large, fixture, f"第{i}件独立安排。" + "记录共同活动及不同的安排。" * 20, f"large{i}")
        refs.append(row.ref)
    calls_before = len(fixture.provider.requests)
    try:
        await ReflectionAgent(large, fixture).propose(refs)
        blocked = False
    except BudgetExceeded:
        blocked = True
    results.append({"id": "A06", "confirmed": blocked,
                    "observation": {"event_count": len(refs), "reflection_budget_blocked": blocked,
                                    "provider_requests": len(fixture.provider.requests)-calls_before},
                    "scope": "genuine request-size guard, no real model call or quality claim"})

    class UsageProvider:
        async def generate(self, request):
            return ModelResponse(content="ok", provider="audit", model="offline", usage={"total_tokens": 900})
    daily = JobQueue(root / "budget.sqlite3")
    gates = [Gateway(UsageProvider(), daily_token_limit=1100, usage_sink=daily.log_usage) for _ in range(2)]
    for gate in gates:
        await gate.generate(ModelRequest(messages=[{"role": "user", "content": "hi"}], max_tokens=1))
    charged = sum(row["charged_tokens"] for row in daily.usage())
    results.append({"id": "A07", "confirmed": charged > 1100,
                    "observation": {"two_instances_charged_tokens": charged, "per_instance_daily_limit": 1100},
                    "scope": "independent gateway instances; not a billing API experiment"})
    return {"mode": "offline-temporary-stores", "paid_calls": 0,
            "production_code_modified": False, "findings": results}


if __name__ == "__main__":
    with tempfile.TemporaryDirectory(prefix="myatri_component_audit_") as temporary:
        report = asyncio.run(audit(Path(temporary)))
    destination = Path(__file__).resolve().parents[1] / "reports" / "component_review.json"
    destination.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
