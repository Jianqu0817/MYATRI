"""Explicit, bounded official DeepSeek smoke. No secret in files or arguments.

Run only after the user has authorized paid tests. Checkpoints prevent automatic
repeat of already attempted cases. Only synthetic material is sent.
"""
from __future__ import annotations

import argparse
import asyncio
from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
import time

import httpx
import jsonschema

from myatri.app import Application
from myatri.contracts import ModelRequest
from myatri.providers import DeepSeekProvider, Gateway, ProviderError
from myatri.providers.gateway import assistant_message


ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "reports/live_smoke.json"


class Recorder:
    def __init__(self):
        self.data = json.loads(REPORT.read_text(encoding="utf-8")) if REPORT.exists() else {
            "date": "2026-10-20", "official_endpoint": "https://api.deepseek.com",
            "requested_model": "deepseek-flash", "advertised_model": "DeepSeek-V4.1-Flash",
            "credential_storage": "Windows Credential Manager", "secret_in_project": False,
            "max_generation_requests": 20, "max_estimated_peak_cost_usd": 0.10,
            "price_reference": "https://api-docs.deepseek.com/quick_start/pricing/",
            "price_per_million_usd_upper_bound": {"input_cache_hit": 0.006, "input_cache_miss": 0.30, "output": 1.20},
            "cases": {}, "requests": [], "real_messages_sent": 0, "external_deployments": 0,
            "scope": "short synthetic API/protocol/integration smoke, not longitudinal persona quality"}
        self.case = ""
        self.save()

    def save(self):
        usage = [r.get("usage", {}) for r in self.data["requests"]]
        self.data["summary"] = {
            "generation_requests": len(self.data["requests"]),
            "successful_responses": sum(r.get("status") == "received" for r in self.data["requests"]),
            "prompt_tokens": sum(x.get("prompt_tokens", 0) for x in usage),
            "completion_tokens": sum(x.get("completion_tokens", 0) for x in usage),
            "estimated_peak_cost_usd": sum(r.get("estimated_peak_cost_usd", 0) for r in self.data["requests"]),
            "cost_bound_including_unknown_usd": sum(r.get("estimated_peak_cost_usd", r.get("reserved_cost_usd", 0)) for r in self.data["requests"]),
            "cost_is_estimate_not_account_debit": True,
        }
        self.data["updated_at"] = datetime.now(timezone.utc).isoformat()
        temp = REPORT.with_suffix(".json.tmp")
        temp.write_text(json.dumps(self.data, ensure_ascii=False, indent=2), encoding="utf-8")
        temp.replace(REPORT)

    async def run_case(self, name, operation):
        if name in self.data["cases"]:
            print(json.dumps({"case": name, "status": self.data["cases"][name]["status"], "already_attempted": True}))
            return
        self.case = name
        self.data["cases"][name] = {"status": "started", "started_at": datetime.now(timezone.utc).isoformat()}
        self.save()
        try:
            details = await operation()
            self.data["cases"][name].update(status="passed", details=details)
        except Exception as exc:
            # Never stringify a transport request/headers or an arbitrary provider error body.
            self.data["cases"][name].update(status="failed", error_type=type(exc).__name__,
                reason=str(exc)[:200] if isinstance(exc, (AssertionError, ProviderError)) else "see bounded request status; no automatic paid retry")
        self.save()
        print(json.dumps({"case": name, "status": self.data["cases"][name]["status"]}, ensure_ascii=False), flush=True)


class MeteredProvider:
    name = "deepseek"

    def __init__(self, provider, recorder):
        self.provider, self.recorder = provider, recorder

    async def generate(self, request):
        data = self.recorder.data
        if len(data["requests"]) >= data["max_generation_requests"]:
            raise ProviderError("smoke generation-request cap reached")
        request = request.model_copy(update={"max_tokens": min(request.max_tokens, 2048), "timeout": min(request.timeout, 60)})
        possible_input_tokens = len(request.model_dump_json().encode("utf-8")) + 512
        reserve = (possible_input_tokens * .30 + request.max_tokens * 1.20) / 1e6
        if data["summary"].get("cost_bound_including_unknown_usd", data["summary"]["estimated_peak_cost_usd"]) + reserve > data["max_estimated_peak_cost_usd"]:
            raise ProviderError("smoke conservative cost cap reached")
        row = {"case": self.recorder.case, "role": request.role, "purpose": request.purpose,
               "trace_id": request.trace_id, "thinking": request.thinking, "max_output_tokens": request.max_tokens,
               "status": "started_outcome_unknown", "reserved_cost_usd": reserve}
        data["requests"].append(row)
        self.recorder.save()
        start = time.monotonic()
        try:
            response = await self.provider.generate(request)
            usage = response.usage
            total_input = usage.get("prompt_tokens", 0)
            hit = usage.get("prompt_cache_hit_tokens", 0)
            miss = usage.get("prompt_cache_miss_tokens", max(0, total_input-hit))
            output = usage.get("completion_tokens", 0)
            row.update(status="received", response_model=response.model, usage=usage,
                finish_reason=response.finish_reason, elapsed_seconds=time.monotonic()-start,
                reasoning_field_present="reasoning_content" in response.provider_fields,
                estimated_peak_cost_usd=(hit*.006 + miss*.30 + output*1.20)/1e6)
            return response
        except httpx.HTTPStatusError as exc:
            row.update(status="http_error", http_status=exc.response.status_code)
            raise
        except Exception as exc:
            row.update(status="error_outcome_unknown", error_type=type(exc).__name__)
            raise
        finally:
            self.recorder.save()


async def execute(phase):
    recorder = Recorder()
    models = json.loads((ROOT / "reports/live_models.json").read_text(encoding="utf-8"))
    assert models["http_status"] == 200 and any(m["id"] == "deepseek-flash" for m in models["models"])
    base = DeepSeekProvider(model="deepseek-flash", allow_paid=True, capability_probe=True)
    metered = MeteredProvider(base, recorder)
    gateway = Gateway(metered, daily_token_limit=100000, retries=0)

    async def basic():
        result = await gateway.generate(ModelRequest(messages=[{"role": "user", "content": "请只回复 MYATRI_OK"}],
            max_tokens=64, purpose="official_live_basic"))
        assert result.content.strip() == "MYATRI_OK", "health-check marker mismatch"
        return {"response": result.content, "model": result.model}

    async def structured():
        schema = {"type": "object", "required": ["ok", "marker"], "properties": {
            "ok": {"const": True}, "marker": {"const": "MYATRI_JSON_OK"}}, "additionalProperties": False}
        result = await gateway.generate(ModelRequest(messages=[{"role": "user", "content": "Return JSON with ok=true and marker=MYATRI_JSON_OK."}],
            output_schema=schema, max_tokens=128, purpose="official_live_json"))
        return {"schema_validated": True, "response": json.loads(result.content)}

    async def tools(thinking):
        tool = {"type": "function", "function": {"name": "lookup_memory", "description": "Read synthetic local E101. No external action.",
            "parameters": {"type": "object", "properties": {"ref": {"const": "E101", "type": "string"}}, "required": ["ref"], "additionalProperties": False}}}
        messages = [{"role": "system", "content": "You are testing a local read-only tool. First call lookup_memory with ref E101, then summarize its result in one Chinese sentence. Never make up its result."},
                    {"role": "user", "content": "请先调用工具读取E101，再告诉我电影安排发生了什么。"}]
        first = await gateway.generate(ModelRequest(messages=messages, tools=[tool], thinking=thinking,
            max_tokens=1024, purpose="official_live_thinking_tools" if thinking else "official_live_tools"))
        assert first.tool_calls, "model did not request the read-only tool"
        assert len(first.tool_calls) <= 2, "unexpected tool expansion"
        messages.append(assistant_message(first))
        for call in first.tool_calls:
            assert call["function"]["name"] == "lookup_memory", "unexpected tool name"
            arguments = json.loads(call["function"]["arguments"])
            jsonschema.validate(arguments, tool["function"]["parameters"])
            messages.append({"role": "tool", "tool_call_id": call["id"], "content": json.dumps({
                "ref": "E101", "synthetic": True, "text": "电影安排临时取消，当事人感到失落。"}, ensure_ascii=False)})
        final = await gateway.generate(ModelRequest(messages=messages, tools=[tool], thinking=thinking,
            max_tokens=1024, purpose="official_live_thinking_tool_result" if thinking else "official_live_tool_result"))
        assert not final.tool_calls, "tool probe did not finish within one roundtrip"
        assert "电影" in final.content and "取消" in final.content, "tool result not grounded in synthetic record"
        if thinking:
            assert "reasoning_content" in first.provider_fields, "thinking tool protocol field missing"
        return {"tool_call_count": len(first.tool_calls), "complete_roundtrip": True,
                "thinking": thinking, "reasoning_returned_to_provider": thinking and "reasoning_content" in first.provider_fields,
                "final_response": final.content, "tools_are_local_read_only": True}

    async def cognition():
        app = Application(ROOT / "var/live-smoke-20261020", mode="live", provider=metered,
            config={"chat": {"capabilities_verified": False}, "budget": {"daily_tokens": 100000,
                "input_per_million": .30, "output_per_million": 1.20}})
        app.gateway.retries = 0
        app.worker.max_attempts = 1
        answer = await app.conversation.respond(
            "这是纯合成测试材料，不是真实用户经历：2026年10月19日，角色与同伴的电影约定临时取消，角色有些失落，"
            "希望下次先确认时间。请回应这种感受，保留暂定性，不要实际联系任何人，也不要据此改写稳定人格。",
            message_id="live_synthetic_turn")
        jobs_run = await app.drain(max_jobs=30)
        jobs = [{"role": j["role"], "status": j["status"], "error": j["error"]} for j in app.queue.list_jobs()]
        recorder.data["cognition_jobs"] = jobs
        recorder.save()
        assert all(j["status"] == "succeeded" for j in jobs), "one or more real cognitive jobs failed; inspect cognition_jobs"
        assert app.store.verify_archive() == [], "archive/source validation failed"
        assert app.persona.read_state().revision == 1, "pure synthetic test must not imply natural persona change"
        events = app.store.list_records("event")
        decisions = [{"role": r.payload.get("role"), "decision": r.payload.get("decision"), "reason": r.payload.get("reason")}
                     for r in app.store.list_records("cognitive_run")]
        return {"front_response": answer.body_markdown, "jobs_run": jobs_run, "jobs": jobs,
            "event_refs": [e.ref for e in events], "event_reality_scopes": [e.payload.get("reality_scope") for e in events],
            "temporary_states": [{"ref": r.ref, "status": r.payload["status"], "origin_kind": r.payload["origin_kind"]} for r in app.states.list()],
            "cognitive_decisions": decisions, "persona_ref": app.persona.read_state().ref,
            "archive_errors": [], "actual_leiden_runs": app.index.clusters.get("quality", {}).get("actual_leiden_runs", 0)}

    async def recovery():
        from myatri.contracts import JobSpec
        app = Application(ROOT / "var/live-smoke-20261020", mode="live", provider=metered,
            config={"budget": {"daily_tokens": 100000, "input_per_million": .30, "output_per_million": 1.20}})
        app.gateway.retries = 0
        app.worker.max_attempts = 1
        prior_failed = [j for j in app.queue.list_jobs() if j["status"] == "failed"]
        assert prior_failed and all(j["role"] == "temporary_state" for j in prior_failed), "unexpected prior failure"
        refs = [r.ref for r in app.store.list_records() if r.record_kind in {"event", "reflection"}]
        new_job = app.queue.enqueue(JobSpec(role="temporary_state", input_refs=refs, prompt_version="v2"))
        processed = await app.drain(max_jobs=12)
        jobs = app.queue.list_jobs()
        new = next(j for j in jobs if j["id"] == new_job)
        assert new["status"] == "succeeded", "v2 temporary-state job did not succeed"
        assert all(j["status"] == "succeeded" for j in jobs if j["id"] not in {old["id"] for old in prior_failed}), "unexpected new job failure"
        assert app.store.verify_archive() == [] and app.persona.read_state().revision == 1
        return {"prompt_version": "temporary_state/v2", "affected_jobs_only_replayed": True,
            "processed": processed, "historical_failed_jobs_preserved": len(prior_failed),
            "new_jobs": [{"role": j["role"], "status": j["status"]} for j in jobs if j["id"] not in {old["id"] for old in prior_failed}],
            "temporary_states": [{"ref": r.ref, "status": r.payload["status"], "origin_kind": r.payload["origin_kind"]} for r in app.states.list()],
            "persona_ref": app.persona.read_state().ref, "archive_errors": [],
            "actual_leiden_runs": app.index.clusters.get("quality", {}).get("actual_leiden_runs", 0)}

    if phase in {"basic", "all"}:
        await recorder.run_case("basic_generation", basic)
    if phase in {"protocol", "all"}:
        assert recorder.data["cases"].get("basic_generation", {}).get("status") == "passed", "first run --phase basic"
        await recorder.run_case("json_schema", structured)
        await recorder.run_case("tools_roundtrip", lambda: tools(False))
        await recorder.run_case("thinking_tools_roundtrip", lambda: tools(True))
    if phase in {"cognition", "all"}:
        assert recorder.data["cases"].get("json_schema", {}).get("status") == "passed", "first run --phase protocol"
        await recorder.run_case("real_cognitive_pipeline", cognition)
    if phase == "recovery":
        await recorder.run_case("cognitive_pipeline_recovered_v2", recovery)
    recorder.save()
    print(json.dumps(recorder.data["summary"], ensure_ascii=False), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase", choices=["basic", "protocol", "cognition", "recovery", "all"], default="all")
    asyncio.run(execute(parser.parse_args().phase))
