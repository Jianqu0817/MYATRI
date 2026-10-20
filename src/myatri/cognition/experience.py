from __future__ import annotations

import json
import re

from myatri.contracts import Event, ModelRequest, Proposal, Record, SourceSpan, digest, uid
from myatri.prompts import load_prompt
from myatri.providers import BudgetExceeded
from .materials import json_bytes, prefix_bytes, select_materials


class IngestProgressPending(BudgetExceeded):
    """A bounded batch was checkpointed; another batch remains, not all done."""

    def __init__(self, message):
        super().__init__(message, reason="ingest_pending")


def source_windows(text, *, max_bytes=3600, overlap_bytes=300):
    start = 0
    while start < len(text):
        fragment = prefix_bytes(text[start:], max_bytes)
        end = start + len(fragment)
        yield start, end, fragment
        if end == len(text):
            break
        overlap = len(prefix_bytes(fragment[::-1], overlap_bytes))
        start = max(start + 1, end - overlap)


EXPERIENCE_SCHEMA = {
    "type": "object", "required": ["events"], "additionalProperties": False,
    "properties": {"events": {"type": "array", "items": {
        "type": "object", "required": ["summary", "quote", "reality_scope", "occurred_at", "event_key"],
        "properties": {"summary": {"type": "string", "minLength": 1}, "quote": {"type": "string", "minLength": 1},
                       "reality_scope": {"enum": ["reported", "observed", "fictional", "quoted"]},
                       "occurred_at": {"type": ["string", "null"]}, "event_key": {"type": "string"},
                       "existing_event_ref": {"type": ["string", "null"]},
                       "participants": {"type": "array", "items": {"type": "string"}},
                       "interpretation": {"type": "string"}, "feeling": {"type": "string"},
                       "uncertainty": {"type": "array", "items": {"type": "string"}}}, "additionalProperties": False}}}}


class ExperienceOrganizer:
    def __init__(self, store, gateway):
        self.store, self.gateway = store, gateway

    async def _bounded_extract(self, message, snapshot, existing, *, max_new_chunks=8):
        results, checkpoints, new_chunks = [], [], 0
        for start, end, fragment in source_windows(message.body_markdown):
            chunk_id = "run_exp_chunk_" + digest([message.ref, start, end, digest(fragment), "bounded-v1"])[:24]
            try:
                checkpoint = self.store.get_record(chunk_id)
            except KeyError:
                if new_chunks >= max_new_chunks:
                    raise IngestProgressPending("A1原文分批进度已保存；仍有未处理窗口，须续批，未标记整条消息已完成")
                selection = select_materials(self.store, [r.ref for r in existing], snapshot=snapshot,
                    query=fragment, required_refs=[r.ref for r in existing if r.body_markdown.strip() == fragment.strip()][-1:],
                    max_bytes=4200, max_records=4, max_record_bytes=1200, include_counters=False)
                payload = {"message": {"ref": message.ref, "record_kind": "raw_message", "role": "user", "text": fragment},
                           "source_window": {"start": start, "end": end, "total_chars": len(message.body_markdown)},
                           "existing_events": selection.material, "selection": selection.metadata()}
                request = ModelRequest(role="experience", purpose="A1", output_schema=EXPERIENCE_SCHEMA,
                    messages=[{"role": "system", "content": load_prompt("experience") +
                        "\n整理本次原文窗口，JSON输出。quote必须逐字位于窗口text，不引用未展示内容。区分转述/虚构。"
                        "日期未知null。同一经历重提可用已展示existing_event_ref；实际后续是新事件。"
                        "旧事件候选不是全量；摘录不能当完整记录。窗口可能重叠，不可把重叠当独立事件。"},
                              {"role": "user", "content": json.dumps(payload, ensure_ascii=False)}])
                while payload["existing_events"] and json_bytes(request.model_dump(mode="json")) + request.max_tokens > request.budget_tokens:
                    payload["existing_events"].pop()
                    selection.sources.pop()
                    selection.omitted_count += 1
                    if "为原文窗口预算进一步省略旧候选。" not in selection.limitations:
                        selection.limitations.append("为原文窗口预算进一步省略旧候选。")
                    payload["selection"] = selection.metadata()
                    request.messages[1]["content"] = json.dumps(payload, ensure_ascii=False)
                response = await self.gateway.generate(request)
                data = json.loads(response.content)
                available = {row["ref"] for row in payload["existing_events"]}
                for item in data["events"]:
                    if item["quote"] not in fragment:
                        raise ValueError("A1 quote not found verbatim in persisted raw source window")
                    if item.get("existing_event_ref") and item["existing_event_ref"] not in available:
                        raise ValueError("A1 references an unshown old event")
                checkpoint = Record(record_id=chunk_id, record_kind="cognitive_run", agent_id=message.agent_id,
                    user_id=message.user_id, source_refs=[message.ref, *sorted(available)],
                    payload={"role": "A1_chunk", "message_ref": message.ref, "start": start, "end": end,
                        "output": data, "provider": response.provider, "model": response.model,
                        "prompt_version": "experience/v1", "materials": payload["selection"]})
                self.store.commit([checkpoint], idempotency_key=chunk_id, expected={chunk_id: 0})
                new_chunks += 1
            checkpoints.append(checkpoint)
            for item in checkpoint.payload["output"]["events"]:
                results.append({**item, "_window_start": start, "_window_end": end,
                    "_generator": {"provider": checkpoint.payload["provider"], "model": checkpoint.payload["model"],
                                   "prompt_version": checkpoint.payload["prompt_version"], "run_id": checkpoint.record_id}})
        return {"events": results}, checkpoints

    async def propose(self, message: Record, *, fixture: dict | None = None) -> Proposal:
        if message.record_kind != "raw_message" or message.payload.get("role") != "user":
            raise ValueError("only user raw messages enter A1; role output is not external evidence")
        snapshot = self.store.snapshot()
        existing = self.store.list_records("event", snapshot=snapshot)
        if fixture is None and getattr(self.gateway.provider, "name", "") == "fixture":
            # Transparent lexical fixture: literal repeated content deduplicates; no inferred date/emotion.
            fixture = {"events": [{"summary": message.body_markdown, "quote": message.body_markdown,
                                    "event_key": digest(re.sub(r"\s+", "", message.body_markdown)),
                                    "occurred_at": None, "reality_scope": "reported", "participants": []}]}
        checkpoints = []
        if fixture is not None:
            import jsonschema
            jsonschema.validate(fixture, EXPERIENCE_SCHEMA)
            data, provider, model = fixture, "fixture", "literal-organizer-v1"
        else:
            data, checkpoints = await self._bounded_extract(message, snapshot, existing)
            provider = checkpoints[-1].payload["provider"] if checkpoints else "local-policy"
            model = checkpoints[-1].payload["model"] if checkpoints else "empty-source-v1"
            snapshot = self.store.snapshot()
        run_id = "run_exp_" + digest({"message": message.ref, "version": "v1"})[:24]
        generator = {"provider": provider, "model": model, "prompt_version": "experience/v1", "run_id": run_id}
        run = Record(record_id=run_id, record_kind="cognitive_run", agent_id=message.agent_id,
                     user_id=message.user_id, source_refs=[message.ref, *[r.ref for r in checkpoints]],
                     payload={"role": "A1", "snapshot": snapshot, "decision": "propose",
                              "source_coverage": {"start": 0, "end": len(message.body_markdown), "complete": True},
                              "limitations": ["窗口完成表示全文均已提交抽取，不保证模型穷尽所有语义事件；原文完整保留。"]})
        records, expected = [run], {message.record_id: message.revision}
        by_fingerprint = {r.payload["event_fingerprint"]: r for r in existing}
        by_ref = {r.ref: r for r in existing}
        seen_spans = set()
        for item in data["events"]:
            quote = item["quote"]
            start = message.body_markdown.find(quote, item.get("_window_start", 0), item.get("_window_end", len(message.body_markdown)))
            if start < 0:
                raise ValueError("A1 quote not found verbatim in persisted raw source")
            span_key = (start, start + len(quote), item["reality_scope"])
            if span_key in seen_spans:
                continue
            seen_spans.add(span_key)
            item_generator = item.get("_generator", generator)
            fingerprint = digest({"key": item["event_key"], "occurred_at": item["occurred_at"],
                                  "reality": item["reality_scope"], "participants": sorted(item.get("participants", [])),
                                  # Model-generated keys are proposals, not a global identity
                                  # oracle. Semantic cross-message merging must name an old
                                  # candidate it actually saw; only the transparent lexical
                                  # fixture uses its deterministic repeat identity.
                                  **({"source_span": [message.ref, start, start + len(quote)]}
                                     if fixture is None else {})})
            prior = by_ref.get(item.get("existing_event_ref")) or by_fingerprint.get(fingerprint)
            if item.get("existing_event_ref") and not prior:
                raise ValueError("unknown existing event ref")
            if prior:
                if prior.ref in by_ref:
                    expected[prior.record_id] = prior.revision
                if prior.payload["reality_scope"] != item["reality_scope"]:
                    raise ValueError("reality scope mismatch in event merge")
                interpretation = Record(record_id="repeat_" + digest([message.ref, prior.ref])[:24],
                    record_kind="interpretation", agent_id=message.agent_id, user_id=message.user_id,
                    author_kind="model", generator=item_generator, source_refs=[prior.ref, message.ref, run.ref],
                    body_markdown=item.get("interpretation") or "同一经历再次提及，保留新增原文，不新增事件根。",
                    payload={"event_refs": [prior.ref], "source_spans": [SourceSpan(message_ref=message.ref, start=start,
                             end=start + len(quote), quote=quote).model_dump()], "repeated_mention": True,
                             "uncertainty": item.get("uncertainty", []), **({"feeling": item["feeling"]} if item.get("feeling") else {})})
                if interpretation.record_id not in {r.record_id for r in records}:
                    records.append(interpretation)
                continue
            event = Event(occurred_at=item["occurred_at"], time_precision="unknown" if not item["occurred_at"] else "reported",
                          participants=item.get("participants", []), fact_summary=item["summary"],
                          source_spans=[SourceSpan(message_ref=message.ref, start=start, end=start + len(quote), quote=quote)],
                          event_fingerprint=fingerprint, reality_scope=item["reality_scope"])
            record = Record(record_id="event_" + fingerprint[:24], record_kind="event",
                            agent_id=message.agent_id, user_id=message.user_id, author_kind="model",
                            generator=item_generator, source_refs=[message.ref], body_markdown=event.fact_summary, payload=event.model_dump())
            records.append(record)
            expected[record.record_id] = 0
            by_fingerprint[fingerprint] = record
            if item.get("interpretation") or item.get("feeling"):
                interpreted = Record(record_id="interpret_" + digest([record.ref, message.ref])[:24], record_kind="interpretation",
                    agent_id=message.agent_id, user_id=message.user_id, author_kind="model", generator=item_generator,
                    source_refs=[record.ref, message.ref, run.ref], body_markdown=item.get("interpretation") or item["feeling"],
                    payload={"event_refs": [record.ref], "interpretation_text": item.get("interpretation", ""),
                             "feeling": item.get("feeling", ""), "uncertainty": item.get("uncertainty", []),
                             "source_spans": [span.model_dump() for span in event.source_spans]})
                records.append(interpreted)
                expected[interpreted.record_id] = 0
        return Proposal(proposal_id="proposal_" + run_id, base_snapshot=snapshot, read_versions=expected,
                        records=records, role="A1", run_id=run_id)
