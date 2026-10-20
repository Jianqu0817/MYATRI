import json

import pytest

from myatri.app import Application
from myatri.cognition.temporary_state import TemporaryStateAgent
from myatri.providers import Gateway, FixtureProvider, ProviderError


async def test_actual_failure_shape_active_state_is_rejected_by_explicit_schema(tmp_path):
    app = Application(tmp_path)
    payload = {"decision": "propose", "reason": "synthetic", "temporary_entries": [
        {"text": "暂定想法", "entry_ref": "new@1", "origin_kind": "generated_idea", "origin_refs": [], "status": "active"}]}
    provider = FixtureProvider([{"content": json.dumps(payload)}])
    raw = app.store.append_message("user", "我们先讨论下次安排", message_id="schema_material")
    with pytest.raises(ProviderError, match="invalid structured"):
        await TemporaryStateAgent(app.store, Gateway(provider)).propose([raw.ref])
    request = provider.requests[0]
    assert request.prompt_version == "temporary_state/v2"
    entry = request.output_schema["properties"]["temporary_entries"]["items"]
    assert entry["additionalProperties"] is False
    assert entry["properties"]["status"]["const"] == "open"
    assert not app.states.list()


async def test_generated_idea_schema_links_real_run_and_does_not_add_event_root(tmp_path):
    app = Application(tmp_path)
    provider = FixtureProvider([{"content": json.dumps({"decision": "propose", "reason": "synthetic", "temporary_entries": [
        {"text": "下次也许可以先确认安排", "origin_kind": "generated_idea", "origin_refs": [], "status": "open"}]})}])
    raw = app.store.append_message("user", "我们先讨论下次安排", message_id="idea_material")
    proposal = await TemporaryStateAgent(app.store, Gateway(provider)).propose([raw.ref])
    app.committer.submit_proposal(proposal)
    state = app.states.list()[0]
    assert state.source_refs == [proposal.records[0].ref]
    assert state.generator["prompt_version"] == "temporary_state/v2"
    assert app.store.list_records("event") == []
