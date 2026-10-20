# V1 本地评估

2026-10-20；36个合成会话，24开发/12留出；固定seed17。真实本地向量和Leiden，0付费调用、0外发。

B0最近事件；B1单事件向量；B2加入有限图邻居；B3混合回忆含主题；B4为相同检索预算下认知fixture不改变查询的结构条件（完整反思/临时状态/人格闭环另见demo_trace.json）。均top5，B3/B4相同6000预算；B4不代表真实模型人格质量，真实语义消融待live与长期人工评估。

|后端|条件|留出Recall@5|留出MRR@5|中位延迟ms|
|---|---|---:|---:|---:|
|tfidf|B0_recent|0.167|0.125|220.64|
|tfidf|B1_single_vector|1.000|1.000|1.14|
|tfidf|B2_vector_graph|1.000|1.000|0.89|
|tfidf|B3_graph_theme|1.000|0.958|443.81|
|tfidf|B4_fixture_context|1.000|0.958|445.66|
|tfidf|multi_view|1.000|0.764|1.31|
|bge_local_onnx|B0_recent|0.167|0.125|259.38|
|bge_local_onnx|B1_single_vector|1.000|0.958|2.47|
|bge_local_onnx|B2_vector_graph|1.000|0.958|2.02|
|bge_local_onnx|B3_graph_theme|1.000|0.958|513.39|
|bge_local_onnx|B4_fixture_context|1.000|0.958|513.59|
|bge_local_onnx|multi_view|1.000|0.917|3.50|

临时状态消融：`{"off": {"injected": 0, "relevant_injected": false, "irrelevant_injected": 0}, "all": {"injected": 6, "relevant_injected": true, "irrelevant_injected": 5}, "context": {"injected": 4, "relevant_injected": true, "irrelevant_injected": 3}, "limitation": "relevance labels are synthetic topic labels; lexical activation scores are heuristic, not psychological probabilities"}`

完整逐例结果、开发集与负结果见evaluation.json，语料与人工合成目标见evals/corpus.json。未调参到留出集。

局限：相似不是同义；BGE对否定句相似度可很高。图/主题可能无提升或降低排序，不据此宣称图更好。语义边和认知输出使用带标签fixture验证结构，不冒充真实A2/A5/DeepSeek推断。成本为本地CPU耗时，API价格与真实网络延迟未验证。来源/隔离/幂等硬约束另由pytest故障/并发/状态测试验收。

## 评估解释补充

语料为刻意简短的合成会话，查询保留人物/话题/感受关键词，因此Recall@5高不代表真实开放域效果。evals/annotations.json提供允许关联与不得合并的独立事件对，群落不设唯一金标准。B0含档案读取、B1/B2主要内存索引、B3含来源读取/检查，延迟是当前评估程序的实际成本，不直接当作生产用户响应SLO。

负结果：本轮TF-IDF加入图/主题后MRR从1.000降至0.958，多视角降至0.764；BGE多视角0.917也低于单视角0.958，不能宣称堆叠组件必然更好。临时状态按情境注入仍选入3个标签判定的无关状态（全部注入为5个）；注意分配仍有干扰，未据本留出集反复调参。保留这些结果以便后续用真实语义服务和独立样本评价。
