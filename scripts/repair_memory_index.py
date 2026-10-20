"""Rebuild a derived local index without rewriting memory/persona or calling an LLM."""
import argparse
import asyncio
from datetime import datetime, timezone
import json
from pathlib import Path
import threading

from myatri.memory import MemoryIndex
from myatri.storage import ArchiveStore


async def repair(root, agent, user, model_path=None):
    root = Path(root).resolve()
    store = None
    for domain in (root / "domains").iterdir():
        commits = sorted((domain / "commits").glob("*.json"))
        if not commits:
            continue
        header = json.loads(commits[0].read_text(encoding="utf-8"))
        if (header["agent_id"], header["user_id"]) != (agent, user):
            continue
        store = ArchiveStore.__new__(ArchiveStore)
        store.root, store.domain_path = root, domain
        store.agent_id, store.user_id = agent, user
        store.manifest_path, store.db_path = domain / "commits", domain / "projection.sqlite3"
        store._thread_lock = threading.RLock()
        break
    if store is None:
        raise ValueError("No existing archive with the requested agent/user; nothing created")
    before, records = store._load(force=True)
    provider = None
    if model_path:
        from myatri.providers.local_onnx import LocalOnnxEmbeddingProvider
        provider = LocalOnnxEmbeddingProvider(Path(model_path).resolve())
    index = MemoryIndex(store, provider)
    pointer = index.path / "current.json"
    backup = None
    if pointer.exists():
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        backup = index.path / ("before-repair-" + stamp + ".json")
        backup.write_bytes(pointer.read_bytes())
    generation = await index.rebuild()
    after, retained = store._load(force=True)
    assert all(retained.get(ref) == row for ref, row in records.items())
    result = {"archive_verified": True, "original_revisions_preserved": len(records),
        "commits_before": len(before), "commits_after": len(after),
        "generation": generation, "index_sequence": index._sequence,
        "pointer_backup": str(backup) if backup else None,
        "indexed_rows": {view: len(data.rows) for view, data in index.indexes.items()},
        "llm_calls": 0, "persona_modified": False,
        "note": "Running processes may retain the old index in memory; reopen the chat/service to reload."}
    (index.path / "last-repair.json").write_text(json.dumps(result, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument("--agent", default="atri")
    parser.add_argument("--user", default="local")
    parser.add_argument("--model-path", type=Path)
    args = parser.parse_args()
    print(json.dumps(asyncio.run(repair(args.root, args.agent, args.user, args.model_path)), ensure_ascii=False))
