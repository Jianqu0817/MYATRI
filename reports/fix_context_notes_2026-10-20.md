# CTX-01 与摘要增量修复记录

2026-10-20。本分工仅修改 `src/myatri/conversation/{context,compaction,engine}.py` 和三个相关测试文件；未修改 contracts/app/persona/runtime/cognition/memory、依赖或公共文档。没有网络请求、凭据访问、真实 `var/` 访问。

## 已实施

- **重复自动压缩**：sync 与 async ContextBuilder 在现有摘要之后历史继续增长并超预算时，都可再次压缩。使用有限循环替代 sync 递归；默认最多 3 次压缩（可选 `max_compaction_passes`），并比较原文覆盖集合/片段水位。有摘要但新材料未覆盖不再成为拒绝自动压缩的条件。没有水位进展或只剩固定/显式保留/近期原文时停止；仍过预算则明确抛 BudgetExceeded，保留 explain_context 诊断。
- **增量语义摘要**：只对没有处理的原始消息片段调用 LLM。有效旧语义要点原样保留，逐项重新校验原始 SourceSpan 和引用，旧摘要正文不送模型。`processed_segments` 持久保存每条 raw 的连续处理偏移；`source_range` 只记录完整处理过的 raw，单条长消息部分处理后仍留在当前历史。兼容旧版语义摘要的全量 source_range。
- **长历史有界推进**：每次最多处理 max_chunks（缺省 8 批），超过上限发布已完整校验的本次有限进度并明确 pending；后续或重启继续尚未处理的 raw，不再因全部历史超过 8 批而永远退回原文前 160 字。
- **失败处理**：本次所选批次有任意失败/非法引文/defer，丢弃本次未发布语义结果。若有有效旧语义摘要，保留其已验证要点、旧覆盖水位，新增 raw 继续留在历史，并写 fallback 限制；没有有效旧语义结果时保持明确的原文摘录降级。人格/状态变化仍使旧摘要失效，并保留发布 CAS 和上下文双路径过滤。
- **上下文投影有界**：归档保留全部语义要点、来源和诊断；模型上下文只渲染有界摘要要点/摘录，并给出被省略来源的数量、有限 ref 列表和 summary_ref。回忆局限可能随候选数量增长，模型可见诊断投影限制为 1200B，完整内容仍在 explain_context，避免几十/上百条“未注入”警告自身阻断聊天。
- **答案回调**：Conversation 新增可选 keyword `on_answer`，同步传入已持久化的 assistant Record；首次答案保存后调用，稳定 message_id 命中旧答案及重启重试时也调用。消费者负责幂等入队；回调失败会向调用者报错，已持久化答案不丢，重试不再次请求模型。既有 constructor 位置参数和 tools 协议保留。

## 验证

最终命令：

```powershell
.venv/Scripts/python.exe -m pytest tests/test_context.py tests/test_llm_context.py tests/test_protocol_recovery.py -q --basetemp=reports/fix_context_tmp_20261020/base4 --junitxml=reports/fix_context_regression_20261020.xml
```

**33 passed，36.58 秒。** 包含原有来源/失效/工具协议/官方适配 MockTransport 测试与 8 个新增场景：

1. sync 三次历史增长均自动续压。
2. 固定内容过大时停止并明确预算错误，无递归和无界发布。
3. 三次增量语义压缩，每次重启后早期约定与精确原文 span 保留，仅送新增原文。
4. 总材料超过 8 批，含一条跨多批的长消息；每次上限 1 批并重启续做，最终所有原文片段恰好处理一次。
5. 增量失败后旧语义约定保留，新增 raw 没有被标为已覆盖，仍进入历史。
6. async 三次自动压缩并每次重启后，早期约定始终可见，预算满足。
7. on_answer 首次保存、同 ID 幂等重试、重启重试均收到同一已持久化答案。
8. 回调失败后答案可恢复，重试不会重复模型生成。

早期一次 pytest 因嵌套 basetemp 的父目录尚未创建而 setup 失败，已创建独立目录后修正；另更新一项旧断言：原先预期“全部历史超 cap 永久 fallback”，现在验证只处理新 delta 并保留 semantic 策略。最终运行全部通过。

## 边界

- 这验证增量来源、恢复、预算与回调控制流；没有验证真实模型的长期摘要质量。摘要仍是派生转述，原文是权威，不成为新的独立事件证据。
- 保留旧要点不会自动证明它仍是最新事实。新的 change/uncertainty 条目与精确原文可共存；没有实现跨条目的完整语义撤销/冲突裁决。
- 每次 compaction 的网络材料有上限，持久摘要/来源游标总量仍随原文增长。ContextBuilder 每次最多 3 轮，极大积压仍可能明确超预算；已完成的片段水位会保存，后续重试能继续推进。
- 状态/人格发生变化时旧摘要不复用，需要重新从原文建立；持续高频状态变化的重建成本仍需真实使用评估。
- 显式 preserve、运行规则、人格和最近 6 条原文不被任意裁切；这些内容本身过大仍会返回预算错误。
- on_answer 只提供同步持久入队接口；主 Agent 负责 app 的行为归因任务接线，本分工没有在回调里进行 API 或语义工作。
