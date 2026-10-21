"""AstrBot-developed conversation runtime with a terminal transport and old CLI archive."""
from __future__ import annotations

import asyncio
from contextlib import closing
from datetime import datetime, timezone
import json
from pathlib import Path
import secrets
import sqlite3
import sys
import uuid

from aiohttp import web

from myatri.interfaces.terminal import chat_block, input_prompt
from myatri.retrieval import RecallService
from .bridge import Bridge, Incoming
from .group_memory import GroupRecall
from .server import create_app, service_lock


PRIVATE_CHANNEL = (
    "当前是本机CLI私聊，不是微信群，也没有旁观的群友。当前用户身份由本机配置提供，昵称不是认证。"
    "原CLI库中没有渠道标记的历史人类原话属于本机原对话人，作为历史材料保留；"
    "不能宣称已导入微信群聊档案，角色卡中的群聊示例只是表达示例，不是本轮新发生的事。"
    "按当前text接最相关的话头，不总结全场、不刻意展示记忆，不强行反问或暧昧。"
    "对已核验的创作者可自然表达少量依恋。历史助手回复不是人类事实，也不能证明对方已读。"
    "只输出自然正文；语义分段仍用<|msg|>，日期时间由终端显示，不复述发送标签。"
)


class PrivateRecall(GroupRecall):
    def recall(self, query, filters=None, snapshot=None, budget=4000):
        # Existing CLI records have no WeChat IDs. Their human ownership comes
        # from this locally selected private library, never a nickname in text.
        if self.current_sender == self.identities.owner_id:
            return RecallService.recall(self, query, filters, snapshot, budget)
        return super().recall(query, filters, snapshot, budget)


class CliRuntime(Bridge):
    def __init__(self, archive_root, config, engine_config, persona_file, *, agent="atri", user="local",
                 provider_factory=None):
        self.archive_root = Path(archive_root).resolve()
        self.archive_agent, self.archive_user = agent, user
        self.display_name = config.get("display_name", "小温暖")
        self.output_lock = asyncio.Lock()
        self.sender_id = config.get("owner_id", "local-owner")
        self.sender_name = config.get("owner_name", "你")
        settings = {**config, "allowed_groups": ["cli|private"], "random_reply_probability": 1.,
                    "cooldown_seconds": 0}
        super().__init__(self.archive_root / "cli-runtime", settings, engine_config, persona_file,
                         provider_factory=provider_factory)
        self.session = Incoming(platform_id="cli", bot_id="xiaowennuan", group_id="private",
            sender_id=self.sender_id, sender_name=self.sender_name, message_id="bootstrap",
            sent_at=datetime.now(timezone.utc).isoformat(), text="本机会话启动", mentioned=True)

    def _application_location(self, message):
        return self.archive_root, self.archive_agent, self.archive_user

    def _channel_instruction(self):
        return PRIVATE_CHANNEL

    def _application(self, message, *, start_workers=True):
        app = super()._application(message, start_workers=start_workers)
        if not isinstance(app.recall, PrivateRecall):
            recall = PrivateRecall(app.store, app.index, self.identities, message.scope)
            app.recall = app.conversation.recall = app.conversation.context.recall = recall
            app.conversation.context.private_history = True
            # Retain the old library's provider-scoped budget accounting.
            app.gateway.budget_ledger = app.queue
            app.gateway.budget_scope = getattr(app.gateway.provider, "name", type(app.gateway.provider).__name__)
        return app

    def _proactive_budget_ratio(self, scope):
        app = self.apps.get(scope)
        if app is None:
            return 0.
        usage = app.gateway.budget_ledger.budget_usage(app.gateway.budget_scope)
        return (usage["used_tokens"] + usage["reserved_tokens"]) / max(1, app.gateway.daily_token_limit)

    def _health_snapshot(self):
        from .health import health_snapshot
        return health_snapshot(self.root, runtime_paths=[self.archive_root / "runtime.sqlite3"])

    async def bootstrap(self):
        # Route metadata is not a human message and never enters raw_message.
        self.routes[self.session.scope] = self.session.model_dump()
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute("INSERT OR REPLACE INTO group_routes VALUES (?,?)",
                       (self.session.scope, json.dumps(self.session.model_dump(), ensure_ascii=False)))
        self._application(self.session, start_workers=False)
        await self.reload_runtime(self.session.scope)
        self._application(self.session)
        self.start()

    async def receive_text(self, text, *, message_id=None, sender_id=None, sender_name=None):
        message = self.session.model_copy(update={"message_id": message_id or uuid.uuid4().hex,
            "text": text, "sent_at": datetime.now(timezone.utc).isoformat(),
            "sender_id": sender_id or self.sender_id, "sender_name": sender_name or self.sender_name})
        return await self.receive(message)

    async def display_delivery(self, result, emit=None):
        if result.get("status") != "prepared":
            return result
        emit = emit or (lambda text: print(text, flush=True))
        async with self.output_lock:
            claim = await self.claim(result["id"])
            if not claim.get("claimed"):
                return claim
            try:
                for index, part in enumerate(result["reply_parts"]):
                    stamp = datetime.now().astimezone().isoformat()
                    emit(chat_block(self.display_name, part, stamp))
                    # For the terminal, a successful flush is the delivery
                    # receipt. It does not prove that the user read the text.
                    await self.acknowledge(result["id"], "sent", part_index=index)
            except BaseException:
                await self.acknowledge(result["id"], "unknown", reason_code="send_error")
                raise
        return result

    async def poll_proactive(self):
        while True:
            with closing(sqlite3.connect(self.path)) as db:
                keys = [r[0] for r in db.execute("SELECT id FROM deliveries WHERE scope=? AND status='prepared' "
                    "AND trigger_kind='proactive' ORDER BY rowid", (self.session.scope,))]
                pending = [self._delivery_result(db, key) for key in keys]
            for result in pending:
                await self.display_delivery(result)
            await asyncio.sleep(1)


def _toml_table(name, values):
    lines = [f"[{name}]"]
    for key, value in values.items():
        if isinstance(value, dict) or value is None:
            continue
        lines.append(f"{key} = " + json.dumps(value, ensure_ascii=False))
    for key, value in values.items():
        if isinstance(value, dict):
            lines.extend(["", _toml_table(name + "." + key, value)])
    return "\n".join(lines)


def write_active_config(project, settings, archive_root, scope):
    project = Path(project).resolve()
    values = {**settings, "application_root": str(Path(archive_root).resolve()), "cli_scope": scope,
              "state_root": str(Path(archive_root).resolve() / "cli-runtime")}
    path = project / "config/cli.local.toml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_toml_table("bridge", values) + "\n", encoding="utf-8")
    return path


async def start_ui(runtime, project, settings, token):
    from .context_viewer import create_app as create_viewer_app
    from .monitor import create_monitor_app
    apps = [(create_app(runtime, token), settings.get("port", 8776)),
            (create_monitor_app(project), settings.get("monitor_port", 8777)),
            (create_viewer_app(project), settings.get("viewer_port", 8778))]
    runners = []
    try:
        for app, port in apps:
            runner = web.AppRunner(app, access_log=None)
            await runner.setup()
            runners.append(runner)
            await web.TCPSite(runner, "127.0.0.1", port).start()
    except BaseException:
        for runner in reversed(runners):
            await runner.cleanup()
        raise
    return runners


async def run_cli(args, config, settings=None, *, provider_factory=None):
    project = Path(getattr(args, "project", None) or Path.cwd()).resolve()
    # Lock before opening sidecars: their recovery must never touch a live writer.
    with service_lock(project / "var/cli-service.lock"):
        return await _run_cli(args, config, settings, provider_factory=provider_factory)


async def _run_cli(args, config, settings=None, *, provider_factory=None):
    project = Path(getattr(args, "project", None) or Path.cwd()).resolve()
    settings = {**(config.get("companion") or {}), **(settings or {})}
    settings.setdefault("owner_id", "local-owner")
    settings.setdefault("owner_name", "你")
    settings.setdefault("port", 8776)
    settings.setdefault("monitor_port", 8777)
    settings.setdefault("viewer_port", 8778)
    settings.setdefault("capture_requests", True)
    settings.setdefault("cold_retention_days", 30)
    settings.setdefault("token_file", "var/cli-token.txt")
    settings.setdefault("engine_config", "config/cli-engine.toml")
    if getattr(args, "config", None):
        settings["engine_config"] = str(Path(args.config).resolve())
    settings.update(mode=args.mode, project_root=str(project))
    if getattr(args, "display_name", None):
        settings["display_name"] = args.display_name
    persona = Path(getattr(args, "persona_file", None) or project / "config/personas/xiaowennuan/persona.md")
    if not persona.is_file() and not getattr(args, "persona_file", None):
        persona = Path(__file__).resolve().parents[1] / "config/personas/xiaowennuan/persona.md"
    root = Path(args.root).resolve()
    config.setdefault("chat", {})["allow_paid"] = args.mode == "live"
    runtime = CliRuntime(root, settings, config, persona, agent=args.agent, user=args.user,
                         provider_factory=provider_factory)
    runners, proactive = [], None
    token_path = project / settings["token_file"]
    token_path.parent.mkdir(parents=True, exist_ok=True)
    if not token_path.exists():
        token_path.write_text(secrets.token_urlsafe(48), encoding="ascii")
    try:
        await runtime.bootstrap()
        write_active_config(project, settings, root, runtime.session.scope)
        if not getattr(args, "no_ui", False):
            runners = await start_ui(runtime, project, settings, token_path.read_text().strip())
        if getattr(args, "message", None) is not None:
            result = await runtime.receive_text(args.message, message_id=getattr(args, "message_id", None))
            await runtime.display_delivery(result)
            return result
        proactive = asyncio.create_task(runtime.poll_proactive())
        print(f"MYATRI CLI · {settings.get('display_name', '小温暖')} · {args.mode}", flush=True)
        print("/quit 退出；/reload 重载角色卡和提示词；/clear 清空工作上下文；/context 查看统计；/memory 关键词 检索。", flush=True)
        if runners:
            print(f"监视 http://127.0.0.1:{settings['monitor_port']}/  原文与控制 http://127.0.0.1:{settings['viewer_port']}/", flush=True)
        while True:
            try:
                text = (await asyncio.to_thread(input, input_prompt())).strip()
            except EOFError:
                break
            if text == "/quit":
                break
            if text == "/reload":
                print(json.dumps(await runtime.reload_runtime(runtime.session.scope), ensure_ascii=False))
            elif text == "/clear":
                print(json.dumps(await runtime.clear_runtime_context(runtime.session.scope), ensure_ascii=False))
            elif text == "/context":
                app = runtime.apps[runtime.session.scope]
                print(json.dumps(app.conversation.context.explain_context().get("context_stats", {}), ensure_ascii=False))
            elif text.startswith("/memory "):
                app = runtime.apps[runtime.session.scope]
                bundle = app.recall.recall(text[8:])
                print(json.dumps([{"ref": r.ref, "text": r.body_markdown[:400]} for r in bundle.records], ensure_ascii=False))
            elif text == "/retry-memory":
                print(json.dumps(await runtime.retry_summaries(runtime.session.scope), ensure_ascii=False))
            elif text == "/compact":
                print(json.dumps(await runtime.apps[runtime.session.scope].conversation.context.compactor.acompact(), default=str, ensure_ascii=False))
            elif text:
                print("  发送时间：" + datetime.now().astimezone().isoformat(timespec="seconds"), flush=True)
                try:
                    await runtime.display_delivery(await runtime.receive_text(text))
                except Exception as error:
                    print(f"本轮未完成，原话保留：{type(error).__name__}", file=sys.stderr)
    finally:
        if proactive:
            proactive.cancel()
            await asyncio.gather(proactive, return_exceptions=True)
        for runner in reversed(runners):
            await runner.cleanup()
        await runtime.close()
