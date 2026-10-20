"""Local double-click entry point. No keys in files or command-line arguments."""
from __future__ import annotations

import argparse
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tomllib


PROJECT = Path(__file__).resolve().parents[1]


@contextmanager
def single_launcher(root: Path):
    """Keep one launcher alive per character library, releasing on process exit."""
    import msvcrt

    # Keep the locked byte outside the library so normal backups can copy it.
    lock_dir = root.parent / ".myatri-launcher-locks"
    lock_dir.mkdir(parents=True, exist_ok=True)
    name = hashlib.sha256(os.path.normcase(str(root)).encode("utf-8")).hexdigest()
    with (lock_dir / f"{name}.lock").open("a+b") as stream:
        if stream.seek(0, 2) == 0:
            stream.write(b"\0")
            stream.flush()
        stream.seek(0)
        try:
            msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
        except OSError:
            raise RuntimeError("这个角色库的聊天窗口已经打开，请使用原来的窗口。") from None
        try:
            yield
        finally:
            stream.seek(0)
            msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)


def cli(root: Path, *args: str, agent: str = "atri", capture: bool = False):
    result = subprocess.run(
        [sys.executable, "-m", "myatri.interfaces.cli", "--root", str(root), "--agent", agent, *args],
        cwd=PROJECT, encoding="utf-8", capture_output=capture,
    )
    if result.returncode:
        if capture:
            print(result.stdout or "", end="")
            print(result.stderr or "", end="", file=sys.stderr)
        raise RuntimeError(f"运行失败（退出码 {result.returncode}），请查看上面的错误。")
    return result


def prepare_profile() -> Path:
    profile = PROJECT / "config/live.local.toml"
    if not profile.exists():
        template = (PROJECT / "config/live.example.toml").read_text(encoding="utf-8")
        template = template.replace("allow_paid = false", "allow_paid = true")
        template = template.replace("capabilities_verified = false", "capabilities_verified = true")
        # Exclusive creation never overwrites a profile created concurrently.
        try:
            with profile.open("x", encoding="utf-8") as stream:
                stream.write(template)
        except FileExistsError:
            pass
    with profile.open("rb") as stream:
        config = tomllib.load(stream)
    chat = config.get("chat", {})
    if chat.get("allow_paid") is not True or chat.get("capabilities_verified") is not True:
        raise RuntimeError("config/live.local.toml 尚未开启 live 调用，请检查 allow_paid 和 capabilities_verified。")
    if config.get("outreach", {}).get("enabled"):
        raise RuntimeError("当前版本不支持外发；请关闭 outreach.enabled。")
    return profile


def start(root: Path, check_only: bool, *, agent: str = "atri", persona_file: Path | None = None,
          display_name: str | None = None):
    from myatri.credentials import read_deepseek_key

    profile = prepare_profile()
    if not read_deepseek_key():
        if check_only:
            raise RuntimeError("尚未配置 Windows 凭据；正常启动时可以隐藏输入密钥。")
        print("首次启动需要输入 DeepSeek 密钥，输入内容不会显示，也不会写入项目文件。", flush=True)
        subprocess.run([sys.executable, "-m", "myatri.credentials", "store-deepseek"], check=True)
    # Use the stored credential consistently, even when inherited shell variables exist.
    os.environ.pop("DEEPSEEK_API_KEY", None)
    with single_launcher(root):
        print("[2/3] 检查角色库，已有记忆会继续保留。", flush=True)
        init_args = ["init"]
        if not (root / "runtime.sqlite3").exists() and not (root / "domains").exists():
            init_args += ["--persona-file", str(persona_file or PROJECT / "config/persona_template.md")]
        cli(root, *init_args, agent=agent, capture=True)
        result = cli(root, "doctor", agent=agent, capture=True)
        health = json.loads(result.stdout)
        if health.get("ok") is not True:
            print(result.stdout)
            raise RuntimeError("角色库完整性检查未通过，请先保留数据并排查。")
        print(f"记忆目录：{root}", flush=True)
        if check_only:
            print("检查通过：环境、配置、凭据、角色库均已就绪；没有调用模型 API。", flush=True)
            return
        print("[3/3] 开始真实聊天；后台整理和情绪评价会自动运行。", flush=True)
        print("使用付费 DeepSeek API；输入 /quit 退出，输入 /compact 压缩上下文。\n", flush=True)
        chat_args = ["--config", str(profile), "chat", "--mode", "live"]
        if display_name:
            chat_args += ["--display-name", display_name]
        cli(root, *chat_args, agent=agent)
        print("聊天已结束，记忆已保留。下次双击同一个启动文件即可继续。", flush=True)


def main():
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", line_buffering=True)
    parser = argparse.ArgumentParser(description="MYATRI 一键启动")
    parser.add_argument("--root", default="var/myatri-main")
    parser.add_argument("--agent", default="atri")
    parser.add_argument("--persona-file")
    parser.add_argument("--display-name")
    parser.add_argument("--check-only", action="store_true")
    args = parser.parse_args()
    root = Path(args.root)
    if not root.is_absolute():
        root = PROJECT / root
    try:
        persona_file = Path(args.persona_file) if args.persona_file else None
        if persona_file is not None and not persona_file.is_absolute():
            persona_file = PROJECT / persona_file
        start(root.resolve(), args.check_only, agent=args.agent, persona_file=persona_file,
              display_name=args.display_name)
    except KeyboardInterrupt:
        print("已停止；已有记忆保留。")
    except Exception as exc:
        print(f"启动失败：{exc}", file=sys.stderr)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
