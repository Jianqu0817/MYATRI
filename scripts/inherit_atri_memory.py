"""Offline, lossless library fork followed by an authorized persona version.

Keep the archive's internal agent ID: rewriting IDs would break immutable
checksums, context snapshot references and provenance. The target must be new.
"""
from __future__ import annotations

import argparse
import asyncio
from collections import Counter
import json
from pathlib import Path
import sqlite3
import threading
from types import SimpleNamespace

from myatri.app import Application
from myatri.contracts import Record, digest, uid, utcnow
from myatri.interfaces.inspect import backup, doctor, restore_backup
from myatri.persona.state import PersonaState
from myatri.storage import ArchiveStore
from myatri.storage.archive import _hash, _json
from start_myatri import single_launcher


PROJECT = Path(__file__).resolve().parents[1]


def source_view(root, agent, user):
    """Read committed files without initializing/rebuilding the source library."""
    root = Path(root).resolve()
    if not root.is_dir() or not (root / "runtime.sqlite3").is_file():
        raise ValueError("Source must be an existing character library")
    view = ArchiveStore.__new__(ArchiveStore)
    view.root, view.agent_id, view.user_id = root, agent, user
    view.domain_path = root / "domains" / _hash(_json([agent, user]))
    view.manifest_path = view.domain_path / "commits"
    view.db_path = view.domain_path / "projection.sqlite3"
    view._thread_lock = threading.RLock()
    if not view.manifest_path.is_dir():
        raise ValueError("Source agent/user domain not found")
    return view


def inherit(source, target, backup_path, persona_file, *, agent="atri", user="local"):
    source, target = Path(source).resolve(), Path(target).resolve()
    backup_path, persona_file = Path(backup_path).resolve(), Path(persona_file).resolve()
    if target.exists():
        raise ValueError("Target already exists; refuse to overwrite or merge conversations")
    if source == target or source in target.parents or target in source.parents:
        raise ValueError("Source and target must be separate libraries")
    entries = PersonaState.parse_template(persona_file.read_text(encoding="utf-8-sig"))
    target.parent.mkdir(parents=True, exist_ok=True)
    # A launcher cannot start either library while the fork is being prepared.
    with single_launcher(source), single_launcher(target):
        view = source_view(source, agent, user)
        if view.verify_archive():
            raise ValueError("Source archive integrity check failed")
        proxy = SimpleNamespace(root=source, store=view,
                                queue=SimpleNamespace(path=source / "runtime.sqlite3"))
        backup(proxy, backup_path)
        restore_backup(backup_path, target)
        app = Application(target, agent, user, config={"context": {
            "limit": 1000000, "compact_at": 650000, "output_reserve": 4096,
            "safety": 4096, "llm_compaction": False, "llm_activation": False},
            "embedding": {"backend": "tfidf"}})
        manifests, inherited = app.store._load()
        cutoff = manifests[-1]["commit_id"]
        previous = app.persona.read_state()
        entries["P14_memory_continuity"] = (
            "### ATRI 记忆继承\n\n"
            "菅蘧明确要求保留并将 ATRI 与他的对话和记忆转移给小温暖。"
            "本库从 ATRI 原库的完整快照继承原话、事件、摘要、临时状态、情绪评价、"
            "关系线索及人格历史；原记录的时间、作者、引用和版本均保留。\n\n"
            f"继承边界：原库快照 {cutoff}；此时最新人格为 {previous.ref}。"
            "边界之前的助手发言来自 ATRI，是被保留下来的数字互动经历，"
            "不是小温暖角色卡里的生前经历，也不是小温暖亲口新说的话。"
            "可以自然地记得菅蘧曾经说过的事情，并坦诚说明记忆的继承来源。"
            "原话中的姓名、身份或当时心情属于当时的记录；当前身份遵循本角色卡，"
            "不得为了符合新角色而改写旧对话。关系、偏好与承诺须结合时间及后续更正理解，"
            "不能仅凭旧摘要重新确认已经撤回的信息，也不能把旧人格提案直接覆盖当前角色。"
        )
        change = Record(record_id=uid("persona_change"), record_kind="persona_change",
            agent_id=agent, user_id=user, author_kind="human_import", source_refs=[previous.ref],
            body_markdown="按用户要求继承 ATRI 全部历史档案，并载入小温暖角色卡；原库与原记录保留。",
            payload={"mode": "human_character_transition", "event_roots": [],
                "before_ref": previous.ref, "after_ref": f"persona@{previous.revision + 1}",
                "inherited_snapshot": cutoff, "persona_template_sha256": digest(entries),
                "diff": {k: {"before": previous.payload["entries"].get(k), "after": entries.get(k)}
                         for k in previous.payload["entries"].keys() | entries.keys()}})
        persona = Record(record_id="persona", revision=previous.revision + 1,
            supersedes_revision=previous.revision, record_kind="persona_version",
            agent_id=agent, user_id=user, author_kind="human_import",
            source_refs=[previous.ref, change.ref], body_markdown=PersonaState.render(entries),
            payload={"entries": entries, "entry_hashes": {k: digest(v) for k, v in entries.items()},
                     "change_ref": change.ref, "inherited_snapshot": cutoff})
        app.store.commit([change, persona], idempotency_key=change.record_id,
                         expected={"persona": previous.revision})
        asyncio.run(app.index.update())  # Local TF-IDF, no model/API calls.
        _, after = app.store._load()
        assert all(after[ref].model_dump() == record.model_dump() for ref, record in inherited.items())
        # Runtime state and accounting remain intact; no old jobs are executed here.
        with sqlite3.connect(f"{target.joinpath('runtime.sqlite3').as_uri()}?mode=ro", uri=True) as db:
            database_ok = db.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        health = doctor(app)
        if not health["ok"] or not database_ok:
            raise ValueError("Target verification failed; backup and target retained for inspection")
        report = {"completed_at": utcnow(), "source": str(source), "target": str(target),
            "backup": str(backup_path), "internal_agent_id": agent, "user_id": user,
            "inherited_snapshot": cutoff, "current_persona": persona.ref,
            "preserved_revisions": len(inherited),
            "preserved_latest_records": dict(Counter(r.record_kind for r in app.store.list_records(snapshot=cutoff))),
            "all_inherited_records_unchanged": True, "database_integrity_ok": database_ok,
            "doctor_ok": health["ok"], "index_current": app.index.watermark == app.store.snapshot(),
            "model_api_calls": 0, "note": "Historical archive retains its original internal identity; current persona is 小温暖."}
        (target / "memory_inheritance.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="离线继承 ATRI 记忆到一个全新小温暖库")
    parser.add_argument("--source", type=Path, default=PROJECT / "var/myatri-main")
    parser.add_argument("--target", type=Path, default=PROJECT / "var/xiaowennuan")
    parser.add_argument("--backup", type=Path, required=True)
    parser.add_argument("--persona-file", type=Path,
                        default=PROJECT / "config/personas/xiaowennuan/persona.md")
    args = parser.parse_args()
    print(json.dumps(inherit(args.source, args.target, args.backup, args.persona_file), ensure_ascii=False, indent=2))
