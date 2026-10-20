# 运行调度与模型预算独立复核

2026-10-20。只读复核 `app.py`、`runtime/jobs.py`、`worker.py`、`scheduler.py`、`providers/gateway.py` 和 `interfaces/cli.py`，对照 `docs/运行与恢复手册.md`、`docs/01_工程规划书.md` §10 与 `reports/component_review.md`。没有读取 `var` 中的实际用户数据、配置密钥，没有调用网络或安装依赖，没有修改生产源码。

复现命令：`.venv/Scripts/python.exe reports/review_runtime_probe_20261020.py`。探针只在 `reports` 下自身创建的临时目录构造合成档案，并在退出时清理；付费调用 0 次。未重复主审查运行的完整回归。

## 新发现 R01：后台本地索引占用前台事件循环（P2）

位置：`D:/DS_workspace/MYATRI/src/myatri/app.py:107`、`:111`；`src/myatri/memory/index.py:73`、`:88`、`:116`、`:121`、`:143`；`src/myatri/memory/embeddings.py:46`。`Application` 在与聊天相同的 asyncio 事件循环直接运行 `index.update()`。虽然接口声明 `async`，默认 TF-IDF 的 `embed()` 实际直接返回同步 `transform()`，其前后拟合、全图构建、Leiden、JSON/磁盘发布也不让出事件循环。

实测：28 条约 350 字的真实合成事件，在真实默认 TF-IDF/Leiden 路径执行 `app.index.rebuild()` 耗时 **1.487 秒**；在它开始前已经运行的 1ms 并发 ticker，在整个重建区间推进 **0 次**。这是本地流水线实际运行结果，未用 sleep 或模拟聚类人为制造阻塞。交互式聊天会同时启动 `run_background()`，因此这段时间无法接收或继续处理前台协程；同一事件循环的任务租约心跳也无法执行。更大档案下若同步区间超过租约，可能放大重领/重复重建风险；本轮没有声称复现了默认 120 秒租约失效。

建议将本地嵌入/构图/聚类/序列化放到专门线程或工作进程，并以不可变输入快照交接、单写发布；不能只添加无实际让出的 `async`。同时补充前台响应时延/事件循环最大阻塞时间的验证。

## 旧 A06 的影响范围扩展：A1 也会停止整理新经历（P1）

位置：`D:/DS_workspace/MYATRI/src/myatri/cognition/experience.py:31`、`:42`、`:47`；`D:/DS_workspace/MYATRI/src/myatri/contracts/__init__.py:202`。A1 在非 fixture 路径将**全部历史 Event 的正文和完整 payload** 打进每次请求，而且使用 `ModelRequest` 默认 16000 的请求预算。普通离线 fixture 特判绕过这一请求，所以常规离线聊天成功不能证明该扩展性。

实测：与旧 A06 同级的 28 条约 350 字事件，给新的短消息调用 `ExperienceOrganizer.propose()`，在离线的非 fixture provider 路径直接 `BudgetExceeded("full request including tools/protocol exceeds token budget")`，provider 进入次数 **0**。同一数据的 A5 也在调用前被预算拒绝。A1 的故障会阻断新消息 → Event → 索引后续链路，影响不止反思；用户原文仍持久保留。`Worker` 对 `BudgetExceeded` 固定延迟一小时后重试相同无界材料，时间过去不能消除请求大小问题。

建议把 A1 去重候选改为有界召回/指纹筛选，把 A2/A5/A6/A8 材料改为增量水位、有限邻域、关联状态及有预算的反例集。把“请求尺寸过大”和“当天额度用尽”分开处理；前者需要重新规划材料，不能原样定时重试。

## 已知问题仍开放

|旧 ID|优先级|本轮实际证据|关键位置|
|---|---|---|---|
|A04|P1|契约接受 `review_at="2026-10-20"`；实际调用 `app.run_background()` 抛 `TypeError: can't compare offset-naive and offset-aware datetimes` 并退出。一个状态可阻断整个后台循环。|`D:/DS_workspace/MYATRI/src/myatri/app.py:248`；`src/myatri/contracts/__init__.py:112`|
|A01|P2|9 个主题中前 8 个已完成，第 9 个待总结，`_cycle()` 创建主题任务 0 个。|`D:/DS_workspace/MYATRI/src/myatri/app.py:124`|
|A02|P2|旧到期复审已成功后加入新 Event，专门复审仍只有原来的 succeeded job；持续 idle 相隔 1 秒再次 tick 就改写 last_scheduled。普通新事件 cycle 仍可能处理该状态。|`D:/DS_workspace/MYATRI/src/myatri/runtime/scheduler.py:38`、`:39`|
|A07|P2|两个同时构造的 Gateway 共享同一 SQLite usage ledger，各设 daily limit=1100，合计接受并记录 1800 tokens。日志共享不等于预算预留原子共享。|`D:/DS_workspace/MYATRI/src/myatri/providers/gateway.py:164`、`:185`；`src/myatri/app.py:58`|

建议顺序：先修 A04 和 A06/A1，随后修主题公平排程、复审输入水位、R01 前后台阻塞与共享预算预留。A04 既应在契约入口规范化带时区时间，也应隔离单条坏状态，避免使整个后台退出。

## 运行维护意见与保留判断

- 已存在的队列租约 CAS、生成结果先保存再 apply、档案提案幂等，确实能支持已持久化结果的重放；没有把这些正确边界误报成问题。
- 暂时失败三次后会进入终态 failed，`recover_pending()` 再次 enqueue 同一个键不会复活任务，而 CLI 的 `jobs` 只有 list。建议增加显式 retry/cancel 和失败计数告警，否则修复网络/配置后缺乏清晰的运维恢复操作。这是操作入口建议，不把有限自动重试本身判为缺陷。
- `run_background()` 创建 worker Task 后没有监督其完成/异常；交互式 CLI 也只在退出时等待该后台 Task。建议使 worker 意外退出能及时报告并触发有界恢复。本轮未人为制造真实 SQLite 30 秒写锁或网络故障，因此不将其列为已复现新缺陷。
- 日额度按 UTC 日结算，而调度默认上海时区；这两个约定可并存，但应在 `cost inspect` 中明确预算结算时区。
- 本轮验证不覆盖真实账单、长达 120 秒以上的 CPU 阻塞、长期排程、多进程付费网络竞争或角色语义质量。

## 探针输出

```json
{
  "paid_calls": 0,
  "production_code_modified": false,
  "A01": {"theme_jobs": 0, "waiting_theme": "t8"},
  "A02": {"reviews_after_new_evidence": 1, "old_review_status": "succeeded", "idle_rewrites_meta": true},
  "A04": {"real_background_exception": "TypeError", "message": "can't compare offset-naive and offset-aware datetimes"},
  "A06_A1": {"event_count": 28, "exception": "full request including tools/protocol exceeds token budget", "provider_calls": 0},
  "A06_A5": {"event_count": 28, "exception": "full request including tools/protocol exceeds token budget", "provider_calls": 0},
  "R01_event_loop_blocking": {"event_count": 28, "index_seconds": 1.487, "concurrent_ticker_advances": 0, "timer_started": true, "backend": "real-default-TFIDF-Leiden"},
  "A07": {"shared_charged_tokens": 1800, "per_gateway_limit": 1100}
}
```
