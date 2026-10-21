from myatri.contracts import ModelRequest
from myatri.providers import FixtureProvider, Gateway


async def test_usage_log_records_switch_limits_and_stop_reason_without_reasoning_text():
    events = []
    provider = FixtureProvider([{"content": "ok", "usage": {"prompt_tokens": 123, "completion_tokens": 9},
        "provider_fields": {"reasoning_content": "PRIVATE REASONING"}}])
    request = ModelRequest(messages=[], thinking=False, max_tokens=512,
        budget_tokens=1000000, estimated_input_tokens=150)
    await Gateway(provider, usage_sink=events.append).generate(request)
    assert len(events) == 1
    log = events[0]
    assert log["thinking_enabled"] is False and log["reasoning_effort"] is None
    assert log["request_max_tokens"] == 512 and log["request_budget_tokens"] == 1000000
    assert log["finish_reason"] == "stop" and log["recorded_at"]
    assert log["reasoning_content_present"] is True
    assert "PRIVATE REASONING" not in str(log)
