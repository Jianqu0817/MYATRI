# A-MEM / Letta 源码复读与等价功能改编

2026-10-20，MYATRI 0.1.2。用户要求认真复读两个项目的代码，并复用本项目中功能完全一致的部分。本轮采用两处**很小的局部改编**，已替换原有生产实现；没有接入完整 A-MEM 或 Letta 框架，也没有新增记忆语义能力或性能领先的证明。

## 阅读范围与版本

从官方 Git 仓库取得源码，所有采用来源固定到提交；临时 checkout 位于被 Git/打包排除的 `reports/*_tmp*`，不进入项目发行包。

- A-MEM：`agiresearch/A-mem@ceffb860f0712bbae97b184d440df62bc910ca8d`。完整阅读 `memory_system.py`（727 行）、`retrievers.py`（303 行）、`llm_controller.py`（97 行）及相关测试，对照现有事件组织、关联、检索和模型网关。
- Letta 当前实现：原 `letta-ai/letta` 的 main 已变为迁移说明，指向 `letta-ai/letta-code`；本次固定 `e8073d4e475ab7f56e76f9aaeea81a7618a92575`。检查局部上下文估算、消息/工具投影、compaction、运行恢复、文件锁及原子文件写入等相关实现与测试。
- Letta 原 Python 服务：`letta-ai/letta` 的 `archive@56ba9c25552605eec89de8ed3dc6394b625c1993`。对照摘要/滑动窗口、JSON、工具协议、重试及文件分块。未把旧服务当成当前运行时，也未宣称逐行审完当前 Letta 全仓库。

采用的源码文件哈希、精确函数/行范围、修改、生产调用链和测试文件见 [逐段清单](../LICENSES/upstream/manifest.json)。固定 Git blob 与许可证逐字节核对见 [核验结果](upstream_reuse_verification.json)。两份分工阅读记录见 [A-MEM](../docs/progress/agents/amem_reuse.md)、[Letta](../docs/progress/agents/letta_reuse.md)。

## 实际替换

| 来源 | 原始范围 | 本地改编及生产入口 | 保持的职责 |
|---|---|---|---|
| A-MEM `AgenticMemorySystem.search_agentic` | `agentic_memory/memory_system.py:554–583` 中的关联邻居去重与计数机制 | `_vendor/amem.py::iter_unique_neighbors` → `MemoryGraph.get_subgraph` → `RecallService.recall` | 关联展开、已访问 ID 去重与数量限制；本地仍持有边类型/快照/路径/深度 |
| Letta Code `writeAuthFile` | `src/backend/local/local-provider-auth-store.ts:145–167` | `_vendor/letta.py::atomic_write` → `storage.archive._atomic_write` → 档案记录/manifest 与索引 generation/current 发布 | 完整快照以排他同目录临时文件落盘、fsync、rename 与清理；本地仍持有单写者与 manifest-last |

A-MEM 实际改编函数只有 8 个物理行（含 1 行 docstring）；它只是通用关联去重小内核，不能算“复用了整个 A-MEM 记忆演化”。不为增加比例加入无调用的上游代码。外层按原 edge-first 顺序提供候选；保留双向关系、incident-edge 重复、自环、tight limit、多 seed、多 depth 的原输出。额度耗尽后仍消费候选，避免丢失本地原有边输出。

Letta 片段由 TypeScript 改为 Python，接收预序列化 bytes 而非认证对象。未移植凭据访问、路径发现或任何认证状态；二进制原文不变。保留本地目录 fsync，并采用上游临时文件 0600 mode，Windows 不据此宣称 POSIX ACL。排他创建碰撞不删除他人的文件；清理或 descriptor close 的二次错误不遮蔽首个 IO 错误。目录 fsync 在 rename 后失败时，新文件可能已可见，不虚构回滚。

这次并未减少大量代码，Letta 的错误边界适配还增加了显式处理。价值是可定位的局部代码来源与经过测试的行为兼容，不能将复用行数等同于可靠性收益。

## 未按“同名功能”强行替换的部分

| 候选 | 不等价的具体原因 |
|---|---|
| A-MEM MemoryNote/CRUD、ChromaRetriever | 可变内存笔记、模型初始化、metadata 字符串推断与现有精确 revision/embedding space/权威原文契约不同；初始系统还会尝试 reset 集合 |
| A-MEM analyze_content / process_memory | 关键词/标签不是本地带原文 span 的事件；直接更新旧邻居不是有来源的类型边提案。上游按查询排名访问插入序列可能选错邻居，未照搬 |
| A-MEM 完整 search_agentic | 最后的 `memories[:k]` 在 seed 已满 k 时会截去追加邻居；只提取所需内核，未复制该结果截断 |
| Letta 摘要、滑动窗口与分块 | 现有 MYATRI 摘要还必须保存原文 span、revision、处理覆盖和状态失效；上游部分裁剪/空白归一化行为不能保持这些约束 |
| Letta 工具消息与 JSON 修补 | 移除孤立结果、补/改工具 ID、宽松 JSON 和清洗字符，不等于本地严格拒绝不完整协议与保留原始字节 |
| Letta token 估算、重试与运行时 | 字符启发式估算、重试类别/次数和运行状态写入会改变本地中文保守预算、未知计费结算与统一提交职责 |

这些排除只针对本次“保持功能和行为”的直接替换。若以后选择更换记忆后端或运行底座，需要另做契约迁移和同条件质量/成本比较。

## 许可与发行

A-MEM MIT 原始 LICENSE 与 Letta Code 完整 LICENSE（Apache-2.0 文本及 Brand Assets Exclusion）保存在 `LICENSES/upstream/`，两个固定 Git 树均无独立 NOTICE。改编文件注明版权、来源、固定提交与修改。未复制 Letta 品牌资产。

sdist 保留 `LICENSES/upstream/`，wheel 在 `myatri/_vendor/upstream/` 携带许可证和 manifest；`.gitattributes` 保持两份原始许可字节不被 Windows 换行转换。打包回归同时检查完整许可哈希、改编模块与虚构敏感数据排除。源码锁定、第三方说明及来源审计脚本已更新，T00 的“未复制”记录显式标为历史。

## 验证

- A-MEM 定向：35 passed / 12.718s。冻结移植前完整输出对照、120 张确定性随机图及实际回忆接入。
- Letta 定向：38 passed / 6.943s。真实 Windows 文件发布、write/fsync/rename 故障、临时碰撞、关闭/清理错误、跨进程 CAS 和进程死亡恢复。POSIX 目录 fsync 分支使用隔离 OS 代理验证，未冒称原生 POSIX 实测。
- 完整回归：**192 passed / 140.56s，0 failures/errors/skipped**，见 `upstream_reuse_regression.xml`。构建 `myatri-0.1.2` wheel/sdist 成功，许可原始字节哈希和临时/私密路径排除通过。实际 wheel 安装到独立目标目录后，从 `C:/Windows/Temp` 以隔离模式完成 init/chat/compact/doctor，doctor ok=true。见 `upstream_wheel_smoke.json`；最终构建哈希见 `upstream_package_check.json`。

本轮模型 API 调用 0 次，未读取实际凭据或修改真实用户运行库，未启动服务或对外发送消息。依赖沿用锁定版本，未安装两个完整上游框架。
