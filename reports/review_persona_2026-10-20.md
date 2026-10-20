# 人格、临时状态与 LLM 激活独立审查

2026-10-20。只读审查；只新建本报告、唯一探针和 `reports/review_persona_tmp_20261020/` 内合成数据。没有读取 `var/`、凭据，没有网络或安装依赖，没有修改生产源码。全套回归由主 Agent 统一运行。

已读 `docs/01_工程规划书.md` §9、`reports/component_review.md`、`docs/adr/0005-llm-context.md`。审查 `persona/{patch,state,temporary,activation}.py`、`cognition/{persona_revision,reviewer,temporary_state,tasks}.py`、contracts、提交边界及相关测试；为确认调用边界补读 app、import 和 doctor。

结论：没有在本分工发现新的常规聊天人格证据绕过。确认一项较窄的公开 Python API 契约缺陷（P2），另有一项生命周期策略不一致建议；A8 正常生产路径对这些输入另有防护，不能把它们描述为常规聊天模型可以直接制造人格变化。

## P2 / PERSONA-01：create 可以持久化没有 PersonaChange 的 consolidated 状态

- 位置：`D:\DS_workspace\MYATRI\src\myatri\persona\temporary.py:35-46`；契约弱检查在 `D:\DS_workspace\MYATRI\src\myatri\contracts\__init__.py:117-122`。
- 触发：直接调用 `TemporaryStates.create(TemporaryEntry(..., status="consolidated", persona_change_ref="missing_change@1"))`；origin 使用真实存在的合成 cognitive_run。
- 原因：create 检查 origin，但没有拒绝 consolidated；TemporaryEntry 仅要求 `persona_change_ref` 非空，不核查实际记录、更不要求与人格更新原子发布。该字段不进入新状态的 `source_refs`，档案的来源存在性校验也捕获不到。
- 实测：成功持久化 `fake_consolidated@1`；persona 仍 `persona@1`，档案中 PersonaChange 数量为 0。`doctor()` 会报 `missing consolidation source`，所以运维检查能发现，写入时却已违反 §9.7 不变量。
- 影响范围：调用该公开业务 API 的脚本、兼容包装 `apply_recent_feeling()` 或未来集成可能写入虚假巩固状态。当前 A8 新建状态 schema 固定 open，且 `import_record()` 明确拒绝 consolidated（`cognition/temporary_state.py:9-10,39-40`、`interfaces/inspect.py:59-62`），因此普通聊天和手动 import 的这两条路径已有防护。
- 建议：在 create 边界拒绝 consolidated，仅 `PersonaPatcher` 的原子批次能建立它；如允许初始化其他历史状态，单独说明允许状态集合。
- 与旧报告：不重复；旧 M5 宣称的“consolidated 与人格变化原子关联”需要加上上述 API 例外。

## 生命周期建议 / PERSONA-02：明确退休状态经过 settled 后能否重新激活

- 位置：`D:\DS_workspace\MYATRI\src\myatri\persona\temporary.py:53-59`。
- 触发：对同一 ID 依次调用 `review(open→discarded)`、`review(discarded→settled)`、`review(settled→open)`，各次提供当前 base_revision。
- 原因：禁止复活只检查当前状态为 discarded/consolidated 且下一状态为 open/paused；允许先转成 settled 后，下一次检查不再知道它已经退休。程序错误文案要求新建 linked state，A8 也拒绝退休状态更新；但 §9 没有定义完整终态转移矩阵，各次 API 调用都有显式 reason，不能仅凭这条显式操作链断言产品一定要求绝对终态。
- 实测：直接 `discarded@2→open` 被拒；中间链却产生 `retirement_probe@4`、状态 open；异步 `aselect_active_entries()`（本探针关闭 LLM、使用明确启发式）再次选中该同一 ID 的 @4。
- 影响范围：公开 review API 不能保证其错误文案所述“退休后必须创建新 linked state”。未观察到常规 A8 会执行它：A8 更新时直接禁止 discarded/consolidated（`cognition/temporary_state.py:50-52`）。CLI 目前只有 dismiss，没有 reopen 操作。它不是旧摘要直接复活，也不是 LLM 激活器漏查当前生命周期。
- 建议：先明确生命周期策略。如 discarded/consolidated 是终态，应拒绝其全部离开转换；若允许人工重新考虑，应有明确恢复语义，并统一错误文案和 A8/API 策略。把允许转移矩阵集中起来供业务 API 与 A8 共同使用。
- 与旧报告：不重复；既有测试仅覆盖直接 discarded→open，没有覆盖中间状态绕行。本项作为策略一致性建议，不列入确认生产缺陷数量。

## 有效保护与已知边界

- `event_roots()` 对 reported/observed Event 才计独立外部根；reflection/cognitive_run/raw assistant 不会成为新外部根。PersonaPatcher 进一步要求 evidence_refs 本身就是外部 Event 根，不能直接用生成念头或行为记录代替。
- A7 覆盖读材料并绑定确切 patch hash；人格旧版本/hash、状态与 attempt 的当前版本、最终 CAS 和局部 entries 更新已有实际代码保护。未发现更改 replacement 后复用原 A7 的路径。语义审阅是否合理仍需要独立样本，不以结构保护推断模型判断质量。
- 新异步 LLM 激活路径限制候选、数量和 UTF-8 字节预算；await 后复核所有输入候选版本，trace CAS 发生冲突会重查，连续失败返回空集合。已撤回候选不能因等待中的模型结果重新入选。候选上限和降级是已记录设计边界。
- 额外检查 `record_attempt_feedback(decision_status="attempted")`：只要引用持久 assistant 原文并提供 occurred_at，就能接受任意占位文本，不执行“文字语义确实完成该意图”的程序证明。这是语义归因边界，不计本轮缺陷；探针结果仍是 outcome_unknown=true、event_roots=[]，不能把该记录当独立外部成功证据。普通聊天尚未接通行为归因仍是旧 A05。
- 旧 A04 仍在：TemporaryEntry.review_at 接受任意字符串，调度直接 parse/aware 比较。旧 A05、A06、A02 在本分工仅作为已知问题引用，不重复计新发现。

## 复现记录

命令：

```powershell
.venv/Scripts/python.exe -X utf8 reports/review_persona_probe_20261020.py
```

退出 0，1.99 秒；探针 assertions 全部通过。没有付费调用、没有生产数据访问。此次合成目录如下（审查结束已清理，可用探针重新构造）：

`D:\DS_workspace\MYATRI\reports\review_persona_tmp_20261020\39861cd91a134c2ca035f0ca8f4fe3c3`

关键 stdout：

```json
{
  "create_consolidated": {
    "accepted_ref": "fake_consolidated@1",
    "persona_revision": 1,
    "persona_change_count": 0,
    "doctor": ["missing consolidation source"]
  },
  "indirect_reactivation": {
    "direct_reopen_rejected": true,
    "status_chain": ["open", "discarded", "settled", "open"],
    "reactivated_ref": "retirement_probe@4",
    "activation_selected_refs": ["retirement_probe@4"]
  },
  "arbitrary_assistant_action": {
    "accepted_ref": "arbitrary_attempt@1",
    "external_event_roots": [],
    "outcome_unknown": true,
    "classification": "known semantic boundary, not code-review finding"
  },
  "paid_calls": 0
}
```
