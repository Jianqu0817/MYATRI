"""Read-only runtime audit; writes synthetic archives only under its own temp directory."""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import tempfile
import time

from myatri.app import Application
from myatri.cognition.experience import ExperienceOrganizer
from myatri.cognition.reflection import ReflectionAgent
from myatri.contracts import JobSpec, ModelRequest, ModelResponse, TemporaryEntry
from myatri.providers import BudgetExceeded, FixtureProvider, Gateway
from myatri.runtime.commit import Committer
from myatri.runtime.jobs import JobQueue
from myatri.runtime.scheduler import Scheduler


async def add_event(app, text, key):
    raw = app.store.append_message("user", text, message_id=key)
    proposal = await ExperienceOrganizer(app.store, app.gateway).propose(raw, fixture={"events": [{
        "summary": text, "quote": text, "event_key": key, "occurred_at": None,
        "reality_scope": "reported", "participants": []}]})
    Committer(app.store).submit_proposal(proposal)
    return next(r for r in proposal.records if r.record_kind == "event")


async def main(root):
    output = {"paid_calls": 0, "production_code_modified": False}
    app = Application(root / "synthetic")
    app.index.themes = {f"t{i}": {"members": [f"e{i}@1"], "material_hash": str(i),
                                  "needs_summary": i == 8} for i in range(9)}
    scheduled = await app._cycle(JobSpec(role="cycle"))
    output["A01"] = {"theme_jobs": len([x for x in scheduled["jobs"] if x["role"] == "theme"]),
                      "waiting_theme": "t8"}
    app.index.themes = {}

    queue = JobQueue(root / "schedule.sqlite3")
    clock = datetime(2026, 10, 20, tzinfo=timezone.utc)
    scheduler = Scheduler(queue)
    first = scheduler.tick(now=clock, dirty_refs=["e1@1"], review_refs=["s1@1"],
                           last_activity=clock - timedelta(hours=2))
    for _ in first:
        job = queue.lease_job("audit", now=clock.timestamp())
        queue.finish(job["id"], "audit", now=clock.timestamp() + 1)
    scheduler.tick(now=clock + timedelta(hours=4), dirty_refs=["e1@1", "e2@1"],
                   review_refs=["s1@1"], last_activity=clock)
    old_meta = queue.get_meta("last_scheduled")
    scheduler.tick(now=clock + timedelta(hours=4, seconds=1), dirty_refs=["e1@1", "e2@1"],
                   review_refs=["s1@1"], last_activity=clock)
    reviews = [j for j in queue.list_jobs() if j["role"] == "temporary_review"]
    output["A02"] = {"reviews_after_new_evidence": len(reviews), "old_review_status": reviews[0]["status"],
                      "idle_rewrites_meta": old_meta != queue.get_meta("last_scheduled")}

    refs = []
    for i in range(28):
        event = await add_event(app, f"第{i}件独立安排。" + "记录共同活动及不同的安排。" * 20, f"large{i}")
        refs.append(event.ref)
    app.states.create(TemporaryEntry(text="到期再考虑", origin_refs=[refs[0]], review_at="2026-10-20"), entry_id="due")
    try:
        await asyncio.wait_for(app.run_background(), timeout=1)
    except TypeError as exc:
        output["A04"] = {"real_background_exception": type(exc).__name__, "message": str(exc)}
    except TimeoutError:
        output["A04"] = {"real_background_exception": None}

    class OfflineLivePathProvider:
        name = "offline-audit-nonfixture"
        def __init__(self):
            self.calls = 0
        async def generate(self, request):
            self.calls += 1
            return ModelResponse(content='{"events":[]}', provider="offline-audit", model="none")

    provider = OfflineLivePathProvider()
    livepath = Gateway(provider, daily_token_limit=10_000_000)
    pending = app.store.append_message("user", "新增经历：今天散步了。", message_id="new")
    try:
        await ExperienceOrganizer(app.store, livepath).propose(pending)
    except BudgetExceeded as exc:
        output["A06_A1"] = {"event_count": len(refs), "exception": str(exc), "provider_calls": provider.calls}
    try:
        await ReflectionAgent(app.store, livepath).propose(refs)
    except BudgetExceeded as exc:
        output["A06_A5"] = {"event_count": len(refs), "exception": str(exc), "provider_calls": provider.calls}

    # The provider and pipeline here are the actual default TF-IDF/Leiden path.
    # The 1 ms ticker is a runnable concurrent UI/heartbeat surrogate, with no mocks.
    ticks = []
    async def ticker():
        while True:
            ticks.append(time.perf_counter())
            await asyncio.sleep(.001)
    timer = asyncio.create_task(ticker())
    await asyncio.sleep(.01)
    before = len(ticks)
    started = time.perf_counter()
    await app.index.rebuild()
    elapsed = time.perf_counter() - started
    after = len(ticks)
    timer.cancel()
    try:
        await timer
    except asyncio.CancelledError:
        pass
    output["R01_event_loop_blocking"] = {"event_count": len(refs), "index_seconds": round(elapsed, 4),
                                         "concurrent_ticker_advances": after - before,
                                         "timer_started": before > 0, "backend": "real-default-TFIDF-Leiden"}

    class UsageProvider:
        async def generate(self, request):
            return ModelResponse(content="ok", provider="offline-audit", model="none", usage={"total_tokens": 900})
    shared = JobQueue(root / "budget.sqlite3")
    gates = [Gateway(UsageProvider(), daily_token_limit=1100, usage_sink=shared.log_usage) for _ in range(2)]
    await asyncio.gather(*[gate.generate(ModelRequest(messages=[{"role": "user", "content": "hi"}], max_tokens=1)) for gate in gates])
    output["A07"] = {"shared_charged_tokens": sum(x["charged_tokens"] for x in shared.usage()), "per_gateway_limit": 1100}
    return output


if __name__ == "__main__":
    reports = Path(__file__).resolve().parent
    with tempfile.TemporaryDirectory(prefix="review_runtime_probe_20261020_", dir=reports) as temporary:
        print(json.dumps(asyncio.run(main(Path(temporary))), ensure_ascii=False, indent=2))
