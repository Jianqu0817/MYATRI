"""Read-only production audit, using synthetic data and an offline provider."""
import asyncio
import json
import tempfile
from pathlib import Path

from myatri.conversation.budget import TokenBudget
from myatri.conversation.compaction import Compactor
from myatri.conversation.context import ContextBuilder
from myatri.persona.state import PersonaState
from myatri.providers import BudgetExceeded, FixtureProvider, Gateway
from myatri.retrieval import RecallService
from myatri.storage import ArchiveStore


async def audit_existing_summary_overflow(root):
    store = ArchiveStore(root)
    PersonaState(store).initialize()
    for index in range(20):
        store.append_message("user" if index % 2 == 0 else "assistant",
                             f"第{index}轮，" + "普通对话内容持续保存。" * 14, f"turn_{index}")
    provider = FixtureProvider()
    builder = ContextBuilder(store, RecallService(store), gateway=Gateway(provider),
                             budget=TokenBudget(limit=11000, output_reserve=512, safety=512))
    await builder.abuild_context("别的话题")
    first = builder.compactor.current()
    assert first is not None
    first_count = len(store.list_records("summary"))
    for index in range(20, 40):
        store.append_message("user" if index % 2 == 0 else "assistant",
                             f"第{index}轮，" + "普通对话内容持续保存。" * 14, f"turn_{index}")
    error = None
    try:
        await builder.abuild_context("别的话题")
    except BudgetExceeded as exc:
        error = str(exc)
    blocked_count = len(store.list_records("summary"))
    assert error is not None, "expected to expose missing repeat compaction"
    assert blocked_count == first_count, "overflow did not attempt another summary"
    Compactor(store).compact()
    await builder.abuild_context("别的话题")
    return {"first_summary_source_count": len(first.payload["source_range"]),
            "raw_after_growth": len(store.list_records("raw_message")),
            "summaries_before_growth": first_count, "summaries_after_failed_build": blocked_count,
            "error": error, "manual_recompaction_restores_context": True,
            "archive_errors": store.verify_archive(), "external_api_calls": 0}


async def main():
    reports = Path(__file__).resolve().parent
    with tempfile.TemporaryDirectory(prefix="review_context_", dir=reports) as directory:
        result = await audit_existing_summary_overflow(Path(directory))
    target = reports / "review_context_2026-10-20.json"
    target.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=True))


if __name__ == "__main__":
    asyncio.run(main())
