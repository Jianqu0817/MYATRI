# ADR 0004：V1实现范围与验收分层

2026-10-20。原规划保留需求语义；当前按授权完成本地实现，不擅自扩大付费/外发范围。

- 档案统一不可变JSON，正文含body_markdown；人格/主题/状态不额外双写独立Markdown当前卡。模板/prompt仍Markdown。规划允许JSON文本档案；这样避免人工误改派生卡。人工角色调整由persona edit单条human_edit原子记录，初始persona可从Markdown稳定条目模板导入。
- 精确向量/全图Leiden重建为正确性基线，不做尚无规模依据的ANN或局部重聚类；generation、水位和fallback均实装。
- 临时激活使用词面与同空间向量启发，预算内选少量；矛盾可并存，注意和生命周期分离。启发分数不是事实概率。保持评估负结果，不据留出集反复调门槛。
- 压缩采用来源摘录而不是伪造的神经摘要，完整原文可恢复；自动/手动同流程。固定内容超限显式拒绝；模型cognitive输入去掉重复信封字段，并有32000保守字节预算与输出预留。实际token校准/真实语义摘要待live。
- 认知角色是受限gateway任务/Proposal，模型不能直接写档案。A7绑定确切patch hash；worker保存模型结果之后才提交，版本冲突不盲覆盖。
- 完整工具协议保存runtime DB而不是记忆；供应商必要字段用于协议回传，不成为角色念头、外部事件或人格证据。
- 实际测试集中在tests/test_*.py和tests/integration/，按场景命名，未为清单中每个tests/scenarios子目录制造空壳。
- B0–B3与多视角是真实本地检索比较；B4仅同预算的fixture结构条件，不把它称为真实人格语义消融。临时状态消融报告干扰。真实DeepSeek/长期人工评价另列pending，任务completed_local不等于完整live验收。
