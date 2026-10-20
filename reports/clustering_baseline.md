# 真实聚类与向量基线

执行日期：2026-10-20（Asia/Shanghai）。离线合成材料；未调用付费 API、未发送消息。

算法实际运行：sklearn 字符 1–4 gram TF-IDF（词面向量，不是神经语义模型）、NumPy 精确余弦、igraph + leidenalg 的 RBConfigurationVertexPartition。不是手写主题代替聚类。

环境：Python 3.12；numpy 2.4.6；scikit-learn 1.9.1；igraph 1.0.0；leidenalg 0.12.0。

材料：6 个带逐字 raw_message 来源的事件，其中 3 个共同安排/散步、2 个代码修复、1 个海底潜泳；2 条 interpretation 提供独立感受视角并 anchor 回事件。raw_message、reflection、temporary_state 不进入聚类节点。

配置：seed=17，k=2，threshold=0.2；递归 resolution=[0.5,1.25]。实际 Leiden 调用 3 次；事件节点 6，相似边 4。每层是单归属分区，软主题归属是另行计算的检索强度。

| 叶群落 | 事件成员 |
|---|---|
| 1 | e1@1, e2@1, e3@1 |
| 2 | e4@1, e5@1 |
| 3 | e6@1 |

孤立节点：e6@1。孤点保留为 provisional，不强行合并。

| 视角 | space_id | 维度 | 索引记录数 |
|---|---|---:|---:|
| event | tfidf_event_78d0911ec55693fdebbf | 279 | 14 |
| feeling | tfidf_feeling_4b1447a85f553f6c4d3e | 142 | 2 |

多视角对照（相同材料/seed/k/threshold）：事件单视角相似边 4 条；事件+感受相似边 4 条。缺失感受时仅归一化可用视角，不拼接不同空间；这不是有标注召回收益证明。

事件单视角：`[["e1@1", "e2@1", 0.3726], ["e4@1", "e5@1", 0.2643], ["e2@1", "e3@1", 0.2451], ["e1@1", "e3@1", 0.2144]]`。

事件+感受：`[["e1@1", "e2@1", 0.358], ["e4@1", "e5@1", 0.2643], ["e2@1", "e3@1", 0.2451], ["e1@1", "e3@1", 0.2144]]`。

验证命令：`.venv/Scripts/python.exe -m pytest tests/test_memory.py tests/test_retrieval.py tests/test_storage.py tests/integration/test_commit_recovery.py -q`，30 passed。覆盖 space/dimension 拒绝混查、模型迁移/旧代回退、缓存与重启、真实 Leiden/孤点/层次、主题 split/merge/软归属、A3 摘要材料哈希失效、否定反转/来源路径/中文 FTS、隔离与索引滞后、临时状态历史、Windows 跨进程 CAS/崩溃恢复。

限制：样本量小，全部主题仍为 provisional；TF-IDF 否定和跨话题语义能力有限，不能将高余弦解释成支持或同义；语义边单独保存且不进入 Leiden 正相似权重。多分辨率采用父群落内递归算法，不宣称任意局部更新等价于全图最优；V1 update 使用全图重建作为正确性基线。模型 A2/A3 schema 接口离线验证不等于 DeepSeek live 验证。真实神经 BGE 由主 Agent另作明确 smoke 与报告。
