"""Publish the manually audited local acceptance evidence, refusing missing artifacts/failing tests."""
import json
from pathlib import Path
import xml.etree.ElementTree as ET

root = Path(__file__).resolve().parents[1]
current_plan = json.loads((root / "docs/02_实施任务清单.json").read_text(encoding="utf-8-sig"))
if current_plan.get("persistence_repairs"):
    raise SystemExit("Historical finalizer disabled after persistence repairs; use reports/persistence_fixes_2026-10-20.md and current validation evidence.")
suite = ET.parse(root / "reports/pytest_results.xml").getroot().find("testsuite")
assert suite is not None and suite.attrib["failures"] == suite.attrib["errors"] == "0"
evidence = {
    "T00": ["reports/source_audit.md", "reports/source_verification.json", "THIRD_PARTY_NOTICES.md", "docs/adr/0001-scope.md"],
    "T01": ["uv.lock", "pyproject.toml", "reports/environment_smoke.json", "reports/model_manifest.json", "docs/adr/0002-stack-and-models.md"],
    "T02": ["src/myatri/contracts/__init__.py", "tests/fixtures/contracts/Record.schema.json", "docs/adr/0003-data-and-interfaces.md"],
    "T03": ["src/myatri/storage/archive.py", "src/myatri/runtime/commit.py", "tests/integration/test_commit_recovery.py"],
    "T04": ["src/myatri/providers/gateway.py", "src/myatri/providers/local_onnx.py", "tests/test_gateway.py", "tests/test_protocol_recovery.py"],
    "T05": ["src/myatri/runtime/jobs.py", "src/myatri/runtime/worker.py", "tests/test_jobs.py"],
    "T06": ["src/myatri/cognition/experience.py", "tests/test_experience.py", "prompts/experience/v1.md"],
    "T07": ["src/myatri/memory/index.py", "src/myatri/memory/graph.py", "src/myatri/cognition/association.py", "tests/test_neural.py"],
    "T08": ["src/myatri/memory/clustering.py", "src/myatri/memory/themes.py", "src/myatri/cognition/theme.py", "reports/clustering_baseline.md"],
    "T09": ["src/myatri/retrieval/service.py", "tests/test_retrieval.py"],
    "T10": ["src/myatri/conversation/engine.py", "src/myatri/conversation/context.py", "src/myatri/interfaces/cli.py", "tests/integration/test_v1_lifecycle.py"],
    "T11": ["src/myatri/conversation/compaction.py", "src/myatri/conversation/budget.py", "tests/test_context.py"],
    "T12": ["src/myatri/persona/temporary.py", "src/myatri/persona/activation.py", "src/myatri/cognition/reflection.py", "src/myatri/cognition/temporary_state.py", "tests/test_persona_lifecycle.py"],
    "T13": ["src/myatri/persona/patch.py", "src/myatri/cognition/persona_revision.py", "src/myatri/cognition/reviewer.py", "tests/test_human_persona.py", "reports/demo_trace.json"],
    "T14": ["src/myatri/app.py", "src/myatri/runtime/scheduler.py", "config/schedules.toml", "tests/integration/test_v1_lifecycle.py"],
    "T15": ["src/myatri/interfaces/inspect.py", "tests/test_inspection.py", "docs/运行与恢复手册.md", "reports/runtime_inspection.md", "reports/dependency_licenses.json"],
    "T16": ["src/myatri/evaluation.py", "evals/corpus.json", "evals/annotations.json", "reports/evaluation.md", "reports/evaluation.json", "reports/live_smoke.md"],
    "T17": ["dist/myatri-0.1.0-py3-none-any.whl", "dist/myatri-0.1.0.tar.gz", "docs/交付与限制.md", "reports/acceptance.md", "reports/demo_archive.zip"],
}
for paths in evidence.values():
    for path in paths:
        assert (root / path).is_file() and (root / path).stat().st_size, path
path = root / "docs/02_实施任务清单.json"
tasks = json.loads(path.read_text(encoding="utf-8-sig"))
live_path = root / "reports/live_smoke.json"
live = json.loads(live_path.read_text(encoding="utf-8")) if live_path.exists() else {}
protocol_verified = all(live.get("cases", {}).get(name, {}).get("status") == "passed" for name in
    ("basic_generation", "json_schema", "tools_roundtrip", "thinking_tools_roundtrip"))
tasks.update(status="v1_live_protocol_verified_semantic_pending" if protocol_verified else "v1_local_delivered_live_pending", updated_date="2026-10-20",
    execution_gate="用户2026-10-20追加授权官方DeepSeek-V4.1-Flash小规模测试与Windows安全凭据存储；真实消息与外部部署仍未授权且未执行。" if protocol_verified else
        "用户已授权本地实现/必要依赖/离线验证；付费live状态以最新用户授权与报告为准。",
    validation_levels={"interfaces": "implemented", "offline_fixture": "passed", "local_tfidf": "actually_run",
        "local_bge_onnx": "actually_run_512_dimensions", "leiden": "actually_run", "deepseek_live": "official_flash_protocol_smoke_passed" if protocol_verified else "not_verified",
        "real_cognitive_semantic_quality": "pending_live_and_longitudinal_review", "real_outreach": "disabled_not_implemented"},
    final_test_result={"tests": int(suite.attrib["tests"]), "failures": 0, "errors": 0,
                       "skipped": int(suite.attrib["skipped"]), "seconds": float(suite.attrib["time"]), "report": "reports/pytest_results.xml"})
for task in tasks["tasks"]:
    if task["id"] in evidence:
        task["status"] = "completed_local"
        task["completion_evidence"] = evidence[task["id"]] + ["reports/pytest_results.xml"]
        task["validation_note"] = "本地实现/离线结构与实际本地算法已验；最新官方Flash协议smoke见reports/live_smoke.json，长期人格语义效果仍未验证。"
        if task["id"] in {"T01", "T04", "T16", "T17"}:
            task["live_verification"] = "pending_not_authorized"
        if protocol_verified and task["id"] in {"T01", "T04"}:
            task["live_verification"] = "official_flash_generation_json_tools_thinking_verified"
            task["completion_evidence"] += ["reports/live_smoke.json", "reports/live_models.json", "tests/test_credentials.py"]
        if protocol_verified and task["id"] in {"T16", "T17"}:
            task["live_verification"] = "protocol_verified_short_cognition_recovered_v2_longitudinal_pending"
            task["completion_evidence"] += ["reports/live_smoke.json", "tests/test_secret_exclusion.py"]
path.write_text(json.dumps(tasks, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
delivery = root / "docs/交付与限制.md"
import re
delivery.write_text(re.sub(r"\d+项测试", suite.attrib["tests"]+"项测试", delivery.read_text(encoding="utf-8-sig")), encoding="utf-8")
print(json.dumps(tasks["final_test_result"]))
