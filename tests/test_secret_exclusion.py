"""Distribution/backup checks use only temporary, fabricated credentials.

Never read a developer .env, local live configuration, environment API key, or
Windows Credential Manager. Build a public-source staging tree, then inject
fresh random sentinels to test the actual archive builders.
"""
from __future__ import annotations

from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import uuid
import zipfile

import pytest

from myatri.app import Application
from myatri.interfaces.inspect import backup, restore_backup


SENSITIVE_PATHS = [
    ".env",
    ".env.live",
    "nested/.env.local",
    "credentials.json",
    "secrets.toml",
    "private.key",
    "private.pem",
    "config/live.local.toml",
    "config/development.local.toml",
    "config/credentials.json",
    "config/.env.production",
    "nested/CREDENTIALS.JSON",
    "nested/private.PEM",
    "nested/.ENV.LIVE",
    "credentials.yaml",
    "config/SECRETS.YML",
]


def plant_fake_credentials(root: Path, relative_paths: list[str]) -> bytes:
    sentinel = f"MYATRI_FABRICATED_SENTINEL_{uuid.uuid4().hex}".encode("ascii")
    for relative in relative_paths:
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(sentinel)
    return sentinel


def archive_members(path: Path) -> dict[str, bytes]:
    if path.suffix == ".whl" or path.suffix == ".zip":
        with zipfile.ZipFile(path) as archive:
            return {item.filename: archive.read(item) for item in archive.infolist() if not item.is_dir()}
    with tarfile.open(path, "r:gz") as archive:
        return {item.name: archive.extractfile(item).read() for item in archive.getmembers() if item.isfile()}


def test_runtime_backup_excludes_fabricated_secret_files_and_preserves_records(tmp_path):
    app = Application(tmp_path / "runtime")
    message = app.store.append_message("user", "这是一条应当恢复的普通原文。", "safe_record")
    sentinel = plant_fake_credentials(app.root, SENSITIVE_PATHS)
    path = Path(backup(app, tmp_path / "safe_backup.zip"))
    members = archive_members(path)
    leaked_paths = [relative for relative in SENSITIVE_PATHS if relative in members]
    assert leaked_paths == [], f"Sensitive runtime paths leaked into backup: {leaked_paths}"
    assert all(sentinel not in content for content in members.values())
    restored = Application(restore_backup(path, tmp_path / "restored"))
    assert restored.store.get_record(message.record_id).body_markdown == message.body_markdown
    assert restored.store.verify_archive() == []


@pytest.mark.parametrize("relative", [".env", "config/live.local.toml", "credentials.json", "private.pem", "nested/.ENV.LIVE", "nested/private.PEM", "credentials.yaml", "config/SECRETS.YML"])
def test_restore_rejects_fabricated_credential_members_before_extract(tmp_path, relative):
    app = Application(tmp_path / "source")
    app.store.append_message("user", "可恢复的安全记录", "safe")
    path = Path(backup(app, tmp_path / "tainted.zip"))
    with zipfile.ZipFile(path, "a") as archive:
        archive.writestr(relative, f"MYATRI_FABRICATED_SENTINEL_{uuid.uuid4().hex}")
    target = tmp_path / "target"
    with pytest.raises(ValueError):
        restore_backup(path, target)
    assert not target.exists()


@pytest.fixture(scope="module")
def staged_distributions(tmp_path_factory):
    source = Path(__file__).resolve().parents[1]
    staging = tmp_path_factory.mktemp("myatri-public-build")
    # Explicitly copy public project inputs. Do not inspect/copy source .env,
    # live.local.toml, runtime archives, reports, or the developer's credentials.
    for name in ("pyproject.toml", ".gitignore", "README.md", "uv.lock", "THIRD_PARTY_NOTICES.md"):
        path = source / name
        if path.is_file():
            shutil.copyfile(path, staging / name)
    for directory in ("src", "prompts", "LICENSES"):
        path = source / directory
        if path.is_dir():
            def public_inputs_only(current, names):
                ignored = []
                for name in names:
                    candidate = Path(current) / name
                    if (name == "__pycache__" or candidate.is_symlink() or candidate.is_junction() or
                            (directory == "src" and candidate.is_file() and candidate.suffix not in {".py", ".html"})):
                        ignored.append(name)
                return ignored
            shutil.copytree(path, staging / directory, ignore=public_inputs_only)
    (staging / "config").mkdir()
    for name in ("defaults.toml", "schedules.toml", "persona_template.md", "live.example.toml", "cli-engine.toml"):
        path = source / "config" / name
        if path.is_file():
            shutil.copyfile(path, staging / "config" / name)
    (staging / "docs").mkdir()
    shutil.copyfile(source / "docs/companion_port_source.json", staging / "docs/companion_port_source.json")
    # These explicit public role-card inputs are required by wheel force-include.
    role_source = source / "config/personas/xiaowennuan"
    role_target = staging / "config/personas/xiaowennuan"
    role_target.mkdir(parents=True)
    for name in ("persona.md", "source.md", "README.md", "style_update_2026-10-21.md"):
        shutil.copyfile(role_source / name, role_target / name)
    sensitive = [*SENSITIVE_PATHS, "src/myatri/.env.hidden", "src/myatri/credentials.json",
                 "src/myatri/upper/CREDENTIALS.JSON", "src/myatri/private.PEM", "src/myatri/.ENV.LIVE",
                 "src/myatri/credentials.yaml", "src/myatri/upper/SECRETS.YML"]
    sentinel = plant_fake_credentials(staging, sensitive)
    built = staging / "built"
    process = subprocess.run([sys.executable, "-m", "build", "--no-isolation", "--outdir", str(built)], cwd=staging,
                             capture_output=True, text=True, timeout=120)
    assert process.returncode == 0, process.stdout + process.stderr
    wheel = next(built.glob("*.whl"))
    sdist = next(built.glob("*.tar.gz"))
    return {"wheel": archive_members(wheel), "sdist": archive_members(sdist), "sentinel": sentinel,
            "credentials_module": (source / "src/myatri/credentials.py").is_file(),
            "live_example": (source / "config/live.example.toml").is_file()}


@pytest.mark.parametrize("kind", ["wheel", "sdist"])
def test_real_distribution_build_excludes_fabricated_credentials(staged_distributions, kind):
    members = staged_distributions[kind]
    leaked = [name for name, content in members.items() if staged_distributions["sentinel"] in content]
    assert leaked == [], f"Fabricated credentials leaked into {kind}: {leaked}"
    assert any(name.endswith("myatri/contracts/__init__.py") for name in members)
    assert any(name.endswith("defaults.toml") for name in members)
    if staged_distributions["credentials_module"]:
        assert any(name.endswith("myatri/credentials.py") for name in members)
    if staged_distributions["live_example"]:
        assert any(name.endswith("live.example.toml") for name in members)
    # Production-used upstream adaptations carry their original
    # license texts in both source and binary distributions.
    import hashlib
    import json
    expected_licenses = {
        "A-MEM-LICENSE": "c8a51c83455b8afc3a11b085ce57c7b9b34c6725d6b2329ce3dd9a273f0add6d",
        "Letta-Code-LICENSE.txt": "036e78b9d7dd33ae5b378fdda973b4aad7901c8d8371a0ae40fae1f6659a89d0",
        "Emotional-Memory-LICENSE": "babeb375e954b7970fd93aa970528f2b939c37c2abfb8265901667fd53e3f107",
    }
    prefix = "myatri/_vendor/upstream/" if kind == "wheel" else "LICENSES/upstream/"
    manifest = next(content for name, content in members.items() if name.endswith(prefix + "manifest.json"))
    assert len(json.loads(manifest)["adaptations"]) == 3
    for filename, digest in expected_licenses.items():
        content = next(content for name, content in members.items() if name.endswith(prefix + filename))
        assert hashlib.sha256(content).hexdigest() == digest
    for filename in ("amem.py", "letta.py", "emotional_memory.py"):
        assert any(name.endswith("myatri/_vendor/" + filename) for name in members)


def test_gitignore_explicitly_ignores_local_live_config():
    # Read only policy text, never a credential/local configuration value.
    rules = (Path(__file__).resolve().parents[1] / ".gitignore").read_text(encoding="utf-8")
    assert ".env" in rules
    assert ".env.*" in rules
    assert "config/live.local.toml" in rules or "*.local.toml" in rules
