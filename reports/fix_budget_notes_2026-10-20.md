# A07：共享日额度与任务人工恢复修复

日期：2026-10-20（Asia/Shanghai）。独立子任务只修改 `src/myatri/providers/gateway.py`、`src/myatri/runtime/jobs.py`，新增 `tests/test_shared_budget.py`；应用接线与 CLI 由主 Agent 负责。

## 变更与接口

- `Gateway(..., budget_ledger=queue, budget_scope=None)`：生产调用可使用持久化原子账本。默认 scope 为 provider.name，同一个 runtime SQLite 内跨 Gateway、跨 agent/user、跨进程共享额度；不读取密钥以生成 scope。旧的无账本 Gateway 继续支持内存额度和 usage_sink。
- `JobQueue.reserve_budget(scope, estimated_tokens, daily_limit, *, ttl_seconds=300, now=None)` 返回 reservation ID；额度不足返回 None。SQLite `BEGIN IMMEDIATE` 将读额度、核验、写预留合为事务。额度按 UTC 日期分区。
- `settle_budget(reservation_id, charged_tokens=None, *, status=None, now=None)`：已知 usage 结算实际 token；未知 usage 保守保留预留量。省略 charged_tokens 代表未知，不能将未知结算为免费；相同结算幂等，已知结算不能重写。未知/过期记录允许后到的实际 usage 解决。
- `budget_usage(scope, *, now=None)` 返回当日 used_tokens/reserved_tokens/day。重启读取同一账本。升级前的旧 usage 日志按 provider/scope 导入，使用单调日志游标和稳定 ID 去重；新日志携带 budget_reservation_id，不重复计费。
- 每次 provider attempt 都先独立预留，重试也需重新通过额度检查。响应已到但 schema/截断/空内容校验失败仍结算 usage。超时、网络错误、取消及其他供应商调用异常均按未知计费记录，防止“失败即免费”的绕过。
- reservation TTL 有界为 1–3600 秒。过期将 running reservation 转为 unknown，仍占其原 UTC 日的额度；下一 UTC 日使用新的分区。跨午夜的晚到结算归原预留日。
- `BudgetExceeded.reason` 区分 `request_size`（默认，兼容已有上下文报错）与 `daily_limit`，供 worker 决定修正材料或等下一额度窗口。
- `retry_job(job_id, *, clear_result=False, now=None)` / `cancel_job(job_id, *, reason=..., now=None)` 提供显式运维入口。检查 agent/user 域、活跃 lease 和终态；默认重试复用已保存结果，避免再付费生成，clear_result=True 才丢弃结果。过期 lease 可取消，旧 owner 不能复活任务。

这些改变支持持久 Agent 在长期积累和进程重启后维持连续、可解释的成本与任务状态；不会把重复尝试当成新的外部生活经历或人格证据。

## 实际验证

最终定向命令：

```powershell
.venv/Scripts/python.exe -m pytest -q tests/test_gateway.py tests/test_shared_budget.py tests/test_jobs.py --tb=short --basetemp=reports/fix_budget_tmp/run3 --junitxml=reports/fix_budget_2026-10-20.xml
```

结果：**23 passed，2.58 秒**。其中 15 项为新增共享预算/恢复检查，原 Gateway 与 JobQueue 的 8 项正常回归通过。包含 4 个真实独立 Python 子进程同时竞争同一合成 SQLite 额度，仅一个 600-token 预留可进入 1000-token 日额度；双 Gateway 并发前预留、跨 domain/重启、UTC 换日、晚到 usage、模拟崩溃 TTL、取消、每次重试、schema 错误计费、旧日志迁移及运维 lease 保护均通过。

首次执行因 `reports/fix_budget_tmp` 父目录尚未建立，15 个 tmp_path fixture 报 FileNotFoundError，5 个无需 tmp_path 的原测试通过。建立该独立父目录后执行通过；最终 XML 对应上述完整 23 项结果。没有安装依赖、没有读取真实 var 或凭据、没有新增 API 请求。没有宣称完整项目测试或真实供应商计费核对已完成。

## 边界与限制

- 共享范围是**同一个 runtime SQLite 文件与同一 scope**。不同 root/runtime 数据库使用同一个 API 账号，当前无法形成账号全局额度；需由部署方统一账本。默认 provider scope 会保守合并同一 runtime 中的多个同供应商账号；需要区分时应显式使用稳定且不含秘密的账号 scope。
- 每个调用者传入 daily_limit；同一 scope 的部署应配置相同的额度策略。配置更高额度的另一个实例可采用更高上限，账本不是账号侧强制限额服务。
- token 上限是本地保守估计与供应商 usage 的预算，不能证明供应商实际账单上限。供应商实际回报超过预留量时仍忠实记入实际 usage，随后阻止超限的新尝试；已经发生的收费不能撤销。
- 未知失败保留额度可能造成保守拒绝，包括供应商内部在网络前失败而未给出可验证“未收费”结果的情况。这是有意避免静默退款；到 UTC 换日恢复新额度，不因 TTL 到期自动免费。
- 旧版本在崩溃前完全没有写出 usage 的已发生请求无法从旧日志恢复；本次升级后的请求在 IO 前即写预留。
- 本轮未引入新的 retry/replay 自动语义，未修改人格或记忆档案，也没有测试长期语义质量。
