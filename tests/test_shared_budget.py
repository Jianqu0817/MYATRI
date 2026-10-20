"""Offline persistent budget and operator recovery checks; no provider network IO."""
import asyncio
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys

import httpx
import pytest

from myatri.contracts import JobSpec, ModelRequest, ModelResponse
from myatri.providers import BudgetExceeded, FixtureProvider, Gateway, ProviderError
from myatri.runtime.jobs import JobQueue


def estimate(request):
    return len(json.dumps(request.model_dump(mode="json"), ensure_ascii=False).encode("utf-8")) + request.max_tokens


def test_reservations_survive_restart_and_are_shared_between_domains(tmp_path):
    path = tmp_path / "runtime.sqlite3"
    first = JobQueue(path, agent_id="one", user_id="alice")
    reservation = first.reserve_budget("provider", 700, 1000, now=10)
    second = JobQueue(path, agent_id="two", user_id="bob")
    assert second.reserve_budget("provider", 400, 1000, now=11) is None
    second.settle_budget(reservation, 500)
    assert second.reserve_budget("provider", 500, 1000, now=12)
    assert first.reserve_budget("provider", 1, 1000, now=13) is None
    assert first.reserve_budget("different-account", 1000, 1000, now=13)


def test_expired_crash_reservation_is_not_refunded_and_late_usage_can_resolve(tmp_path):
    queue = JobQueue(tmp_path / "runtime.sqlite3")
    reservation = queue.reserve_budget("provider", 700, 1000, ttl_seconds=5, now=10)
    assert queue.budget_usage("provider", now=16) == {
        "day": "1970-01-01", "reserved_tokens": 0, "used_tokens": 700}
    assert queue.reserve_budget("provider", 301, 1000, now=16) is None
    queue.settle_budget(reservation, 600, now=17)
    queue.settle_budget(reservation, 600, now=18)  # Idempotent settlement.
    with pytest.raises(ValueError, match="immutable"):
        queue.settle_budget(reservation, 0, now=18)
    assert queue.budget_usage("provider", now=19)["used_tokens"] == 600


def test_unknown_settlement_cannot_discount_unconfirmed_usage(tmp_path):
    queue = JobQueue(tmp_path / "runtime.sqlite3")
    reservation = queue.reserve_budget("provider", 700, 1000, now=10)
    queue.settle_budget(reservation, now=11)
    queue.settle_budget(reservation, 0, status="unknown", now=12)
    assert queue.budget_usage("provider", now=13)["used_tokens"] == 700
    queue.settle_budget(reservation, 20, now=14)
    assert queue.budget_usage("provider", now=15)["used_tokens"] == 20


def test_utc_rollover_does_not_move_late_settlement_into_new_day(tmp_path):
    queue = JobQueue(tmp_path / "runtime.sqlite3")
    midnight = datetime(2026, 10, 21, tzinfo=timezone.utc).timestamp()
    reservation = queue.reserve_budget("provider", 1000, 1000, now=midnight - 1)
    assert queue.reserve_budget("provider", 1000, 1000, now=midnight + 1)
    queue.settle_budget(reservation, 900, now=midnight + 2)
    assert queue.budget_usage("provider", now=midnight - 1)["used_tokens"] == 900
    assert queue.budget_usage("provider", now=midnight + 3)["reserved_tokens"] == 1000
    assert queue.budget_usage("provider", now=midnight + 3)["used_tokens"] == 0


def test_legacy_usage_import_and_reservation_logs_do_not_double_charge(tmp_path):
    queue = JobQueue(tmp_path / "runtime.sqlite3")
    queue.log_usage({"day": "1970-01-01", "provider": "provider", "charged_tokens": 600})
    assert queue.budget_usage("provider", now=10)["used_tokens"] == 600
    assert queue.budget_usage("provider", now=11)["used_tokens"] == 600
    reservation = queue.reserve_budget("provider", 400, 1000, now=12)
    queue.settle_budget(reservation, 300)
    queue.log_usage({"day": "1970-01-01", "provider": "provider", "charged_tokens": 300,
                     "budget_reservation_id": reservation})
    assert queue.budget_usage("provider", now=13)["used_tokens"] == 900
    assert queue.reserve_budget("provider", 101, 1000, now=14) is None


def test_separate_processes_cannot_overreserve(tmp_path):
    path = tmp_path / "runtime.sqlite3"
    JobQueue(path)
    script = """
import sys
from pathlib import Path
from myatri.runtime.jobs import JobQueue
queue = JobQueue(Path(sys.argv[1]))
print('ready', flush=True)
input()
print('accepted' if queue.reserve_budget('shared', 600, 1000) else 'rejected', flush=True)
"""
    env = dict(os.environ, PYTHONPATH=str(Path(__file__).resolve().parents[1] / "src"))
    processes = [subprocess.Popen([sys.executable, "-c", script, str(path)],
                                 stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE, text=True, env=env) for _ in range(4)]
    try:
        for process in processes:
            assert process.stdout.readline().strip() == "ready"
        for process in processes:
            process.stdin.write("go\n")
            process.stdin.flush()
        outputs = [process.communicate(timeout=30) for process in processes]
        assert all(process.returncode == 0 for process in processes), outputs
        assert sum(output.strip() == "accepted" for output, _ in outputs) == 1
        assert JobQueue(path).budget_usage("shared")["reserved_tokens"] == 600
    finally:
        for process in processes:
            if process.poll() is None:
                process.kill()
                process.wait(timeout=10)


async def test_two_gateways_use_atomic_reservations_before_concurrent_io(tmp_path):
    path = tmp_path / "runtime.sqlite3"
    request = ModelRequest(messages=[], max_tokens=100)
    bound = estimate(request)
    providers = [FixtureProvider([{"content": "ok", "usage": {"total_tokens": bound}}], delay=.02)
                 for _ in range(2)]
    gateways = [Gateway(provider, budget_ledger=JobQueue(path, user_id=str(i)),
                        daily_token_limit=bound) for i, provider in enumerate(providers)]
    results = await asyncio.gather(*(gateway.generate(request) for gateway in gateways), return_exceptions=True)
    assert sum(isinstance(result, BudgetExceeded) for result in results) == 1
    assert sum(len(provider.requests) for provider in providers) == 1
    assert gateways[0].used_tokens == bound
    assert gateways[1].used_tokens == bound
    assert gateways[0].reserved_tokens == 0


async def test_independent_gateway_restarts_restore_settled_usage(tmp_path):
    path = tmp_path / "runtime.sqlite3"
    first = Gateway(FixtureProvider([{"content": "ok", "usage": {"total_tokens": 900}}]),
                    budget_ledger=JobQueue(path), daily_token_limit=1100)
    request = ModelRequest(messages=[{"role": "user", "content": "hi"}], max_tokens=1)
    await first.generate(request)
    provider = FixtureProvider()
    second = Gateway(provider, budget_ledger=JobQueue(path), daily_token_limit=1100)
    with pytest.raises(BudgetExceeded):
        await second.generate(request)
    assert second.used_tokens == 900 and not provider.requests


async def test_legacy_in_memory_gateway_keeps_midnight_attempts_on_original_day(monkeypatch):
    day = ["2026-10-20"]
    monkeypatch.setattr(Gateway, "_utc_day", staticmethod(lambda now=None: day[0]))
    provider = FixtureProvider([{"content": "ok", "usage": {"total_tokens": 10}},
                                {"content": "ok", "usage": {"total_tokens": 20}}], delay=.02)
    gateway = Gateway(provider)
    first = asyncio.create_task(gateway.generate(ModelRequest(messages=[])))
    while not provider.requests:
        await asyncio.sleep(0)
    day[0] = "2026-10-21"
    second = asyncio.create_task(gateway.generate(ModelRequest(messages=[])))
    await asyncio.gather(first, second)
    assert gateway.used_tokens == 20 and gateway.reserved_tokens == 0
    assert gateway._local_budget("2026-10-20")["used_tokens"] == 10


async def test_every_retry_reserves_and_transport_failure_stays_charged(tmp_path):
    class FailingProvider:
        name = "synthetic"
        calls = 0

        async def generate(self, request):
            self.calls += 1
            raise httpx.ReadTimeout("offline transport fixture")

    request = ModelRequest(messages=[], max_tokens=100)
    bound = estimate(request)
    queue = JobQueue(tmp_path / "runtime.sqlite3")
    provider = FailingProvider()
    gateway = Gateway(provider, budget_ledger=queue, usage_sink=queue.log_usage,
                      daily_token_limit=bound, retry_delay=0)
    with pytest.raises(BudgetExceeded) as exc:
        await gateway.generate(request)
    assert exc.value.reason == "daily_limit"
    assert provider.calls == 1
    assert gateway.used_tokens == bound and gateway.reserved_tokens == 0
    assert queue.usage()[0]["status"] == "failed_unknown"
    assert Gateway(provider, budget_ledger=JobQueue(queue.path)).used_tokens == bound


async def test_retry_success_and_invalid_schema_both_settle_actual_usage(tmp_path):
    class RetryProvider:
        name = "synthetic"
        calls = 0

        async def generate(self, request):
            self.calls += 1
            if self.calls == 1:
                raise httpx.ReadTimeout("offline transport fixture")
            return ModelResponse(provider=self.name, model="offline", content="{}", usage={"total_tokens": 7})

    request = ModelRequest(messages=[], output_schema={"type": "object", "required": ["ok"]})
    queue = JobQueue(tmp_path / "runtime.sqlite3")
    provider = RetryProvider()
    gateway = Gateway(provider, budget_ledger=queue, usage_sink=queue.log_usage, retry_delay=0)
    with pytest.raises(ProviderError, match="invalid structured"):
        await gateway.generate(request)
    assert provider.calls == 2
    assert gateway.used_tokens == estimate(request) + 7
    assert gateway.reserved_tokens == 0
    assert [row["charged_tokens"] for row in queue.usage()] == [estimate(request), 7]
    assert len({row["budget_reservation_id"] for row in queue.usage()}) == 2


async def test_cancelled_io_keeps_conservative_charge(tmp_path):
    queue = JobQueue(tmp_path / "runtime.sqlite3")
    provider = FixtureProvider(delay=10)
    request = ModelRequest(messages=[])
    gateway = Gateway(provider, budget_ledger=queue, usage_sink=queue.log_usage)
    task = asyncio.create_task(gateway.generate(request))
    while not provider.requests:
        await asyncio.sleep(0)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert gateway.reserved_tokens == 0 and gateway.used_tokens == estimate(request)
    assert queue.usage()[0]["status"] == "cancelled_unknown"


async def test_request_size_and_daily_limit_have_distinct_reasons(tmp_path):
    queue = JobQueue(tmp_path / "runtime.sqlite3")
    provider = FixtureProvider()
    gateway = Gateway(provider, budget_ledger=queue, daily_token_limit=1)
    with pytest.raises(BudgetExceeded) as exc:
        await gateway.generate(ModelRequest(messages=[], budget_tokens=1))
    assert exc.value.reason == "request_size"
    with pytest.raises(BudgetExceeded) as exc:
        await gateway.generate(ModelRequest(messages=[]))
    assert exc.value.reason == "daily_limit"
    assert not provider.requests


def test_operator_retry_cancel_and_reuse_saved_proposal(tmp_path):
    queue = JobQueue(tmp_path / "runtime.sqlite3")
    job_id = queue.enqueue(JobSpec(role="reflection"), now=1)
    queue.lease_job("worker", now=2)
    queue.save_result(job_id, "worker", {"value": "durable"}, now=3)
    for operation in (queue.retry_job, queue.cancel_job):
        with pytest.raises(ValueError, match="active lease"):
            operation(job_id, now=4)
    queue.finish(job_id, "worker", status="failed", error="publish rejected", now=5)
    assert queue.cancel_job(job_id, now=6)["status"] == "cancelled"
    retried = queue.retry_job(job_id, now=7)
    assert retried["status"] == "retry_wait"
    assert json.loads(retried["result"]) == {"value": "durable"}
    assert queue.retry_job(job_id, clear_result=True, now=8)["result"] is None
    with pytest.raises(KeyError):
        JobQueue(queue.path, user_id="other").retry_job(job_id, now=9)
    queue.lease_job("next", now=10)
    queue.finish(job_id, "next", status="succeeded", now=11)
    with pytest.raises(ValueError, match="completed"):
        queue.retry_job(job_id, now=12)


def test_operator_can_cancel_expired_worker_without_lease_resurrection(tmp_path):
    queue = JobQueue(tmp_path / "runtime.sqlite3")
    job_id = queue.enqueue(JobSpec(role="reflection"), now=1)
    queue.lease_job("worker", now=2, lease_seconds=5)
    queue.cancel_job(job_id, now=8)
    assert queue.lease_job("other", now=9) is None
