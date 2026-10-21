"""Recovery of poisoned maintenance cutoffs, entirely offline."""
import json

import pytest

from myatri.app import Application
from myatri.cognition.experience import ExperienceOrganizer
from myatri.providers import Gateway
from myatri.runtime.commit import Committer
from myatri.storage import ArchiveStore
from myatri.contracts import JobSpec, ModelResponse
from myatri.runtime.jobs import JobQueue
from test_group_memory_sources import extraction, group_message
from test_turn_maintenance import BatchProvider, CONFIG


def add_pair(app, name):
    message = app.store.append_message("user", "普通闲聊", name)
    app.store.append_message("assistant", "嗯。", name + "_reply", reply_to=message.ref)
    return message


async def fail_three(app):
    for _ in range(3):
        with app.queue.db() as db:
            db.execute("UPDATE jobs SET available=0")
        assert await app.worker.run_once()
    assert app.queue.list_jobs()[0]["status"] == "failed"
    assert app.queue.list_jobs()[0]["attempts"] == 3


async def test_failed_cutoff_retries_same_task_once_after_upgrade(tmp_path):
    provider = BatchProvider()
    provider.fail_memory = True
    app = Application(tmp_path, provider=provider, config={**CONFIG, "cognition": {"maintenance_turns": 1}})
    first = add_pair(app, "first")
    job_id = app.maintenance.schedule(force=True)
    await fail_three(app)
    provider.fail_memory = False
    resumed = Application(tmp_path, provider=provider, config={**CONFIG, "cognition": {"maintenance_turns": 1}})
    assert resumed.maintenance.schedule(force=True) == job_id
    assert await resumed.worker.run_once()
    assert len(resumed.queue.list_jobs()) == 1
    assert resumed.queue.list_jobs()[0]["status"] == "succeeded"
    assert resumed.queue.get_meta("maintenance_cursor") == first.ref
    assert resumed.store.verify_archive() == []


async def test_exhausted_cutoff_is_deferred_new_turns_work_and_manual_retry_keeps_cursor(tmp_path):
    provider = BatchProvider()
    provider.fail_memory = True
    app = Application(tmp_path, provider=provider, config={**CONFIG, "cognition": {"maintenance_turns": 1}})
    first = add_pair(app, "first")
    job_id = app.maintenance.schedule(force=True)
    await fail_three(app)
    assert app.maintenance.schedule(force=True) == job_id
    assert await app.worker.run_once()
    assert app.queue.list_jobs()[0]["attempts"] == 4
    assert app.maintenance.schedule(force=True) is None
    assert app.maintenance.schedule(force=True) is None
    assert len(provider.requests) == 4
    deferred = app.queue.get_meta("maintenance_deferred_batches")[job_id]
    assert deferred["status"] == "deferred" and deferred["input_refs"] == [first.ref]
    assert app.queue.get_meta("maintenance_cursor") is None
    second = add_pair(app, "second")
    provider.fail_memory = False
    assert app.maintenance.schedule(force=True) != job_id
    assert await app.worker.run_once()
    assert app.queue.get_meta("maintenance_cursor") == second.ref
    with pytest.raises(ValueError, match="deferred source"):
        await app.maintenance.before_compact()
    app.queue.retry_job(job_id)
    assert await app.worker.run_once()
    assert app.queue.get_meta("maintenance_cursor") == second.ref
    assert app.queue.get_meta("maintenance_deferred_batches")[job_id]["status"] == "recovered"
    assert app.store.get_record(first.record_id) == first
    assert app.store.verify_archive() == []


class MixedAttribution(BatchProvider):
    async def generate(self, request):
        if request.purpose not in {"A1_batch", "A1"}:
            return await super().generate(request)
        self.requests.append(request)
        payload = json.loads(request.messages[-1]["content"])
        ref = payload["messages"][0]["ref"] if request.purpose == "A1_batch" else None
        good = extraction()["events"][0]
        bad = {**good, "participants": ["invented_member"]}
        values = [good, bad]
        if ref:
            values = [{**value, "message_ref": ref} for value in values]
        from myatri.contracts import ModelResponse
        return ModelResponse(content=json.dumps({"events": values}, ensure_ascii=False),
                             provider=self.name, model="offline")


@pytest.mark.parametrize("batched", [False, True])
async def test_bad_identity_candidate_is_quarantined_without_discarding_valid_peer(tmp_path, batched):
    store = ArchiveStore(tmp_path, agent_id="xiaowennuan", user_id="group")
    provider = MixedAttribution()
    organizer = ExperienceOrganizer(store, Gateway(provider))
    commit = Committer(store).submit_proposal
    message = group_message(store)
    if batched:
        await organizer.organize_batch([message], commit)
    else:
        commit(await organizer.propose(message))
    events = store.list_records("event")
    assert len(events) == 1 and events[0].payload["participants"] == ["member_a"]
    runs = store.list_records("cognitive_run")
    checkpoint = next(row for row in runs if row.payload["role"] in {"A1_batch", "A1_chunk"})
    rejected = checkpoint.payload["rejected_candidates"]
    assert len(rejected) == 1 and rejected[0]["reason_code"] == "unknown_participant"
    assert rejected[0]["candidate"]["participants"] == ["invented_member"]
    assert rejected[0]["message_ref"] == message.ref and rejected[0]["status"] == "unconfirmed"
    run = next(row for row in runs if row.payload["role"] == "A1")
    assert run.payload["source_coverage"]["complete"] is True
    assert run.payload["source_coverage"]["validation_complete"] is False
    assert run.payload["source_coverage"]["quarantined_candidates"] == 1
    assert run.payload["quarantine_refs"] == [checkpoint.ref]
    await organizer.organize_batch([message], commit)
    assert len(provider.requests) == 1
    assert len(store.list_records("event")) == 1
    assert store.verify_archive() == []


def test_upgrade_recovery_is_durable_and_claimed_once_across_queue_instances(tmp_path):
    path = tmp_path / "jobs.sqlite3"
    first = JobQueue(path)
    job_id = first.enqueue(JobSpec(role="maintenance", input_refs=["raw@1"]), now=0)
    first.lease_job("worker", now=1)
    first.finish(job_id, "worker", "failed", "synthetic", now=2)
    assert first.retry_failed_once(job_id, "repair-v1", now=3)
    second = JobQueue(path)
    assert not second.retry_failed_once(job_id, "repair-v1", now=4)
    second.lease_job("worker", now=4)
    second.finish(job_id, "worker", "failed", "synthetic", now=5)
    assert not JobQueue(path).retry_failed_once(job_id, "repair-v1", now=6)
    assert first.list_jobs()[0]["attempts"] == 2


async def test_quarantine_survives_support_review_failure_without_repaying_extraction(tmp_path):
    class ReviewFailsOnce(MixedAttribution):
        async def generate(self, request):
            if request.purpose == "A1_support":
                self.requests.append(request)
                if sum(r.purpose == "A1_support" for r in self.requests) == 1:
                    raise ValueError("synthetic support unavailable")
                return ModelResponse(content=json.dumps({"checks": [{"index": 0, "verdict": "supported",
                    "reason": "原话支持"}]}, ensure_ascii=False), provider=self.name, model="offline")
            return await super().generate(request)

    store = ArchiveStore(tmp_path, agent_id="xiaowennuan", user_id="group")
    provider = ReviewFailsOnce()
    gateway = Gateway(provider)
    gateway.group_support_review = True
    organizer = ExperienceOrganizer(store, gateway)
    message = group_message(store)
    commit = Committer(store).submit_proposal
    with pytest.raises(ValueError, match="support unavailable"):
        await organizer.organize_batch([message], commit)
    assert not store.list_records("event")
    await organizer.organize_batch([message], commit)
    assert [r.purpose for r in provider.requests] == ["A1_batch", "A1_support", "A1_support"]
    assert len(store.list_records("event")) == 1
    run = next(r for r in store.list_records("cognitive_run") if r.payload["role"] == "A1")
    assert run.payload["source_coverage"]["quarantined_candidates"] == 1
    assert store.verify_archive() == []


async def test_maintenance_projects_quarantine_health_count_without_duplicate_charges(tmp_path):
    provider = MixedAttribution()
    app = Application(tmp_path, provider=provider,
                      config={**CONFIG, "cognition": {"maintenance_turns": 1}})
    message = group_message(app.store)
    app.store.append_message("assistant", "嗯。", "reply", reply_to=message.ref)
    app.maintenance.schedule(force=True)
    assert await app.worker.run_once()
    assert app.queue.list_jobs()[0]["status"] == "succeeded"
    counts = app.queue.get_meta("a1_quarantine_counts")
    assert len(counts) == 1 and sum(counts.values()) == 1
    run_ref = next(iter(counts))
    run_id, revision = run_ref.rsplit("@", 1)
    assert app.store.get_record(run_id, int(revision)).payload["source_coverage"]["validation_complete"] is False
    before = len(provider.requests)
    # Replay the same saved cutoff/checkpoints after a simulated cursor rollback.
    app.queue.set_meta("maintenance_cursor", None)
    await app.maintenance.run([message.ref])
    assert app.queue.get_meta("a1_quarantine_counts") == counts
    assert len(provider.requests) == before
