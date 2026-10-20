# 运行检查记录

2026-10-20。实际命令：

- `uv sync --extra neural --index-url https://pypi.tuna.tsinghua.edu.cn/simple`：52项解析，实际安装成功；uv.lock固定。
- `python scripts/audit_sources.py`：5个锁定Git提交+许可核验通过；没有复制其源码。
- `pytest -q --junitxml=reports/pytest_results.xml`：覆盖故障恢复/并发/来源/隔离/协议/临时状态/局部人格/完整队列；最终计数见XML和acceptance.md。
- `myatri --root var/smoke init` / `chat --message ... --message-id smoke_1`：本地fixture回复、原文落盘、8个后台job成功；未调用API。
- `myatri eval --suite demo --output reports`：persona@2、4个独立事件根、doctor_ok=true；重提10次/激活不增加根、仅P03变更、撤回状态重启不复活。
- `myatri eval --suite baseline --neural-path var/models/bge-small-zh-v1.5 --output reports`：真实TF-IDF/BGE/Leiden，36案例24开发/12留出，结果与负结果见evaluation.md/json。
- `uv build`：成功生成wheel/sdist。
- `uv export --frozen --no-dev --no-emit-project ...` + 新建var/package-check/.venv + `uv pip sync` + 安装wheel：实际依赖隔离安装成功。
- 在 `var/package-check` 目录运行安装包（import路径为该新环境site-packages）：prompt资源加载、单轮chat+后台队列、doctor均成功，doctor ok=true；不依赖源码editable安装。

运维能力已实际测试：在线SQLite备份+档案打包，恢复到新目录，保留snapshot/persona/队列；zip路径穿越拒绝；原目录已有目标不覆盖；模型权重不打进发行包。

当前无付费API、外发、部署进程。离线合成数据保存在var/smoke/package-wheel-runtime和reports/demo_archive.zip，不含用户真实联系人活动。临时评估目录正常关闭清理；可重复运行报告命令。完整工具协议在运行库，与经历权威档案隔离。

## 本轮安全凭据与真实官方API补验

最新结果：80 passed；官方Flash13次生成，生成/JSON/tools/thinking往返通过；A8初次弱schema失败保留，v2完整契约定向恢复通过。用量与保守峰值估价见live_smoke.json/md；无常驻付费worker、无联系人发送、无部署。密钥位于Windows Credential Manager，不在项目文件；backup/restore/真实wheel+sdist的12项fake sentinel安全回归通过（含大小写与YAML）。实际key排除扫描0匹配，见secret_exclusion.json。

最新独立安装复验包括凭据模块status（只显示configured）、包内temporary_state/v2 prompt加载、既有离线运行目录doctor；不再调用API。公开包不含config/live.local.toml，默认paid=false。
