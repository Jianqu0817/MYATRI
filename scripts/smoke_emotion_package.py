"""Install wheel into an isolated temporary target and run outside the checkout.

Reuses this interpreter's existing dependencies. No credentials or live API.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import zipfile


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--wheel", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("reports/emotion_package_smoke.json"))
    args = parser.parse_args()
    wheel = args.wheel.resolve()
    root = Path(tempfile.mkdtemp(prefix="myatri-emotion-package-"))
    target = root / "installed"
    subprocess.run(["uv", "pip", "install", "--offline", "--no-deps", "--target", str(target), str(wheel)],
                   check=True, capture_output=True, text=True, encoding="utf-8")
    body = r'''
import asyncio, json
from pathlib import Path
from datetime import datetime, timezone
import myatri
from myatri.app import Application
from myatri.contracts import Event, Record, SourceSpan, digest
from myatri.cognition.emotion import EmotionAgent
from myatri.persona.temporary import TemporaryStates
from myatri.providers import FixtureProvider, Gateway
from myatri.prompts import load_prompt
from myatri.interfaces.inspect import doctor

async def check():
    assert str(Path(myatri.__file__).resolve()).startswith(str(Path(TARGET).resolve()))
    assert myatri.__version__ == '0.1.3'
    assert load_prompt('emotion')
    app = Application(Path('synthetic-root'))
    raw = app.store.append_message('user', 'synthetic arrangement cancelled', message_id='smoke_emotion_raw')
    event = Event(fact_summary=raw.body_markdown, event_fingerprint=digest(raw.ref),
        source_spans=[SourceSpan(message_ref=raw.ref,start=0,end=len(raw.body_markdown),quote=raw.body_markdown)])
    row = Record(record_id='smoke_emotion_event',record_kind='event',source_refs=[raw.ref],body_markdown=raw.body_markdown,payload=event.model_dump())
    app.store.commit([row], 'smoke-seed')
    value = {'decision':'propose','reason':'synthetic fixture','appraisal':{'target':{'valence':-0.5,'arousal':0.6,'dominance':0.5},'confidence':0.8,'label':'disappointment','meaning':'synthetic expectation changed','concern':'clarify the plan'},'evidence':[{'message_ref':raw.ref,'quote':raw.body_markdown}]}
    provider = FixtureProvider([{'content':json.dumps(value)}])
    proposal = await EmotionAgent(app.store, Gateway(provider)).propose(row.ref)
    app.committer.submit_proposal(proposal)
    state = app.emotions.read()
    assert state['unique_event_count'] == 1
    assert state['affect']['valence'] < 0
    messages, _ = app.conversation.context.build_context('arrangement')
    assert app.conversation.context.explain_context()['emotion']['unique_event_count'] == 1
    assert app.conversation.context.budget.fits(messages, [])
    fresh = Application(Path('synthetic-root'))
    assert fresh.emotions.read()['unique_event_count'] == 1
    correction = fresh.emotions.propose_retraction(state['appraisal_refs'][0], 'synthetic correction')
    fresh.committer.submit_proposal(correction)
    assert fresh.emotions.read()['unique_event_count'] == 0
    assert fresh.states.list()[0].payload['status'] == 'discarded'
    assert doctor(fresh)['ok']
    return {'wheel_import':myatri.__file__,'version':myatri.__version__,'offline_appraisal_restart_context_retraction_doctor':True,'new_model_api_calls':0,'credentials_read':False}
print(json.dumps(asyncio.run(check())))
'''
    bootstrap = "import sys; TARGET=" + repr(str(target)) + "; sys.path.insert(0,TARGET);\n"
    process = subprocess.run([sys.executable, "-I", "-c", bootstrap + body], cwd=root,
                             check=True, capture_output=True, text=True, encoding="utf-8")
    result = json.loads(process.stdout)
    for command in (["emotion", "show"], ["emotion", "history"], ["doctor"]):
        check = subprocess.run([sys.executable, "-I", "-c", bootstrap + "from myatri.interfaces.cli import main; main()",
            "--root", "synthetic-root", *command], cwd=root, check=True, capture_output=True, text=True, encoding="utf-8")
        json.loads(check.stdout)
    with zipfile.ZipFile(wheel) as archive:
        names = archive.namelist()
        license_text = archive.read("myatri/_vendor/upstream/Emotional-Memory-LICENSE")
        assert hashlib.sha256(license_text).hexdigest() == "babeb375e954b7970fd93aa970528f2b939c37c2abfb8265901667fd53e3f107"
        assert not any("live.local.toml" in name or "/var/" in name for name in names)
    result.update({"wheel": wheel.name, "sha256": hashlib.sha256(wheel.read_bytes()).hexdigest(),
                   "isolated_target_installed": True, "external_cwd": str(root), "cli_show_history_doctor": True,
                   "license_in_wheel": True})
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result))


if __name__ == "__main__":
    main()
