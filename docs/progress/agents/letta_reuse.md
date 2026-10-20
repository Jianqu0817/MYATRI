# Letta 源码复读与实际移植记录

日期：2026-10-20。范围：Letta Code 当前运行时和 Letta Python archive 中，与 MYATRI 现有职责重叠的代码；未运行上游 Agent、未访问任何真实认证存储或付费模型 API。

## 来源与许可

| 来源 | 固定 commit | 核对结果 |
| --- | --- | --- |
| `letta-ai/letta-code` | `e8073d4e475ab7f56e76f9aaeea81a7618a92575` | Apache-2.0；完整 LICENSE 还包含 Brand Assets Exclusion。未发现独立 NOTICE。 |
| `letta-ai/letta` 的 archive 分支 | `56ba9c25552605eec89de8ed3dc6394b625c1993` | Apache-2.0，版权声明为 2023 Letta authors。未发现独立 NOTICE。 |

此次只适配通用源代码，不复制名称、logo、图片、ASCII art 等排除资产。完整当前源码许可证由主任务保留于 `LICENSES/upstream/Letta-Code-LICENSE.txt`，源码链接固定到 commit。

## 实际移植及生产接入

原始函数：[writeAuthFile 第 145–167 行](https://github.com/letta-ai/letta-code/blob/e8073d4e475ab7f56e76f9aaeea81a7618a92575/src/backend/local/local-provider-auth-store.ts#L145-L167)。采用其中“完整快照写入同目录唯一临时文件、排他创建、文件 fsync、关闭、原子 rename、finally 清理”的内核，适配为 `src/myatri/_vendor/letta.py::atomic_write`。

这是 TypeScript 到 Python 的小型代码适配，功能范围是**原子发布文件快照**。不是 Letta SDK、完整 Agent 运行时、记忆后端或其认证系统的接入。函数接收已序列化二进制字节；没有任何 auth-store 路径发现或凭据读取逻辑。

`src/myatri/storage/archive.py::_atomic_write` 现在委托给该适配函数。ArchiveStore 的记录文件和最后发布的 manifest，以及 MemoryIndex 的 generation 和 current 指针，都通过原有接口进入同一生产实现；旧自研写入函数体已删除。

适配与保留的细节：

- 接口保持 `(Path, bytes) -> None`，不重新序列化、不修补 Unicode、不变换换行或原始字节。
- 保留 MYATRI 隐藏同目录 UUID 临时文件、二进制模式和 POSIX 目录 fsync。Windows 跳过目录 fsync；测试覆盖真实 Windows 文件发布，并通过隔离 OS 代理核对 POSIX 分支顺序，未声称在原生 POSIX 上完成实测。
- 采用上游 `0600` 临时文件创建 mode；POSIX 下按进程 umask 收紧，Windows 下不能据此宣称已设置等价 POSIX ACL。
- 临时文件排他创建成功后才进入清理范围。UUID 碰撞时不会删除其他写入者拥有的文件。
- 写入、文件 fsync、rename 前失败时，旧目标快照保留；正常可删除的临时文件被清理。清理若被文件系统拒绝，不得用二次清理错误遮蔽主错误；这种情况下临时文件可能残留，属于明确失败语义。
- 适配额外保证 descriptor close 的二次错误不遮蔽先前 IO 错误；独立 close 错误仍会向上传递。
- 目录 fsync 在 rename 后发生；若它失败，新快照已经可见。函数报告失败，但不承诺回滚已完成的 rename。

## 已复读但未直接移植的重叠功能

| 上游代码 | 对应 MYATRI 功能 | 不直接替换的原因 |
| --- | --- | --- |
| 当前 `src/backend/local/compaction.ts`，以及 Python `letta/services/summarizer/{compact,summarizer,summarizer_sliding_window}.py` | `conversation/compaction.py`、`conversation/context.py` | 上游主要生成会话摘要、选择窗口、截短文本。MYATRI 现有摘要还必须保存逐条原文证据 span、固定 revision、增量处理覆盖、显式保留请求、状态/人格失效边界；接口与完成条件不等价。 |
| 当前 `src/backend/local/local-context-estimate.ts` | `conversation/budget.py` | 上游含 chars/4 估算、图像常数成本和历史 usage 锚点；MYATRI 的中文保守 UTF-8 请求上界、固定工具/schema 开销和统一额度不是同一语义。不能直接以较小估算替换预算保证。 |
| 当前 `src/backend/local/local-message-projection.ts::removeOrphanLocalToolResults`（第 389 行起）、Python `letta/utils.py::annotate_message_json_list_with_tool_calls` | `providers/gateway.py::validate_protocol` | 上游投影会移除孤立结果，旧实现还可补/改调用 ID。我们要求显式拒绝不完整 roundtrip、重复结果和重复 ID；静默修补会改变验证契约。 |
| Python `letta/helpers/json_helpers.py` | 网关结构化结果、原始记录序列化 | 上游允许宽松 JSON，并清除 surrogate/null 字节以适应数据库；MYATRI 原文与内容哈希不能接受这种静默更改，也不能绕过严格 schema 校验。 |
| 当前 `src/agent/turn-recovery-policy.ts`、`src/backend/dev/local-provider-errors.ts`；Python `letta/llm_api/llm_api_tools.py::retry_with_exponential_backoff` | `providers/gateway.py::Gateway.generate`、`runtime/worker.py` | 重试类别、jitter、尝试次数、同步/异步调用和已计费未知请求处理不同。扩大重试会改变当前额度结算与重试行为，不能称为完全一致的替换。 |
| Python `letta/services/file_processor/chunker/line_chunker.py`、摘要中的 middle truncation | `cognition/materials.py`、事件分块 | 上游 trim、空白归一化、去空行或丢弃中段，无法直接保留 MYATRI 的绝对字符区间与精确原文引用。 |
| 当前 `src/utils/file-lock.ts`、Python `letta/services/memory_repo/storage/local.py` | `storage/archive.py`、统一写入事务 | 其锁拥有者/过期回收和普通文件后端没有 MYATRI manifest-last、版本 CAS 和原始记录不可改写的组合职责。不是等价事务存储替代。 |

以上排除的是本次“行为完全一致”的直接替换，不代表相应架构不能在未来单独评估。没有把无生产调用的上游代码堆放进项目来增加复用比例。

## 验证

执行：

```powershell
.venv/Scripts/python.exe -m pytest tests/test_upstream_letta.py tests/test_storage.py tests/integration/test_commit_recovery.py tests/test_memory_consistency.py -q --junitxml=reports/letta_reuse_regression.xml
```

结果：**38 passed**；JUnit 记录测试耗时 **6.943 秒**。包括真实文件二进制一致性、写/fsync/rename 故障、临时文件碰撞、错误优先级、目录 fsync 顺序、真实 ArchiveStore/MemoryIndex 生产路径、manifest-last 进程死亡恢复、跨进程 CAS 和索引一致性。报告：`reports/letta_reuse_regression.xml`。
