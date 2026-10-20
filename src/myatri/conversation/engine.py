from __future__ import annotations

import asyncio
import json

import jsonschema

from myatri.contracts import ModelRequest, uid
from myatri.providers.gateway import ProviderError, assistant_message, validate_protocol
from myatri.persona.temporary import resolve
from .context import ContextBuilder


TOOLS = [{"type": "function", "function": {"name": "recall", "description": "回忆带版本来源的本地材料",
    "parameters": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"], "additionalProperties": False}}},
    {"type": "function", "function": {"name": "read_record", "description": "按精确ID@revision读取原始记录",
    "parameters": {"type": "object", "properties": {"ref": {"type": "string"}}, "required": ["ref"], "additionalProperties": False}}}]


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
        self._lock = asyncio.Lock()

    async def respond(self, text, *, message_id=None):
        async with self._lock:
            raw = self.store.append_message("user", text, message_id=message_id)
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
            tools = TOOLS if self.enable_tools else []
            saved = self.protocol_store.get_protocol(raw.record_id) if self.protocol_store else None
            if saved and saved["status"] == "active":
                messages, snapshot, start_step = saved["messages"], saved["snapshot"], saved["steps"]
                validate_protocol(messages)
            else:
                messages, snapshot = await self.context.abuild_context(text, tools=tools)
                start_step = 0
            for step in range(start_step, self.max_steps):
                request = ModelRequest(messages=messages, tools=tools, role="foreground", purpose="conversation",
                                       budget_tokens=self.context.budget.limit, max_tokens=self.context.budget.output_reserve)
                self.context.budget.require(messages, tools)
                response = await self.gateway.generate(request)
                self.context.budget.calibrate(messages, response.usage, tools)
                messages.append(assistant_message(response))
                if not response.tool_calls:
                    validate_protocol(messages)
                    answer = self.store.append_message("assistant", response.content,
                        message_id="answer_" + raw.record_id, reply_to=raw.ref,
                        provider=response.provider, model=response.model, context_snapshot=snapshot)
                    if self.protocol_store:
                        self.protocol_store.save_protocol(raw.record_id, {"status": "completed", "snapshot": snapshot,
                            "steps": step+1, "messages": messages, "reply_ref": answer.ref})
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
                        else:
                            result = resolve(self.store, args["ref"], snapshot).model_dump(mode="json")
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
