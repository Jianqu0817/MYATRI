import pytest

from myatri.app import Application
from myatri.persona.state import PersonaState
from myatri.persona.patch import PersonaPatcher


def test_initial_markdown_and_human_edit_are_not_natural_evidence(tmp_path):
    entries = PersonaState.parse_template("# 角色\n\n## identity\n\n我是小海。\n\n## style\n\n我喜欢简洁表达。")
    app = Application(tmp_path, config={"initial_persona_entries": entries})
    initial = app.persona.read_state()
    updated = PersonaPatcher(app.store).human_edit("style", "我喜欢先说结论，再举一个例子。", "用户明确调整角色设定")
    assert app.persona.diff(1, 2).keys() == {"style"}
    assert updated.payload["entry_hashes"]["identity"] == initial.payload["entry_hashes"]["identity"]
    change = app.store.get_record(updated.payload["change_ref"].split("@")[0])
    assert change.payload["mode"] == "human_edit" and change.payload["event_roots"] == []
    assert not app.store.list_records("event")
    with pytest.raises(ValueError): app.persona.initialize(entries)
