"""Read-only verification of locked commits/licenses and registered code reuse."""
import concurrent.futures
import json
from pathlib import Path
import urllib.request

ROOT = Path(__file__).resolve().parents[1]


def check(repo):
    base = "https://api.github.com/repos/" + repo["repository"]
    def read(suffix):
        request = urllib.request.Request(base + suffix, headers={"User-Agent": "MYATRI-source-audit"})
        with urllib.request.urlopen(request, timeout=20) as response:
            return json.load(response)
    result = {"repository": repo["repository"], "expected_commit": repo["commit"],
              "copied_code": bool(repo.get("code_reuse")), "code_reuse": repo.get("code_reuse", [])}
    try:
        commit = read("/commits/" + repo["commit"])
        license_data = read("/license?ref=" + repo["commit"])
        result.update(commit_verified=commit["sha"] == repo["commit"],
                      license=license_data.get("license", {}).get("spdx_id"),
                      license_path=license_data.get("path"), status="verified")
    except Exception as exc:
        result.update(status="unverified", error=type(exc).__name__)
    return result


if __name__ == "__main__":
    locked = json.loads((ROOT / "docs/03_参考源码锁定.json").read_text(encoding="utf-8-sig"))
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:
        results = list(pool.map(check, locked["repositories"]))
    (ROOT / "reports/source_verification.json").write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(results, ensure_ascii=True))
