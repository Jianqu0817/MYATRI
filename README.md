# MYATRI

2026-10-20 源码复用：0.1.2 已局部改编 A-MEM 的关联邻居去重内核与 Letta Code 的原子快照写入内核，并接入生产路径。仅两处小型代码适配，未接入完整框架。192项完整离线回归与源码目录外wheel试运行通过；来源、许可、兼容验证与未移植理由见 [复用报告](reports/upstream_reuse_2026-10-20.md) 和 [逐段清单](LICENSES/upstream/manifest.json)。

2026-10-20 持久运行修复：0.1.1 已修复重复压缩、索引快照/发布/历史证据、后台有界材料、调度/时间及共享预算，并接通日常表达/反馈归因。178项完整离线回归通过，详见[修复与边界](reports/persistence_fixes_2026-10-20.md)。本轮0次新API，长期语义及实体/技能设计仍待验证/实现。下文旧审查状态为历史记录，以本补记为准。

当前设计修订（2026-10-20）：[工程规划0.3](docs/01_工程规划书.md)与[动态索引/技能记忆设计及检查表](docs/04_动态索引与技能记忆设计.md)已同步讨论。人物/项目/地点的稳定实体入口、技能学习入口仍待实现；现有能力为事件参与者检索、动态主题和可替换Embedding。默认TF-IDF，可选本地BGE；全文分块、局部增量索引与已知一致性缺陷仍开放。文档新增不代表生产功能已完成。

2026-10-20新增：会话语义压缩和临时状态激活已接入LLM API；116项离线回归、2次官方合成smoke通过。正常live聊天及/compact生效，独立compact/context命令新增--mode live。失败/defer/离线明确降级。详见[本次升级与验证](reports/llm_context_upgrade.md)。其他审查项仍开放，下文80项为历史基线。

V1 本地实现：持久文本经历、真实向量/Leiden记忆图、混合回忆、临时念头与反馈生命周期、局部人格更新、上下文压缩、持久任务与恢复。

**普通回归最新116项通过，官方DeepSeek-V4.1-Flash生成/JSON/工具/thinking协议已有短smoke证据；完整V1验收因组件审查发现的缺陷仍开放。** 密钥保存在Windows凭据管理器，不在项目文件或发行包中。默认offline仍是明确标记的fixture演示；真实长期反思/人格语义效果尚未验证，联系人主动发送与部署未启用。

**2026-10-20组件审查补记：此前80项通过是历史测试基线。新复现了索引发布倒退、历史图快照等一致性缺陷，并确认普通聊天的行动反馈归因尚未接通；完整V1验收重新开放，生产代码本轮未修。** 各组件实际工作方式、9项问题/边界及修改建议见[组件讲解与审查](reports/component_review.md)。

## 运行

在本目录的 PowerShell：

```powershell
uv sync --frozen
.venv/Scripts/myatri.exe --root var/atri init
.venv/Scripts/myatri.exe --root var/atri chat --mode offline
```

单轮与检查：

```powershell
.venv/Scripts/myatri.exe --root var/atri chat --message '电影临时取消后，我想先说清自己的期待。'
.venv/Scripts/myatri.exe --root var/atri recall '电影期待' --explain
.venv/Scripts/myatri.exe --root var/atri worker --once
.venv/Scripts/myatri.exe --root var/atri doctor
```

真实中文神经向量（可选，模型已在本次工作区下载）：

```powershell
uv sync --frozen --extra neural
# 新环境需要显式执行；普通聊天不会自动下载模型
.venv/Scripts/myatri.exe models download --path var/models/bge-small-zh-v1.5
.venv/Scripts/myatri.exe --root var/atri memory rebuild-index --space bge
```

默认真实TF-IDF词面基线无需下载模型；BGE为固定revision的本地512维ONNX推理；Leiden是真实运行的算法。相似度不证明同义，尤其不能由相似直接推导支持/人格变化。

## 验证与交付

```powershell
.venv/Scripts/python.exe -m pytest -q
.venv/Scripts/myatri.exe eval --suite all --neural-path var/models/bge-small-zh-v1.5
uv build
```

- [运行与恢复手册](docs/运行与恢复手册.md)
- [交付与限制](docs/交付与限制.md)
- [验收报告](reports/acceptance.md)、[评估](reports/evaluation.md)、[live状态](reports/live_smoke.md)
- [当前进度](docs/progress/STATUS.md)、[无对话历史的恢复入口](docs/progress/HANDOFF.md)
- [规划0.3](docs/01_工程规划书.md)、[动态索引/技能记忆检查稿](docs/04_动态索引与技能记忆设计.md)、[任务清单（原0.2排程）](docs/02_实施任务清单.json)、[锁定来源](docs/03_参考源码锁定.json)
- [依赖及参考许可](THIRD_PARTY_NOTICES.md)、[实际依赖许可清单](reports/dependency_licenses.json)

八模块：providers / storage / memory / retrieval / persona / conversation / cognition / runtime。认知任务只生成提案，统一提交器校验版本；文本档案权威，SQLite和向量索引可重建。E01不属于本次实现。

## 本机已验证的官方live测试

密钥已安全配置，`.venv/Scripts/python.exe -m myatri.credentials status`只显示配置状态。真实API需显式命令：

```powershell
.venv/Scripts/myatri.exe --config config/live.local.toml --root var/atri-live chat --mode live
```

本机live.local.toml仅含开关/模型/小预算、不含key，已从Git、备份与发行包排除；公开模板为config/live.example.toml，默认关闭paid。不会自动启动常驻付费任务。跨机器需重新设置Windows凭据。实测13次请求与初测问题修复记录见[完整live报告](reports/live_smoke.md)。
