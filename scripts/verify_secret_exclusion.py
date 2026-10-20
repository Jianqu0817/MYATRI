"""Check this actual credential is absent from shareable project artifacts.

Only reports booleans/counts/relative filenames, never the secret or a digest of it.
The credential is fetched from Windows on explicit invocation, never during CI.
"""
import io
import json
from pathlib import Path
import tarfile
import zipfile

from myatri.credentials import read_deepseek_key


ROOT = Path(__file__).resolve().parents[1]


def verify():
    secret = read_deepseek_key()
    if not secret:
        raise RuntimeError("no credential configured; cannot perform actual-secret exclusion check")
    needle = secret.encode("utf-8")
    leaks, checked, archives = [], 0, 0
    candidates = [ROOT / name for name in ("README.md", "pyproject.toml", "uv.lock", ".gitignore", "THIRD_PARTY_NOTICES.md")]
    for folder in ("src", "config", "docs", "reports", "scripts", "tests", "prompts", "evals", "LICENSES", "dist",
                   "var/live-smoke-20261020", "var/live-context-smoke-20261020", "var/smoke", "var/package-wheel-runtime"):
        candidates.extend(path for path in (ROOT / folder).rglob("*") if path.is_file() and "__pycache__" not in path.parts)
    for path in candidates:
        data = path.read_bytes()
        checked += 1
        relative = path.relative_to(ROOT).as_posix().replace(secret, "[redacted]")
        if needle in data:
            leaks.append(relative)
        if path.suffix in {"zip", "whl"} or path.name.endswith((".zip", ".whl")):
            with zipfile.ZipFile(io.BytesIO(data)) as bundle:
                for item in bundle.infolist():
                    if not item.is_dir():
                        archives += 1
                        if needle in bundle.read(item):
                            leaks.append(relative + ":" + item.filename.replace(secret, "[redacted]"))
        elif path.name.endswith(".tar.gz"):
            with tarfile.open(fileobj=io.BytesIO(data)) as bundle:
                for item in bundle:
                    if item.isfile():
                        archives += 1
                        if needle in bundle.extractfile(item).read():
                            leaks.append(relative + ":" + item.name.replace(secret, "[redacted]"))
    result = {"credential_configured": True, "credential_store": "Windows Credential Manager",
              "files_checked": checked, "archive_members_checked": archives, "secret_matches": len(leaks),
              "leaks": leaks, "scope": "project sources/config/docs/reports/tests/packages and synthetic live runtime; not a whole-device audit"}
    (ROOT / "reports/secret_exclusion.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items() if k != "leaks"}, ensure_ascii=False))
    if leaks:
        raise SystemExit(1)


if __name__ == "__main__":
    verify()
