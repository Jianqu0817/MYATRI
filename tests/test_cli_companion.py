"""CLI migration keeps the old archive, adds real channel behavior, uses no paid API."""
from argparse import Namespace
from copy import deepcopy
import json
from pathlib import Path
import sqlite3

from aiohttp.test_utils import TestClient, TestServer
import pytest

from myatri.app import Application, load_config
from myatri.providers import FixtureProvider
from myatri.companion.cli_runtime import CliRuntime, run_cli, write_active_config
from myatri.companion.context_viewer import library_list, create_app as viewer_app
from myatri.companion.monitor import snapshot


PROJECT = Path(__file__).resolve().parents[1]


def configuration():
    config = load_config(PROJECT / "config/cli-engine.toml")
    config["embedding"] = {"backend": "tfidf"}
    config["context"].update(llm_activation=False, llm_compaction=False)
    config["cognition"]["maintenance_turns"] = 0
    return config


def runtime(tmp_path, *, replies=None):
    project = tmp_path / "project"
    project.mkdir(exist_ok=True)
    card = project / "persona.md"
    card.write_text((PROJECT / "config/personas/xiaowennuan/persona.md").read_text(encoding="utf-8"), encoding="utf-8")
    provider = FixtureProvider(replies or [{"content": "我还记得书架上那只纸飞机，放得好好的。<|msg|>不着急，我在这里慢慢陪你聊。"}])
    settings = {"project_root": str(project), "mode": "offline", "owner_id": "owner", "owner_name": "菅蘧",
                "capture_requests": True, "quality_guard_enabled": False, "cold_retention_days": 30}
    return CliRuntime(project / "var/xiaowennuan", settings, configuration(), card,
                      provider_factory=lambda scope: provider), provider, project


async def test_old_cli_memory_and_internal_identity_survive_with_new_role_card(tmp_path):
    rt, provider, _ = runtime(tmp_path)
    old = Application(rt.archive_root, config={"context": {"llm_activation": False, "llm_compaction": False}},
                      provider=FixtureProvider())
    original = old.store.append_message("user", "我们的纸飞机放在书架第二层。", message_id="legacy_user")
    answer = old.store.append_message("assistant", "嗯，放好啦。", message_id="legacy_answer", reply_to=original.ref)
    await rt.bootstrap()
    try:
        result = await rt.receive_text("还记得纸飞机吗", message_id="new")
        app = rt.apps[rt.session.scope]
        assert (app.store.agent_id, app.store.user_id) == ("atri", "local")
        assert app.store.get_record(original.record_id).model_dump() == original.model_dump()
        assert app.store.get_record(answer.record_id).ref == answer.ref
        prompt = json.dumps(provider.requests[-1].messages, ensure_ascii=False)
        assert "我们的纸飞机放在书架第二层" in prompt
        assert "当前是本机CLI私聊" in prompt and "本轮是本机CLI私聊" in prompt
        assert "legacy_user" in app.conversation.context.explain_context()["history_refs"][0]
        assert app.gateway.budget_ledger is app.queue
        printed = []
        await rt.display_delivery(result, emit=printed.append)
        assert len(printed) == 2
        assert all("[小温暖]" in text for text in printed)
        with sqlite3.connect(rt.path) as db:
            assert db.execute("SELECT status,sent_parts FROM deliveries WHERE id=?", (result["id"],)).fetchone() == ("sent", 2)
        assert app.store.verify_archive() == []
    finally:
        await rt.close()


async def test_clear_and_reload_keep_originals_and_take_effect_next_turn(tmp_path):
    rt, provider, _ = runtime(tmp_path, replies=[{"content": "陪你待着。"}, {"content": "好，慢慢说。"}])
    await rt.bootstrap()
    try:
        first = await rt.receive_text("一个旧的话题", message_id="first")
        await rt.display_delivery(first, emit=lambda _: None)
        app = rt.apps[rt.session.scope]
        old_raw = app.store.get_record(first["id"])
        clear = await rt.clear_runtime_context(rt.session.scope)
        assert clear["ok"]
        card = rt.persona_file
        card.write_text(card.read_text(encoding="utf-8") + "\n## P99_cli_test\n这轮卡片带着纸鹤。\n", encoding="utf-8")
        reload = await rt.reload_runtime(rt.session.scope)
        assert reload["ok"] and reload["persona_changed"]
        await rt.receive_text("现在聊新的", message_id="second")
        prompt = json.dumps(provider.requests[-1].messages, ensure_ascii=False)
        assert "这轮卡片带着纸鹤" in prompt
        assert "一个旧的话题" not in prompt
        assert app.store.get_record(old_raw.record_id).ref == old_raw.ref
    finally:
        await rt.close()


async def test_terminal_failure_marks_unknown_without_resubmitting(tmp_path):
    rt, _, _ = runtime(tmp_path)
    await rt.bootstrap()
    try:
        result = await rt.receive_text("在吗", message_id="once")
        def failed(_):
            raise OSError("fixture output disconnected")
        with pytest.raises(OSError):
            await rt.display_delivery(result, emit=failed)
        assert not (await rt.claim(result["id"]))["claimed"]
    finally:
        await rt.close()


async def test_cli_library_controls_metrics_and_viewer_cookies(tmp_path):
    rt, _, project = runtime(tmp_path)
    await rt.bootstrap()
    try:
        settings = {**rt.config, "port": 8776, "engine_config": "config/engine.toml"}
        write_active_config(project, settings, rt.archive_root, rt.session.scope)
        assert library_list(project)["libraries"][0]["key"] == "cli"
        assert library_list(project)["libraries"][0]["runtime_controls"] is True
        assert snapshot(project)["libraries"][0]["key"] == "cli"
        async with TestClient(TestServer(viewer_app(project))) as client:
            assert (await client.get("/api/libraries")).status == 403
            assert (await client.get("/")).status == 200
    finally:
        await rt.close()


async def test_single_turn_cli_dispatch_uses_only_local_fixture(tmp_path):
    rt, _, project = runtime(tmp_path)
    # Only reuse its prepared paths; close empty sidecar before the actual run.
    await rt.close()
    args = Namespace(project=str(project), root=str(rt.archive_root), agent="atri", user="local", mode="offline",
                     display_name="小温暖", persona_file=str(rt.persona_file), no_ui=True,
                     message="你好", message_id="single")
    provider = FixtureProvider([{"content": "我在呢。"}])
    result = await run_cli(args, deepcopy(configuration()), {"quality_guard_enabled": False},
                           provider_factory=lambda scope: provider)
    assert result["status"] == "prepared" and len(provider.requests) == 1


async def test_viewer_reloads_and_clears_real_private_runtime(tmp_path):
    from myatri.companion.server import create_app
    from myatri.companion.context_viewer import proxy_control
    rt, provider, project = runtime(tmp_path)
    await rt.bootstrap()
    token = "test-local-token-" * 4
    (project / "token.txt").write_text(token, encoding="ascii")
    try:
        async with TestServer(create_app(rt, token)) as server:
            write_active_config(project, {"port": server.port, "token_file": "token.txt"}, rt.archive_root, rt.session.scope)
            for action in ("reload", "clear-context"):
                data, status = await proxy_control(project, "cli", action)
                assert status == 200 and data["ok"], data
        assert not provider.requests
    finally:
        await rt.close()


async def test_private_proactive_generation_delivers_without_fake_human_turn(tmp_path):
    from datetime import datetime, timezone
    from myatri.companion.proactive import Candidate, ProactiveDraft
    rt, _, _ = runtime(tmp_path, replies=[{"content": "我在这儿。"}, {"content": "窗边那只纸飞机，还好好放着呢。"}])
    await rt.bootstrap()
    try:
        initial = await rt.receive_text("纸飞机放在窗边", message_id="real-person")
        await rt.display_delivery(initial, emit=lambda _: None)
        app = rt.apps[rt.session.scope]
        before = [r.ref for r in app.store.list_records("raw_message") if r.payload.get("role") == "user"]
        now = datetime.now(timezone.utc)
        candidate = Candidate(candidate_id="cli-test", kind="temporary_entry", created_at=now,
                              excerpt="纸飞机放在窗边", context_hash="test")
        draft = await rt._proactive_generate(scope=rt.session.scope, candidate=candidate, now=now, instruction="自然说一句。")
        assert draft and draft["metadata"]["self_initiated"]
        typed = ProactiveDraft(parts=tuple(draft["parts"]), metadata=draft["metadata"],
                              record_id=draft["record_id"], context_hash=draft["context_hash"])
        result = await rt._proactive_deliver(scope=rt.session.scope, candidate=candidate, draft=typed, now=now)
        printed = []
        await rt.display_delivery(result, emit=printed.append)
        assert printed
        assert before == [r.ref for r in app.store.list_records("raw_message") if r.payload.get("role") == "user"]
    finally:
        await rt.close()
