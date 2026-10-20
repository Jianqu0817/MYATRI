from __future__ import annotations

import asyncio
import json

import jsonschema

from myatri.contracts import ModelRequest
from myatri.providers.gateway import ProviderError, assistant_message, validate_protocol
from myatri.persona.temporary import resolve
from .context import ContextBuilder


TOOLS = [{"type": "function", "function": {"name": "recall", "description": "回忆带版本来源的本地材料",
    "parameters": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"], "additionalProperties": False}}},
    {"type": "function", "function": {"name": "read_record", "description": "按精确ID@revision读取原始记录",
    "parameters": {"type": "object", "properties": {"ref": {"type": "string"},
        "offset": {"type": "integer", "minimum": 0},
        "limit": {"type": "integer", "minimum": 1, "maximum": 800}},
        "required": ["ref"], "additionalProperties": False}}}]


def read_record_page(store, ref, snapshot=None, *, offset=None, limit=None):
    """Keep small-record compatibility; page large text without dropping provenance."""
    if offset is not None and (type(offset) is not int or offset < 0):
        raise ValueError("offset must be a nonnegative integer")
    if limit is not None and (type(limit) is not int or not 1 <= limit <= 800):
        raise ValueError("limit must be between 1 and 800")
    record = resolve(store, ref, snapshot)
    full = record.model_dump(mode="json")
    if offset is None and limit is None and len(json.dumps(full, ensure_ascii=False).encode()) <= 6000:
        return full
    body = record.body_markdown
    content_field = "body_markdown"
    if not body:
        body = json.dumps(record.payload, ensure_ascii=False, sort_keys=True)
        content_field = "payload_json"
    offset, limit = offset or 0, limit or 800
    page = {"ref": record.ref, "record_kind": record.record_kind,
        "agent_id": record.agent_id, "user_id": record.user_id,
        "author_kind": record.author_kind, "created_at": record.created_at,
        "content_field": content_field, "offset": offset, "total_chars": len(body),
        "source_refs": record.source_refs[:10], "source_ref_count": len(record.source_refs),
        "source_refs_complete": len(record.source_refs) <= 10,
        "content_hash": record.content_hash}
    payload = {}
    for key in ("role", "reality_scope", "participants", "event_refs"):
        value = record.payload.get(key)
        if isinstance(value, str):
            payload[key] = value[:160]
        elif isinstance(value, list):
            payload[key] = [str(item)[:160] for item in value[:10]]
    for key in ("channel_source", "attribution"):
        value = record.payload.get(key)
        if isinstance(value, dict):
            payload[key] = {field: value[field][:160] if isinstance(value[field], str) else value[field]
                           for field in ("sender_id", "sender_name", "message_id", "speaker_id",
                            "subject_id", "attribution", "confirmed", "source_message_id")
                           if field in value and isinstance(value[field], (str, bool, type(None)))}
    if payload:
        page["payload"] = payload
    chunk = body[offset:offset + limit]
    while True:
        end = offset + len(chunk)
        page.update(body_markdown=chunk, next_offset=end if end < len(body) else None)
        if len(json.dumps(page, ensure_ascii=False).encode()) <= 6000 or len(chunk) <= 1:
            return page
        chunk = chunk[:max(1, len(chunk) // 2)]


class Conversation:
    def __init__(self, store, gateway, recall, index=None, on_message=None, *, max_steps=4, enable_tools=True, protocol_store=None, context_options=None, on_answer=None):
        self.store, self.gateway, self.recall = store, gateway, recall
        self.context = ContextBuilder(store, recall, index, gateway=gateway, options=context_options)
        self.on_message = on_message
        # Synchronous durable-enqueue hook. It may run again after a crash or
        # stable-message retry, so the consumer owns its idempotency key.
        self.on_answer = on_answer
        self.max_steps, self.enable_tools = max_steps, enable_tools
        self.protocol_store = protocol_store
        self.tool_handlers = {}
        self.reply_guard = None
        self._lock = asyncio.Lock()
        if protocol_store:
            self.context.budget.anchor = protocol_store.get_meta("context_token_anchor")

    async def respond(self, text, *, message_id=None, metadata=None):
        async with self._lock:
            if metadata is not None and not isinstance(metadata, dict):
                raise ValueError("message metadata must be a dict")
            if metadata and set(metadata) & {"role", "content", "message_id"}:
                raise ValueError("message metadata cannot override the conversation identity")
            raw = self.store.append_message("user", text, message_id=message_id, **(metadata or {}))
            try:
                answer = self.store.get_record("answer_" + raw.record_id)
            except KeyError:
                pass
            else:
                if self.on_answer:
                    self.on_answer(answer)
                return answer
            # Queue ingestion before API wait; user text remains safe if the provider fails.
            if self.on_message:
                self.on_message(raw)
            tools = [*TOOLS, *[entry[0] for entry in self.tool_handlers.values()]] if self.enable_tools else []
            completed = sum(1 for r in self.store.list_records("raw_message")
                            if r.payload.get("role") == "assistant" and r.payload.get("reply_to"))
            checkpoint = (completed + 1) % self.context.trace_every_turns == 0
            saved = self.protocol_store.get_protocol(raw.record_id) if self.protocol_store else None
            if saved and saved["status"] == "active":
                messages, snapshot, start_step = saved["messages"], saved["snapshot"], saved["steps"]
                validate_protocol(messages)
            else:
                messages, snapshot = await self.context.abuild_context(text, tools=tools, persist_activation=checkpoint)
                start_step = 0
            for step in range(start_step, self.max_steps):
                reply_policy = self.context.reply_policy
                output_tokens = self.context.budget.output_reserve
                if reply_policy.maximum:
                    output_tokens = min(output_tokens, reply_policy.max_tokens)
                request = ModelRequest(messages=messages, tools=tools, role="foreground", purpose="conversation",
                                       budget_tokens=self.context.budget.limit, max_tokens=output_tokens,
                                       estimated_input_tokens=self.context.budget.estimate(messages, tools))
                self.context.budget.require(messages, tools)
                response = await self.gateway.generate(request)
                self.context.budget.calibrate(messages, response.usage, tools)
                if self.protocol_store and checkpoint:
                    self.protocol_store.set_meta("context_token_anchor", self.context.budget.anchor)
                if not response.tool_calls:
                    if self.reply_guard is not None:
                        checked = await self.reply_guard(response.content, raw, messages)
                        response = response.model_copy(update={"content": checked})
                    response = response.model_copy(update={"content": reply_policy.prepare(response.content)})
                    if not response.content:
                        raise ProviderError("empty reply after metadata removal; raw user message preserved")
                messages.append(assistant_message(response))
                if not response.tool_calls:
                    validate_protocol(messages)
                    answer = self.store.append_message("assistant", response.content,
                        message_id="answer_" + raw.record_id, reply_to=raw.ref,
                        provider=response.provider, model=response.model, context_snapshot=snapshot,
                        **({"quality_review": self.reply_guard.last_check} if self.reply_guard is not None
                           and hasattr(self.reply_guard, "last_check") else {}))
                    if self.protocol_store:
                        protocol = {"status": "completed", "snapshot": snapshot,
                            "steps": step+1, "reply_ref": answer.ref, "sent_at": raw.created_at,
                            "replied_at": answer.created_at, "full_checkpoint": checkpoint}
                        if checkpoint:
                            protocol["messages"] = messages
                            protocol["context"] = self.context.explain_context()
                        self.protocol_store.save_protocol(raw.record_id, protocol)
                    if checkpoint:
                        self.store.flush_projection()
                    if self.on_answer:
                        self.on_answer(answer)
                    return answer
                for call in response.tool_calls:
                    try:
                        name = call["function"]["name"]
                        definition = next(t["function"] for t in tools if t["function"]["name"] == name)
                        args = json.loads(call["function"]["arguments"])
                        jsonschema.validate(args, definition["parameters"])
                        if name == "recall":
                            result = self.recall.recall(args["query"], snapshot=snapshot, budget=1800).model_dump(mode="json")
                        elif name in self.tool_handlers:
                            result = self.tool_handlers[name][1](**args)
                        else:
                            result = read_record_page(self.store, args["ref"], snapshot,
                                offset=args.get("offset"), limit=args.get("limit"))
                        # Bounded result, without truncating JSON/protocol fields.
                        encoded = json.dumps(result, ensure_ascii=False)
                        if len(encoded.encode("utf-8")) > 6000:
                            result = {"error": "record exceeds tool result budget", "ref": args.get("ref"), "suggestion": "use recall with narrower query"}
                    except (ValueError, KeyError, StopIteration, jsonschema.ValidationError) as exc:
                        result = {"error": type(exc).__name__, "message": "tool arguments or source invalid"}
                    messages.append({"role": "tool", "tool_call_id": call["id"], "content": json.dumps(result, ensure_ascii=False)})
                if self.protocol_store:
                    self.protocol_store.save_protocol(raw.record_id, {"status": "active", "snapshot": snapshot,
                        "steps": step+1, "messages": messages})
            raise ProviderError("tool step limit reached; raw user message preserved, no fictitious reply committed")
