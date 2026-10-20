# V1 验收报告

2026-10-20修复补记：本文审查发现现已有0.1.1离线修复，当前状态与178项完整回归见[持久运行修复](persistence_fixes_2026-10-20.md)。以下保留原审查证据，不能把历史未修状态当作当前结果。

最新增强验收：用户指定2/3已接LLM语义压缩/状态激活；116项正常回归全部通过（49.64s），新增两次官方deepseek-flash合成请求均通过，无人格/状态版本误改。范围与用量见llm_context_upgrade.md/live_context_smoke.json。仅关闭本增强实现项，不将下文其他已知审查问题和长期语义验收关闭。

## 最新审查状态（2026-10-20）

**完整验收重新开放。** 下文80项通过及live smoke是已有证据，不能覆盖本轮新发现。组件审查复现了2个索引/检索一致性缺陷、普通聊天行动反馈集成缺口等，详情component_review.md/json、audit_memory_2026-10-20.json。本轮27项正常定向检查通过，2个strict xfail明确表示缺陷尚未修复；未改生产代码，没有新增API调用。尤其R07/R13当前只验证人工构造的行为反馈接口轨迹，尚无日常聊天自动归因闭环；R04历史图快照、R03并发索引发布、R10时间输入/复审、R05上下文元数据等需修正并重验。

2026-10-20。结论：**V1本地验收及官方DeepSeek生成/JSON/tools/thinking短smoke完成；A6/A7真实判断与长期语义验收仍pending。** 用户已授权并完成13次官方生成请求；没有联系人发送或外部部署。

## 实际证据

- 正式Python3.12 .venv执行pytest，最终计数与耗时见pytest_results.xml（交付前复核）；覆盖真实子进程崩溃与Windows跨进程CAS，不是仅mock恢复。
- TF-IDF实际拟合、多视角实际运行、BGE int8 ONNX CPU真实512维推理；同空间同步/异步/重启一致，空间迁移/维度错误拒绝。
- Leiden实际运行，多分辨率/递归、孤点、谱系与软主题归属；clustering_baseline.md有参数/seed/结果。没有LLM手工分类冒充聚类。
- demo_trace.json：电影事件十次重提后仍3个独立根；真实新反馈后4根；激活不增根。只有P03变化，P01/P02哈希保持，状态consolidated链接真实PersonaChange；另一念头放弃且压缩/重启不复活。demo_archive.zip可恢复检查完整轨迹。
- 36合成会话24开发/12留出，B0–B4条件、单/多视角、临时状态off/all/context；实际负结果保留于evaluation.md/json。B4非live语义效果宣称。
- wheel/sdist已实际构建；独立新环境安装锁定依赖与wheel，在源码目录外加载包内prompt、执行chat/后台/doctor（ok=true）。不依赖editable开发目录。

## R01–R13核对

|需求|实现/验证|边界|
|---|---|---|
|R01 外部API与定制|DeepSeek HTTP适配+显式paid gate、协议fixture/截断/重试/预算|官方Flash协议smoke已通过|
|R02 文本经历与日期人物|不可变Record+manifest、Event spans逐字校验、FTS与日期人物过滤|未知发生日不填创建日|
|R03 向量/聚类/图|真实TF-IDF/BGE、双视角对照、类型图、真实Leiden|相似不是支持；图未证明稳定提升|
|R04 关联临时原文读取|RecallBundle版本/理由/路径/反例、read_record/来源分层|预算省略来源明确列指针|
|R05 自动/手动压缩|相同Compactor、来源重建、保留约定/引文、完整协议边界|摘录基线，不冒充神经摘要|
|R06 语义人格修订|A6/A7结构schema与绑定patch、局部CAS原子提交|A6/A7真实判断与长期语义质量待验|
|R07 渐进状态再持久|A5→A8→尝试/反馈→A6/A7→patch完整fixture|没有固定次数自动巩固|
|R08 人格过程可回忆|PersonaChange链接前后/事件根/反例，变化文本索引、恢复新版本|不以变化记录自证经历|
|R09 认知子代理|A1–A8受限gateway任务、独立prompt/预算、Proposal提交|fixture与真实语义分开|
|R10 周期夜间空闲|持久队列/租约/虚拟时钟跨日、错过窗口合并、材料幂等|程序关闭时不活动|
|R11 模型理解+程序完整性|聚类算法与语义边分离；defer/失败明确|没有静默空结果冒充分析|
|R12 持久临时池/情境激活|统一TemporaryEntry视图、同空间向量/词面注意预算、撤回失效|干扰评估已报告|
|R13 先尝试再调整/放弃|assistant消息行动证据、未知回应、反馈/迟到反馈/放弃、历史恢复|草稿不等于发送，E01禁用|

## 故障、并发和边界

文件写入/manifest发布/投影更新故障点，真实进程终止、单写锁释放、重启幂等、跨进程CAS、投影删除重建、来源缺失/篡改/隔离、工具往返/重启边界、超时/429/结构错误/截断/预算、撤回/反馈/旧摘要、局部patch旧hash/版本冲突与restore均有测试。

失败修复保留：Windows未关闭SQLite连接阻止投影删除；空过滤误召回运行日志；尝试正文无话题词导致漏反馈；大运行来源链挤掉人格变化；人格变化没有索引diff/replacement；迟到反馈被关闭意图拦截。已分别加入回归，未绕过断言。

## 仍未完成的验收

官方DeepSeek生成/工具/thinking/JSON与返回usage已验证，费用为保守估算未读取实际账单；A5/A8在纯合成材料上短测并恢复通过，不能证明长期语义质量。A6/A7真实人格判断、远程Embedding服务和长期人工角色连续性仍未验证。详见live_smoke.md与docs/交付与限制.md，不能把短协议smoke解释为所有语义验收完成。

## 2026-10-20 追加live与安全验收

官方DeepSeek-V4.1-Flash已实测：GET/models、基础生成、JSON Schema、工具往返、thinking+tools均通过；13次生成，输入6664/输出1999，保守峰值估价USD0.004247472（非实际扣款）。认知链真实测试暴露A8泛对象schema不足，非法active状态被正确拒绝；新增TemporaryEntry完整schema与prompt v2后只重跑受影响任务，恢复成功。历史失败保留，没有mock成功。A6/A7真实人格判断与长期语义质量仍未验证。

密钥位于Windows Credential Manager，项目内不保存实际值。安全回归12项覆盖backup/restore及真实临时wheel/sdist fake sentinel（含大小写/YAML），实际key排除扫描0匹配，见secret_exclusion.json。默认配置仍关闭paid；仅忽略的本地live配置在显式live命令下启用测试预算。未启动常驻付费worker，无真实联系人消息/部署。最终测试现为80 passed（最新XML为准）。
