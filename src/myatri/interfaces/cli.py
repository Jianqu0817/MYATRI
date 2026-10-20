from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path
import sys
from datetime import datetime

from myatri.app import Application, load_config
from myatri.contracts import JobSpec, Record
from myatri.interfaces.inspect import backup, doctor, import_record, inspect_record, restore_backup
from myatri.persona.patch import PersonaPatcher
from myatri.providers import ProviderError
from myatri.interfaces.terminal import chat_block, input_prompt, display_time


def output(value):
    if hasattr(value, "model_dump"):
        value = value.model_dump(mode="json")
    print(json.dumps(value, ensure_ascii=False, indent=2, default=str))


def parser():
    p = argparse.ArgumentParser(prog="myatri", description="MYATRI V1 本地持久角色与记忆；默认离线，无主动发送")
    p.add_argument("--root", default="var/atri")
    p.add_argument("--agent", default="atri")
    p.add_argument("--user", default="local")
    p.add_argument("--config")
    sub = p.add_subparsers(dest="command", required=True)
    init = sub.add_parser("init"); init.add_argument("--persona-file")
    chat = sub.add_parser("chat")
    chat.add_argument("--mode", choices=["offline", "live"], default="offline")
    chat.add_argument("--message")
    chat.add_argument("--message-id")
    chat.add_argument("--display-name", help="聊天窗口中的角色名称；身份仍由持久化角色卡决定")
    worker = sub.add_parser("worker")
    worker.add_argument("--once", action="store_true")
    worker.add_argument("--mode", choices=["offline", "live"], default="offline")
    memory = sub.add_parser("memory").add_subparsers(dest="action", required=True)
    memory.add_parser("list")
    mi = memory.add_parser("inspect"); mi.add_argument("id")
    im = memory.add_parser("import"); im.add_argument("file")
    re = memory.add_parser("rebuild-index"); re.add_argument("--space", choices=["tfidf", "bge"], default="tfidf"); re.add_argument("--model-path", default="var/models/bge-small-zh-v1.5")
    rb = memory.add_parser("rollback-index"); rb.add_argument("generation")
    recall = sub.add_parser("recall")
    recall.add_argument("query"); recall.add_argument("--explain", action="store_true")
    recall.add_argument("--historical", action="store_true"); recall.add_argument("--person")
    recall.add_argument("--date-from"); recall.add_argument("--date-to")
    recall.add_argument("--kind", action="append", dest="kinds")
    graph = sub.add_parser("graph"); graph.add_argument("action", choices=["inspect"]); graph.add_argument("--theme")
    reflect = sub.add_parser("reflect"); reflect.add_argument("--scope", default="all")
    reflect.add_argument("--mode", choices=["offline", "live"], default="offline")
    persona = sub.add_parser("persona").add_subparsers(dest="action", required=True)
    persona.add_parser("show")
    diff = persona.add_parser("diff"); diff.add_argument("before", type=int); diff.add_argument("after", type=int)
    restore = persona.add_parser("restore"); restore.add_argument("version", type=int)
    edit = persona.add_parser("edit"); edit.add_argument("--entry", required=True); edit.add_argument("--text", required=True); edit.add_argument("--reason", required=True)
    compact = sub.add_parser("compact"); compact.add_argument("--preserve", nargs="*", default=[])
    compact.add_argument("--mode", choices=["offline", "live"], default="offline")
    jobs = sub.add_parser("jobs"); jobs.add_argument("action", choices=["list", "retry", "cancel"])
    jobs.add_argument("id", nargs="?")
    jobs.add_argument("--regenerate", action="store_true", help="explicitly discard saved result when retrying")
    state = sub.add_parser("state").add_subparsers(dest="action", required=True)
    sl = state.add_parser("list"); sl.add_argument("--status")
    si = state.add_parser("inspect"); si.add_argument("id"); si.add_argument("--activation-trace", action="store_true")
    sd = state.add_parser("dismiss"); sd.add_argument("id"); sd.add_argument("--reason", required=True)
    context = sub.add_parser("context")
    context.add_argument("--mode", choices=["offline", "live"], default="offline")
    emotion = sub.add_parser("emotion").add_subparsers(dest="action", required=True)
    es = emotion.add_parser("show"); es.add_argument("--at"); es.add_argument("--snapshot")
    emotion.add_parser("history")
    ea = emotion.add_parser("appraise"); ea.add_argument("event_ref")
    ea.add_argument("--mode", choices=["offline", "live"], default="offline")
    er = emotion.add_parser("dismiss"); er.add_argument("appraisal_ref"); er.add_argument("--reason", required=True)
    protocol = sub.add_parser("protocol"); protocol.add_argument("action", choices=["inspect"]); protocol.add_argument("turn_id")
    sub.add_parser("doctor")
    cost = sub.add_parser("cost"); cost.add_argument("action", choices=["inspect"], nargs="?", default="inspect")
    ba = sub.add_parser("backup"); ba.add_argument("--output", required=True)
    rs = sub.add_parser("restore"); rs.add_argument("--input", required=True); rs.add_argument("--target", required=True)
    ev = sub.add_parser("eval"); ev.add_argument("--suite", choices=["baseline", "demo", "all"], default="all")
    ev.add_argument("--mode", choices=["offline", "live"], default="offline"); ev.add_argument("--output", default="reports")
    ev.add_argument("--neural-path")
    model = sub.add_parser("models"); model.add_argument("action", choices=["download"]); model.add_argument("--path", default="var/models/bge-small-zh-v1.5")
    return p


async def run(args):
    if args.command == "restore":
        return output({"restored": restore_backup(args.input, args.target)})
    if args.command == "eval":
        if args.mode == "live":
            raise ProviderError("live evaluation disabled under current authorization")
        from myatri.evaluation import evaluate
        return output(await evaluate(Path(args.output), neural_path=args.neural_path, suite=args.suite))
    if args.command == "models":
        from myatri.providers.local_onnx import download_model
        return output(download_model(Path(args.path)))
    config = load_config(args.config)
    if args.command == "init" and args.persona_file:
        from myatri.persona.state import PersonaState
        config["initial_persona_entries"] = PersonaState.parse_template(Path(args.persona_file).read_text(encoding="utf-8-sig"))
    app = Application(args.root, args.agent, args.user, mode=getattr(args, "mode", "offline"), config=config)
    command = args.command
    if command == "init":
        output({"root": str(app.root), "persona": app.persona.read_state().ref, "mode": "offline", "outreach": False})
    elif command == "chat":
        if args.message is not None:
            answer = await app.conversation.respond(args.message, message_id=args.message_id)
            output({"reply": answer.body_markdown, "ref": answer.ref})
            await app.drain()
            return
        print("MYATRI 离线fixture" if args.mode == "offline" else "MYATRI live（需单独启用付费配置）")
        print("输入 /quit 退出，/compact 手动压缩；原文即时落盘。")
        task = asyncio.create_task(app.run_background())
        try:
            while True:
                try:
                    text = await asyncio.to_thread(input, input_prompt())
                except EOFError:
                    break
                if task.done():
                    await task
                    raise ProviderError("background stopped unexpectedly; inspect jobs/doctor before restarting")
                if text == "/quit":
                    break
                if text == "/compact":
                    print("\n[系统] 手动压缩结果：")
                    output(await app.conversation.context.compactor.acompact())
                    continue
                if text.strip():
                    sent_at = datetime.now(app.conversation.context.timezone).isoformat(timespec="seconds")
                    print("  发送时间：" + display_time(sent_at))
                    try:
                        answer = await app.conversation.respond(text)
                        print(chat_block(args.display_name or args.agent, answer.body_markdown,
                                         app.conversation.context.message_time(answer)))
                    except ProviderError as exc:
                        print(chat_block("系统", "本轮未收到回复，已保留你发送的原话。\n" + str(exc), sent_at))
        finally:
            app.worker.stopping = True
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            if app.conversation.context.budget.anchor:
                app.queue.set_meta("context_token_anchor", app.conversation.context.budget.anchor)
            app.store.flush_projection()
    elif command == "worker":
        app.recover_pending()
        if args.once:
            output({"processed": await app.drain(), "jobs": app.queue.list_jobs()})
        else:
            await app.run_background()
    elif command == "memory":
        if args.action == "list":
            output([{"ref": r.ref, "kind": r.record_kind, "text": r.body_markdown[:100]} for r in app.store.list_records()])
        elif args.action == "inspect": output(inspect_record(app.store, args.id))
        elif args.action == "import": output(import_record(app.store, args.file))
        elif args.action == "rollback-index":
            app.index.rollback(args.generation); output(app.index.inspect())
        else:
            if args.space == "bge":
                from myatri.providers.local_onnx import LocalOnnxEmbeddingProvider
                app.index.provider = LocalOnnxEmbeddingProvider(Path(args.model_path))
                app.index.requested_space_id = app.index.provider.space_id
            else:
                app.index.provider = None
            await app.index.rebuild()
            app.queue.set_meta("embedding", {"backend": args.space, "path": str(Path(args.model_path).resolve())})
            output(app.index.inspect())
    elif command == "recall":
        output(app.recall.recall(args.query, filters={"include_historical": args.historical,
            "person": args.person, "date_from": args.date_from, "date_to": args.date_to, "kinds": args.kinds}))
    elif command == "graph": output(app.index.theme_materials(args.theme) if args.theme else app.index.inspect())
    elif command == "reflect":
        events = app.store.list_records("event")
        if args.scope != "all":
            if args.scope in app.index.themes:
                refs = app.index.themes[args.scope]["members"]
            else:
                refs = [app.store.get_record(args.scope).ref]
        else:
            refs = [r.ref for r in events]
        app.queue.enqueue(JobSpec(role="cycle", input_refs=refs, payload={"manual": True}))
        output({"processed": await app.drain(), "jobs": app.queue.list_jobs()})
    elif command == "persona":
        if args.action == "show": output(app.persona.read_state())
        elif args.action == "diff": output(app.persona.diff(args.before, args.after))
        elif args.action == "edit": output(PersonaPatcher(app.store).human_edit(args.entry, args.text, args.reason))
        else: output(PersonaPatcher(app.store).restore(args.version))
    elif command == "compact": output(await app.conversation.context.compactor.acompact(preserve_ids=args.preserve))
    elif command == "jobs":
        if args.action == "list":
            output(app.queue.list_jobs())
        elif not args.id:
            raise ValueError("jobs retry/cancel requires a job id")
        elif args.action == "retry":
            output(app.queue.retry_job(args.id, clear_result=args.regenerate))
        else:
            output(app.queue.cancel_job(args.id))
    elif command == "state":
        if args.action == "list": output([r.model_dump(mode="json") for r in app.states.list(status=args.status)])
        elif args.action == "inspect":
            result = inspect_record(app.store, args.id)
            if args.activation_trace:
                result["activations"] = [r.model_dump(mode="json") for r in app.store.list_records("activation") if any(ref.startswith(args.id+"@") for ref in r.source_refs)]
            output(result)
        else:
            record = app.store.get_record(args.id)
            output(app.states.review(args.id, base_revision=record.revision, status="discarded", reason=args.reason))
    elif command == "context":
        await app.conversation.context.abuild_context("当前关注")
        output(app.conversation.context.explain_context())
    elif command == "emotion":
        if args.action == "show":
            from myatri.contracts import parse_timestamp
            output(app.emotions.read(snapshot=args.snapshot, now=parse_timestamp(args.at) if args.at else None))
        elif args.action == "history":
            output([r.model_dump(mode="json") for r in app.store.list_records("emotion_appraisal")])
        elif args.action == "dismiss":
            proposal = app.emotions.propose_retraction(args.appraisal_ref, args.reason)
            if proposal:
                app.committer.submit_proposal(proposal)
            output({"retracted": args.appraisal_ref, "state": app.emotions.read()})
        else:
            event = app.store.get_record(args.event_ref.split("@")[0],
                revision=int(args.event_ref.split("@")[1]) if "@" in args.event_ref else None)
            if event.record_kind != "event":
                raise ValueError("emotion appraise requires an event")
            job_id = app.queue.enqueue(JobSpec(role="emotion", input_refs=[event.ref], priority=40, payload={"manual": True}))
            output({"job_id": job_id, "processed": await app.drain(), "state": app.emotions.read()})
    elif command == "protocol": output(app.queue.get_protocol(args.turn_id))
    elif command == "doctor": output(doctor(app))
    elif command == "cost": output(app.queue.usage())
    elif command == "backup": output({"backup": backup(app, args.output)})


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    args = parser().parse_args()
    try:
        asyncio.run(run(args))
    except (ValueError, KeyError, ProviderError, FileNotFoundError) as exc:
        print(json.dumps({"error": type(exc).__name__, "message": str(exc)}, ensure_ascii=False), file=sys.stderr)
        raise SystemExit(2)
    except KeyboardInterrupt:
        print("已停止；原文和队列保留，租约到期后可恢复。")


if __name__ == "__main__":
    main()
