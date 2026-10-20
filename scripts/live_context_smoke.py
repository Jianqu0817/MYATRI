"""Explicit, capped official-API smoke for semantic summary/activation.

Run manually only. Reuses WinCred through DeepSeekProvider; never prints keys.
Existing report is a checkpoint: rerunning does NOT repeat paid requests.
"""
import asyncio
import json
from pathlib import Path

from myatri.app import Application
from myatri.contracts import Record, TemporaryEntry
from myatri.providers import ProviderError


ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "reports/live_context_smoke.json"
MAX_REQUESTS, MAX_ESTIMATED_USD = 2, 0.03


async def execute():
    if REPORT.exists():
        print("Checkpoint exists; no paid requests repeated. See reports/live_context_smoke.json")
        return
    report = {"scope": "synthetic semantic-compaction/activation smoke, not longitudinal quality",
              "max_requests": MAX_REQUESTS, "max_conservative_usd": MAX_ESTIMATED_USD,
              "attempted_requests": 0, "requests": [], "cases": {}, "status": "running"}
    def save():
        REPORT.parent.mkdir(exist_ok=True)
        REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    save()  # Checkpoint before reading credentials or making the first request.
    app = Application(ROOT / "var/live-context-smoke-20261020", mode="live", config={
        "chat": {"allow_paid": True, "model": "deepseek-flash"},
        "budget": {"daily_tokens": 30000, "input_per_million": .30, "output_per_million": 1.20}})
    app.gateway.retries = 0
    provider = app.gateway.provider
    class MeteredProvider:
        name = "deepseek"
        async def generate(self, request):
            upper_cost = (len(request.model_dump_json().encode("utf-8")) * .30 + request.max_tokens * 1.20) / 1e6
            if (report["attempted_requests"] >= MAX_REQUESTS or
                    sum(r["reserved_upper_usd"] for r in report["requests"]) + upper_cost > MAX_ESTIMATED_USD):
                raise ProviderError("explicit live context smoke cap reached")
            report["attempted_requests"] += 1
            row = {"purpose": request.purpose, "prompt_version": request.prompt_version,
                   "reserved_upper_usd": upper_cost, "status": "attempting"}
            report["requests"].append(row)
            save()
            try:
                response = await provider.generate(request)
                row.update(status="received", provider=response.provider, model=response.model,
                           usage=response.usage, finish_reason=response.finish_reason)
                return response
            except Exception as exc:
                row.update(status="failed", error_type=type(exc).__name__)
                raise
            finally:
                save()
    app.gateway.provider = MeteredProvider()
    try:
        app.store.append_message("user", "纯合成测试约定：周六下午三点去图书馆，改期前先确认。", "context_synthetic_plan")
        app.store.append_message("assistant", "这是测试中的暂定安排，不代表已经完成活动。", "context_synthetic_reply")
        run = Record(record_id="context_synthetic_run", record_kind="cognitive_run", payload={"role": "synthetic_fixture_seed"})
        app.store.commit([run], "context-synthetic-run")
        state = app.states.create(TemporaryEntry(text="安排变化时，想先询问对方是否方便，再确定新时间。", scope="共同日程安排",
                                 origin_kind="generated_idea", origin_refs=[run.ref]), entry_id="context_synthetic_intent")
        before = app.persona.read_state().ref
        selected, activation = await app.conversation.context.selector.aselect_active_entries("周六去图书馆的约定要改时间，想先沟通彼此是否方便。")
        activation_ok = activation.selection_method == "llm" and [r.ref for r in selected] == [state.ref]
        report["cases"]["activation"] = {"passed": activation_ok, "method": activation.selection_method,
            "selected_refs": activation.selected_refs, "limitations": activation.limitations, "generator": activation.generator}
        save()
        summary = await app.conversation.context.compactor.acompact(preserve_ids=["context_synthetic_plan"])
        summary_ok = bool(summary.payload["strategy"] == "llm-semantic-v1" and summary.payload["semantic_items"])
        report["cases"]["compaction"] = {"passed": summary_ok, "strategy": summary.payload["strategy"],
            "summary_ref": summary.ref, "generator": summary.generator, "items": summary.payload["semantic_items"],
            "limitations": summary.payload["limitations"], "preserve_refs": summary.payload["preserve_refs"]}
        report["archive_errors"] = app.store.verify_archive()
        report["persona_unchanged"] = app.persona.read_state().ref == before
        report["state_unchanged"] = app.store.get_record(state.record_id).ref == state.ref
        report["estimated_received_usd"] = sum(
            (r.get("usage", {}).get("prompt_tokens", 0) * .30 + r.get("usage", {}).get("completion_tokens", 0) * 1.20) / 1e6
            for r in report["requests"])
        report["status"] = "passed" if (activation_ok and summary_ok and not report["archive_errors"] and
            report["persona_unchanged"] and report["state_unchanged"]) else "failed"
    except Exception as exc:
        report.update(status="failed", error_type=type(exc).__name__)
    finally:
        save()
    print(json.dumps({key: report[key] for key in ("status", "attempted_requests", "cases")}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8")
    asyncio.run(execute())
