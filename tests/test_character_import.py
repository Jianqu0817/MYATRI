from contextlib import nullcontext
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from myatri.conversation.budget import TokenBudget
from myatri.conversation.context import ContextBuilder, RUNNING_RULES
from myatri.interfaces.cli import parser, run
from myatri.persona.state import PersonaState
from myatri.retrieval import RecallService
from myatri.storage import ArchiveStore


PROJECT = Path(__file__).resolve().parents[1]
CARD = PROJECT / "config/personas/xiaowennuan/persona.md"


@pytest.mark.asyncio
async def test_character_init_context_and_restart_preserve_provenance(tmp_path, capsys):
    args = parser().parse_args(["--root", str(tmp_path), "--agent", "xiaowennuan",
                               "init", "--persona-file", str(CARD)])
    await run(args)
    capsys.readouterr()
    store = ArchiveStore(tmp_path, "xiaowennuan", "local")
    persona = PersonaState(store).read_state()
    entries = persona.payload["entries"]
    assert len(entries) == 15
    assert persona.author_kind == "human_import"
    assert "20岁" in entries["P01_identity"]
    assert "对方抛梗就接，没梗不硬找" in entries["P06_expression"]
    assert "猫咪行为 | 一期对话最多一两次" in entries["P06_expression"]
    assert "父母的姓名、职业和当前状况" in entries["P13_unknown"]
    assert "对话示例仅演示措辞" in entries["P00_provenance"]
    assert not store.list_records("event")
    assert not store.list_records("raw_message")
    builder = ContextBuilder(store, RecallService(store),
        budget=TokenBudget(limit=1000000, compact_at=650000, output_reserve=4096, safety=4096))
    messages, _ = builder.build_context("你是谁？")
    assert persona.body_markdown in messages[0]["content"]
    assert "ATRI" not in RUNNING_RULES
    assert "小温暖" in messages[0]["content"]
    assert builder.budget.fits(messages)
    # An ordinary restart must not restore the example persona or create a new version.
    await run(parser().parse_args(["--root", str(tmp_path), "--agent", "xiaowennuan", "init"]))
    assert PersonaState(store).read_state().ref == persona.ref
    assert PersonaState(store).read_state().payload["entries"] == entries


def test_launcher_selects_card_agent_and_name_only_initializes_new_library(tmp_path, monkeypatch):
    spec = importlib.util.spec_from_file_location("character_launcher", PROJECT / "scripts/start_myatri.py")
    launcher = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(launcher)
    # No real credential access, API request, lock, or user library mutation.
    monkeypatch.setattr("myatri.credentials.read_deepseek_key", lambda: "fake-test-credential")
    monkeypatch.setattr(launcher, "prepare_profile", lambda: tmp_path / "fake.toml")
    monkeypatch.setattr(launcher, "single_launcher", lambda root: nullcontext())
    calls = []

    def fake_cli(root, *args, agent, capture=False):
        calls.append((root, args, agent))
        if args[0] == "init":
            (root / "runtime.sqlite3").touch()
        return SimpleNamespace(stdout=json.dumps({"ok": True}))

    monkeypatch.setattr(launcher, "cli", fake_cli)
    for _ in range(2):
        launcher.start(tmp_path, False, agent="xiaowennuan", persona_file=CARD, display_name="小温暖")
    assert calls[0][1] == ("init", "--persona-file", str(CARD))
    assert calls[3][1] == ("init",)
    assert all(root == tmp_path and agent == "xiaowennuan" for root, _, agent in calls)
    chat_args = calls[2][1]
    assert chat_args[-2:] == ("--display-name", "小温暖")
    parsed = parser().parse_args(["--agent", "xiaowennuan", *chat_args])
    assert parsed.display_name == "小温暖" and parsed.mode == "live"


def test_launcher_cli_passes_agent_to_real_command(monkeypatch, tmp_path):
    spec = importlib.util.spec_from_file_location("character_launcher_command", PROJECT / "scripts/start_myatri.py")
    launcher = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(launcher)
    commands = []

    def fake_run(command, **kwargs):
        commands.append(command)
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(launcher.subprocess, "run", fake_run)
    launcher.cli(tmp_path, "doctor", agent="xiaowennuan", capture=True)
    parsed = parser().parse_args(commands[0][3:])
    assert parsed.agent == "xiaowennuan" and parsed.root == str(tmp_path)
    assert parsed.command == "doctor"
