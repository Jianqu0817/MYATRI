import asyncio
import json

import httpx
import pytest

from myatri.contracts import EmbeddingBatch, ModelRequest
from myatri.providers import DeepSeekProvider, FixtureProvider, Gateway, ProviderError, BudgetExceeded
from myatri.providers.gateway import assistant_message, validate_protocol


def test_tool_protocol_pairs_and_no_orphan():
    call = {"id": "call1", "type": "function", "function": {"name": "read_record", "arguments": "{}"}}
    partial = [{"role": "assistant", "content": "", "tool_calls": [call]}]
    with pytest.raises(ProviderError): validate_protocol(partial)
    with pytest.raises(ProviderError): validate_protocol([{"role": "tool", "tool_call_id": "other", "content": ""}])
    validate_protocol([*partial, {"role": "tool", "tool_call_id": "call1", "content": "{}"}])


async def test_transport_retry_truncation_and_schema_errors():
    seen = []
    def transport(request):
        seen.append(request)
        if len(seen) == 1:
            return httpx.Response(429, request=request)
        return httpx.Response(200, json={"choices": [{"message": {"content": '{"ok":true}', "reasoning_content": "protocol-only"}, "finish_reason": "stop"}], "usage": {"total_tokens": 4}}, request=request)
    async with httpx.AsyncClient(transport=httpx.MockTransport(transport)) as client:
        provider = DeepSeekProvider(model="test-model", api_key="test-key", allow_paid=True, client=client)
        response = await Gateway(provider, retry_delay=0).generate(ModelRequest(messages=[{"role": "user", "content": "JSON test"}], output_schema={"type": "object", "required": ["ok"]}))
    assert len(seen) == 2
    assert assistant_message(response)["reasoning_content"] == "protocol-only"
    for item in [{"content": '{"ok":true}', "finish_reason": "length"}, {"content": "{}"}]:
        with pytest.raises(ProviderError):
            await Gateway(FixtureProvider([item])).generate(ModelRequest(messages=[], output_schema={"type": "object", "required": ["ok"]}))


async def test_api_and_budget_fail_closed():
    with pytest.raises(ProviderError, match="disabled"):
        await DeepSeekProvider(model="unused", api_key="never-send").generate(ModelRequest(messages=[]))
    gateway = Gateway(FixtureProvider(delay=0.03), daily_token_limit=800)
    results = await asyncio.gather(*[gateway.generate(ModelRequest(messages=[], max_tokens=100)) for _ in range(8)], return_exceptions=True)
    assert any(isinstance(r, BudgetExceeded) for r in results)
    assert gateway.reserved_tokens == 0
    with pytest.raises(BudgetExceeded):
        await Gateway(FixtureProvider()).generate(ModelRequest(messages=[{"role": "user", "content": "中"*10000}], budget_tokens=100))


async def test_background_limit_does_not_block_foreground():
    provider = FixtureProvider(delay=0.03)
    gateway = Gateway(provider, background_limit=1, foreground_limit=1)
    background = asyncio.create_task(gateway.generate(ModelRequest(messages=[], role="reflection")))
    await asyncio.sleep(0.001)
    foreground = await gateway.generate(ModelRequest(messages=[]))
    assert foreground.provider == "fixture"
    await background


def test_embedding_metadata_rejects_bad_batch():
    with pytest.raises(ValueError):
        EmbeddingBatch(vectors=[[1, 2]], space_id="a", model="a", model_revision="1", dimension=3)
    with pytest.raises(ValueError):
        EmbeddingBatch(vectors=[[float("nan")]], space_id="a", model="a", model_revision="1", dimension=1)
