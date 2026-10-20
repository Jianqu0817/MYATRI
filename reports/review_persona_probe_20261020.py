"""Read-only review probes against a new, synthetic workspace-local archive.

No credentials, production data, network, or source modifications are used.
Each invocation uses a fresh uniquely named directory; no recursive deletion.
"""
from __future__ import annotations

import asyncio
import json
from pathlib import Path
import uuid

from myatri.app import Application
from myatri.contracts import BehaviorAttempt, Record, TemporaryEntry, utcnow
from myatri.interfaces.inspect import doctor
from myatri.persona.activation import ActivationSelector
from myatri.persona.temporary import event_roots


def main():
    root = (Path(__file__).resolve().parent / "review_persona_tmp_20261020" / uuid.uuid4().hex)
    app = Application(root)
    run = Record(record_id="synthetic_seed", record_kind="cognitive_run", payload={"role": "review_probe"})
    app.store.commit([run], "synthetic-seed")
    idea = lambda text, **extra: TemporaryEntry(
        text=text, scope="散步期待", origin_kind="generated_idea", origin_refs=[run.ref], **extra)

    fake = app.states.create(idea("仅合成探针", status="consolidated", persona_change_ref="missing_change@1"), entry_id="fake_consolidated")
    diagnosis = doctor(app)
    assert fake.payload["status"] == "consolidated"
    assert not app.store.list_records("persona_change")
    assert app.persona.read_state().revision == 1
    assert diagnosis["issues"] == ["missing consolidation source"]

    state = app.states.create(idea("散步时先说清期待"), entry_id="retirement_probe")
    dropped = app.states.review(state.record_id, base_revision=1, status="discarded", reason="synthetic discard")
    direct_blocked = False
    try:
        app.states.review(state.record_id, base_revision=2, status="open", reason="synthetic direct reopen")
    except ValueError:
        direct_blocked = True
    settled = app.states.review(state.record_id, base_revision=2, status="settled", reason="synthetic intermediate transition")
    reopened = app.states.review(state.record_id, base_revision=3, status="open", reason="synthetic indirect reopen")
    selected, activation = asyncio.run(ActivationSelector(app.store, llm_enabled=False).aselect_active_entries("散步期待"))
    assert direct_blocked
    assert dropped.payload["status"] == "discarded" and settled.payload["status"] == "settled"
    assert reopened.ref in [r.ref for r in selected]

    arbitrary = app.store.append_message("assistant", "这是任意合成占位文字。", "arbitrary_assistant")
    observed = app.states.record_attempt_feedback(BehaviorAttempt(intent_ref=reopened.ref, decision_status="attempted",
        action_refs=[arbitrary.ref], occurred_at=utcnow()), attempt_id="arbitrary_attempt")
    assert observed.payload["outcome_unknown"] is True
    assert event_roots(app.store, [observed.ref]) == []

    result = {
        "synthetic_root": str(root),
        "create_consolidated": {"accepted_ref": fake.ref, "persona_revision": app.persona.read_state().revision,
            "persona_change_count": len(app.store.list_records("persona_change")), "doctor": diagnosis["issues"]},
        "indirect_reactivation": {"direct_reopen_rejected": direct_blocked,
            "status_chain": ["open", "discarded", "settled", "open"], "reactivated_ref": reopened.ref,
            "activation_selected_refs": activation.selected_refs},
        "arbitrary_assistant_action": {"accepted_ref": observed.ref, "external_event_roots": event_roots(app.store, [observed.ref]),
            "outcome_unknown": observed.payload["outcome_unknown"], "classification": "known semantic boundary, not code-review finding"},
        "paid_calls": 0,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
