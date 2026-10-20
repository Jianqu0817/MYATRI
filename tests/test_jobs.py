import asyncio
from datetime import datetime, timedelta, timezone
import json

import pytest

from myatri.contracts import JobSpec
from myatri.runtime.jobs import JobQueue, LostLease
from myatri.runtime.worker import Worker
from myatri.runtime.scheduler import Scheduler


def test_idempotency_lease_recovery_and_result_reuse(tmp_path):
    queue = JobQueue(tmp_path / "runtime.sqlite3")
    spec = JobSpec(role="reflection", input_refs=["e1@1"])
    job_id = queue.enqueue(spec, now=0)
    assert queue.enqueue(spec, now=1) == job_id
    job = queue.lease_job("old", lease_seconds=10, now=1)
    queue.save_result(job_id, "old", {"proposal": "already-generated"}, now=2)
    recovered = queue.lease_job("new", now=12)
    assert recovered["id"] == job_id and json.loads(recovered["result"])["proposal"] == "already-generated"
    with pytest.raises(LostLease): queue.finish(job_id, "old", now=12)
    queue.finish(job_id, "new", now=13)
    assert queue.list_jobs()[0]["status"] == "succeeded"
    assert JobQueue(tmp_path / "runtime.sqlite3", user_id="other").list_jobs() == []


async def test_worker_saves_result_before_apply_and_restart_does_not_regenerate(tmp_path):
    queue = JobQueue(tmp_path / "runtime.sqlite3")
    queue.enqueue(JobSpec(role="slow"))
    calls = []
    async def generate(spec):
        calls.append("generation")
        await asyncio.sleep(.02)
        return {"value": "durable"}
    async def apply(result):
        assert queue.list_jobs()[0]["result"] is not None
        calls.append("apply")
        raise RuntimeError("simulated publish interruption")
    worker = Worker(queue, {"slow": generate}, apply)
    assert await worker.run_once()
    assert calls == ["generation", "apply"]
    with queue.db() as db:
        db.execute("UPDATE jobs SET available=0")
    async def complete(result):
        assert result == {"value": "durable"}
        calls.append("completed")
    assert await Worker(queue, {"slow": generate}, complete).run_once()
    assert calls == ["generation", "apply", "completed"]


def test_scheduler_cross_midnight_missed_windows_collapse(tmp_path):
    queue = JobQueue(tmp_path / "runtime.sqlite3")
    scheduler = Scheduler(queue)
    before = datetime(2026, 10, 19, 17, 0, tzinfo=timezone.utc)  # local 01:00
    queue.set_meta("last_scheduled", before.isoformat())
    after = before + timedelta(hours=50)
    jobs = scheduler.tick(now=after, dirty_refs=["e1@1"], last_activity=before, review_refs=["s1@1"])
    assert len(jobs) == 2
    scheduler.tick(now=after+timedelta(hours=6), dirty_refs=["e1@1"], last_activity=before, review_refs=["s1@1"])
    assert len(queue.list_jobs()) == 2
    assert all(x["role"] in {"cycle", "temporary_review"} for x in queue.list_jobs())
    with pytest.raises(ValueError): scheduler.tick(now=datetime(2026, 10, 20))
