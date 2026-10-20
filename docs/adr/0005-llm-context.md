# 0005：语义压缩与临时状态激活使用LLM

2026-10-20，用户明确授权建议2/3的代码修改。

前台Conversation使用ContextBuilder.abuild_context；ActivationSelector.aselect_active_entries通过同一Gateway对有界open候选进行语义选择，允许选空，返回候选ref与理由。程序保留数量/UTF-8预算、版本/生命周期校验和CAS trace；选择不是行动/反馈/人格改变。词面/向量仍用于候选排序与明确标注的降级。

Compactor.acompact将原文按UTF-8分批，LLM提取约定、偏好、未决事项、变化和不确定性；每条要点必须引用本批逐字原文，后端计算SourceSpan并核验。保留全部原文和显式preserve；不递归压缩旧摘要。模型输出正文作为派生转述，不充当逐字引文或人格权威。摘要绑定人格/状态版本，两条注入路径（摘要区、回忆区）都过滤失效摘要。

两个新role使用foreground并发通道，业务role/usage日志仍独立。自动压缩、/compact、CLI compact/context均接入异步路径；普通离线命令不访问真实API。config.context.llm_compaction/llm_activation缺省true，公开paid gate仍false。旧同步接口保留给确定性离线基线和历史测试。

失败/超时/预算/非法引用/defer均明确降级；不发布部分语义摘要、不静默当模型成功。激活最多12候选/6000B材料，正文激活预算默认600B/4条；压缩每批材料约9000B、每次最多8批，超过上限明确降级，尚无增量语义缓存或长期质量保证。固定规则/显式保留内容过大仍抛预算错误，不任意裁切。

接口和本地恢复已验；官方API仅2次合成smoke（各一次），详见reports/live_context_smoke.json。长程事实保真、语义重排收益需要独立样本，不能从schema和短smoke推导。原M01/M02等其他审查问题仍开放。
