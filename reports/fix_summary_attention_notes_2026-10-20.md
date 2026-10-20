# 长期语义摘要注意力补修

2026-10-20。只改 `src/myatri/conversation/context.py`，新增 `tests/test_summary_attention.py`；没有改压缩存储、API、模型调用、行为归因或原有测试。

## 确认问题

语义要点在每轮增量压缩后追加保存。原投影按最旧到最新遍历，在 5000B 内依次取要点，因此长期保存虽然完整，近期变化可能永远进不了模型上下文。复现并非只看摘要存储：新回归读取实际 ContextBuilder 生成的语义摘要消息，并把新 change 后再追加七条原文，确保不能依赖最近六条原文掩盖此缺陷。

## 修改

- 用原始消息在固定快照中的顺序确定近期材料，以查询词面二元组和完整短语命中分配相关性；不调用模型，也不把词面相似当作新事实或人格证据。
- 在同一个 5000B 要点数组预算内先保留互补材料：早期约定、最新变化、查询相关约定/材料、待解问题、最近材料，再按相关性、类别和来源先后补满。超大单条跳过，不让一个候选阻断后续可容纳材料。
- 选中条目按来源先后呈现，早期约定可与后续变化同时可见。说明这是注意选择、不裁定冲突；保留逐条 source_refs、完整持久摘要及省略来源指针。JSON 数组分隔符也计入 5000B。
- 原有摘要 persona/state 失效过滤保持执行，注意选择只在当前有效摘要被选中后发生。旧快照摘要与当前人格不匹配时，专用摘要区和回忆材料区均不会重新引入它。

## 验证

正常联合回归：

```powershell
.venv/Scripts/python.exe -m pytest tests/test_summary_attention.py tests/test_context.py tests/test_llm_context.py tests/test_protocol_recovery.py -q --tb=short --basetemp=reports/fix_summary_attention_tmp --junitxml=reports/fix_summary_attention_2026-10-20.xml
```

**36 passed，47.50 秒**。新增三项使用合成档案、真实增量压缩入口及离线脚本 provider：

1. 密集旧历史下，早期 agreement、近期 change、open_question 和位于中间的查询相关 fact 同时进入有界摘要；change/question 不在最近六条原文内，省略条目仍可回读。
2. persona 更新使旧语义摘要失效，即便请求旧快照，旧摘要也不通过专用块或 Recall 再现。另补断言确认该旧摘要确实会被生产同预算 Recall 找到，然后被 ContextBuilder 过滤；补断言后三个新测试再次 **3 passed，7.66 秒**。
3. 连续三轮增量压缩、每轮重开档案，旧约定保留，最新变化与本轮新约定可见，模型输入仅含尚未处理的原文；精确 span 与原文仍一致。

在独立探针进程中把 `_summary_attention` 临时替换为原来的前缀策略，密集历史回归准确因 `new_change@1` 未投影而失败（1 failed，3.16 秒）。探针只改进程内方法，没有回改源码；预期失败不计入正常通过数。

所有写入都在独立 reports pytest 临时档案，没有网络调用、真实凭据或真实 var 运行档案访问。

## 限制

这是有限注意的确定性来源/词面基线。它不自动判断约定是否已撤销，也不宣称知道哪条陈述仍然成立；冲突理解仍需结合原文与之后变化。预算内不可能同时投影任意多条重要材料，省略条目仍保存在摘要和原始档案，可通过来源读取。真实模型在长周期里理解变化、履行约定的质量仍须独立场景评估。
