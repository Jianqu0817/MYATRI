# memory Agent

状态：DOC-MEM-04 新设计稿与工程规划0.3只读核对完成，4条文档准确性/实施适配建议已交主Agent；此前实现、补验与审查记录保留。禁止继续创建子 Agent。

当前归属：src/myatri/storage/**、src/myatri/memory/**、src/myatri/retrieval/**、对应测试、tests/test_persona_lifecycle.py、tests/test_context.py、tests/integration/test_v1_lifecycle.py、reports/clustering_baseline.md 与本文件。
本轮DOC-MEM-04仅允许修改本进度文件，其余源码和公共文档只读。
公共契约、依赖、runtime/commit.py 与公共进度由主 Agent 负责。

已落盘：ArchiveStore，跨线程/进程单写锁，隔离域、不可变内容寻址 JSON、manifest-last 发布、快照、CAS、幂等、防路径穿越、来源检查、SQLite 可删重建与 FTS 投影。原始消息/事件拒绝新 revision；解释可显式 supersede。

验证：conda Python，`$env:PYTHONPATH='src'; python -m pytest tests/test_storage.py tests/integration/test_commit_recovery.py -q`，16 passed。真实子进程 os._exit 崩溃点和 Windows 跨进程 CAS 均通过；首测发现 SQLite 连接未显式关闭阻止 unlink，已修复并重测通过。FTS 使用 trigram，中文匹配已验证。event/interpretation spans 校验已加入（事件模型、来源role与逐字原文）。未做网络、付费 API 或真实发送。代码均为原创实现，无第三方源码复制。

T07–T09 当前落盘：本地真实 sklearn char1–4 TF-IDF provider（不是神经语义模型）、精确空间校验索引、内容缓存、多视角/独立临时状态视角、原子 generation 发布与回退、稀疏度数限制相似图、类型语义边、递归多分辨率真实 Leiden、暂定主题 ID/谱系/软归属、RRF 混合检索/中文FTS/日期人物/反例/原始来源链与历史临时状态。A3 权威主题按 material_hash 覆盖，成员或相关语义边变化会清空旧模型命名/摘要，避免新反例沿用旧事实。

正式 .venv 验证：`.venv/Scripts/python.exe -m pytest tests/test_memory.py tests/test_retrieval.py tests/test_storage.py tests/integration/test_commit_recovery.py -q`，30 passed（12.00s）。报告 `reports/clustering_baseline.md` 已落盘：真实 Leiden 调用 3 次，6 个事件得到 [e1,e2,e3] / [e4,e5] / [e6]；e6 为孤点。事件与双视角各 4 条相似边，未声称多视角必有收益。

公共入口：`MemoryIndex(store, provider=None, space_id=None)`；`await rebuild()/update()`；`query(text,view='event',limit=5,space_id=None)` 返回 ref/score/view/space_id dict；`await aquery` 支持外部异步 provider；`rollback(generation)`；`inspect()`；`theme_materials(theme_id)`。本地同步 provider 可提供 `embed_sync(texts,space_id)`。`RecallService(store,index).recall(query,filters=None,snapshot=None,budget=4000)` 返回 RecallBundle；过滤 kinds/date_from/date_to/participants/person/include_historical，未知事件日期不冒充创建日期。Event/interpretation 的逐字 span 与 raw 原文成组；其余来源分层展开，超预算日志保留 versioned refs 并明确未展开，不再要求整张递归来源图入上下文。

恢复：ArchiveStore 初始化验证 manifest 并重建 SQLite；MemoryIndex 初始化加载域内 indexes/current.json 指向的校验完整 generation。索引目录删除后 await rebuild；旧 generation 保留可 rollback；外部神经 generation 重启需显式提供相同 provider，TF-IDF primitive state 自包含恢复。没有运行进程遗留。

专项集成（第二次委派）：`.venv/Scripts/python.exe -m pytest tests/test_persona_lifecycle.py tests/test_context.py tests/test_retrieval.py tests/integration/test_v1_lifecycle.py -q`，18 passed（22.58s）。覆盖实际表达/无反馈未知/外部反馈/调整与撤回/迟到反馈不复活、反思10次不增加event根、A7精确patch哈希绑定/P03局部原子更新/P01-P02 hash不变/旧patch冲突/真实change绑定consolidated/restore新版本、手动与自动压缩/原文恢复/旧状态摘要失效/协议未闭合拒绝、默认Application队列全succeeded、脚本Fixture A5→A8→A6→A7闭环与重启。

本次发现并修复：
- Recall空值日期/人物过滤误启用全库通道：改为检测有效过滤值，默认排除运行日志/激活/usage/当前人格候选；显式kinds仍可查，来源追踪保留。
- 实际BehaviorAttempt正文只有expressed，词面检索会漏尝试：沿intent/action/feedback显式引用补全召回路径。
- PersonaChange递归run来源链过大导致候选消失：候选+精确span原文原子保留，优先带有限event根，日志引用按预算保留指针和limitation；1800预算+6份巨大历史来源回归通过。
- 迟到反馈被open意图校验拒绝：已报告主 Agent修复temporary.py，本分工加了“撤回后追加已有行动反馈、不变action/不重新激活”回归并通过。

T16 demo 追加定位：原断言失败并非来源预算，实际 PersonaChange 自身只有1082字符成本、budget10000；其body仅保存理由，query“表达期待”仅出现在payload.patch.replacement/diff.after，旧全文与Embedding都不索引这些字段，导致change根本不进候选。已新增 `memory/text.py` 统一显式业务搜索文本，PersonaChange索引局部before/after/replacement/scope；“为什么/更愿意/变化”等相关人格历史查询增加相关change通道。未把审查run或整份payload拼成向量。`.venv/Scripts/python.exe -m pytest tests/test_retrieval.py tests/integration/test_v1_lifecycle.py -q`，10 passed（13.76s），包含kinds=[change]及[change,event]真实A7提交路径回归。`.venv/Scripts/python.exe -m myatri.interfaces.cli eval --suite demo --output reports` exit0：persona_after=persona@2、event_roots=4、doctor_ok=true、paid_calls=0、real_external_messages=0；reports/demo_trace.json 与 demo_archive.zip 已生成，无evaluation源码改动。

真实 BGE 集成 smoke（2026-10-20）：使用已在本地的 `var/models/bge-small-zh-v1.5`，512维固定space `bge-small-zh-v1_5-75c43b069aac-int8-cls-l2`；MemoryIndex真实推理重建→Leiden实际2次→query/aquery一致→Recall含Event与raw→带同provider重启结果一致，top=e1@1。无下载/外部API调用；模型供应商接口与DeepSeek live未验证。

下一步：主 Agent 运行全套验收和evaluation demo并汇总交付。没有遗留进程；无需重复已通过专项测试，除非集成修改触及接口。付费/真实发送/部署均未执行。

## T04/T15/T17-live 安全补验（进行中）

本分工限制：只写 tests/test_secret_exclusion.py 与本文件；公共backup/restore、pyproject和.gitignore由主 Agent改。只生成虚构随机sentinel，不读Windows凭据、环境API key、真实.env或live.local配置，不调用任何API。

已完成只读审查：原backup ignore未覆盖.env/凭据文件/本地live配置，restore仅验证路径；wheel force-include整个config，sdist无显式白名单。向主 Agent提供了精确修改建议。现有dist仅检查成员名称（不读取内容）：wheel63项/sdist186项，未见敏感命名成员；这不能证明未来force-include安全。

已落盘8项回归：运行备份11种虚构敏感路径排除及正常原文恢复、restore提取前拒绝4种虚构敏感成员、在纯公开源码临时副本种植sentinel后真实构建wheel/sdist并查全体成员字节、.gitignore本地live配置规则。构建保留公开defaults/live.example及credentials.py源码，避免过宽规则误删正常功能。不会复制开发者实际凭据或运行数据。

首轮结果：5 failed、1 passed、2 errors，准确暴露backup/restore缺口；打包error是.venv缺已声明构建backend hatchling（测试使用--no-isolation以避免隐式联网），主 Agent已补齐环境并统一规则。基础复测8 passed（7.51s），wheel/sdist真实离线构建均无基础sentinel泄漏。

额外大小写回归发现并由主 Agent修复真实缺口：security.py先lower可排大写.env/私钥，原Hatch exclude小写glob区分大小写，src/myatri/.ENV.LIVE和private.PEM曾在wheel、sdist均泄漏（2 failed、6 passed）。现由主 Agent增加不区分大小写glob及YAML/YML凭据规则；uppercase credentials用独立子目录避免Windows同名文件覆盖造成假阴性。

最终 `.venv/Scripts/python.exe -m pytest tests/test_secret_exclusion.py -q`：12 passed（最终复测6.80s）。覆盖16种备份敏感路径排除、8类restore提取前拒绝，以及虚构sentinel真实wheel/sdist成员字节检查（含包内.ENV.LIVE/private.PEM/upper/CREDENTIALS.JSON/credentials.yaml/upper/SECRETS.YML）；公开defaults/live.example及credentials.py源码仍正常入包。测试的公开副本只复制.py源码与显式公开模板，不复制开发者未知配置/数据，且不跟随symlink/junction。无实际凭据读取或访问，无API调用。

补验结论限于命名排除及本项目标准打包/备份路径；没有做实际凭据内容扫描，也没有代替主 Agent的Windows凭据管理器和官方API验证。主 Agent处理实际key和live调用，本分工未接触密钥。当前无遗留进程，可交回主 Agent统一全套验证和更新交付报告。

## AUDIT-MEM-01：组件讲解前的只读审查

本轮只读 storage/memory/retrieval/contracts 与相关测试；只新增 `tests/audit_memory_consistency.py`、`reports/audit_memory_2026-10-20.json` 并更新本文件，未改生产代码、配置或公共状态。未读密钥、未调用外部 API。

确认缺陷（未修复）：
- **P1 / AUDIT-MEM-01-01**：`retrieval/service.py:169–183` 在旧snapshot查询中使用最新graph，仅检查端点记录可见，不检查edge记录revision。最小复现：snapshot内已有a/b两个事件、没有任何edge；后来新增contradicts边并rebuild；请求旧snapshot依然得到 `counter_refs=[a@1,b@1]`。无索引同查询则无counter_refs。水位warning不能弥补未来语义进入过去快照；主题索引也应有相同世代约束。
- **P2 / AUDIT-MEM-01-02**：`memory/index.py:141–145` 正常发布current时只有文件写锁，无watermark顺序检查。真实TF-IDF embed暂停旧rebuild→写入second并完成新rebuild→恢复旧任务；重启current回到旧水位，向量行只有first@1，没有second@1。档案原文没丢，但索引回退需要下一次rebuild恢复；正常发布与显式rollback应区分。

复现命令：`.venv/Scripts/python.exe -m pytest tests/audit_memory_consistency.py -q -rx` → **2 xfailed（strict，5.88s）**。这表示两个已确认缺陷，不能记成修复通过。审计JSON另记直接调用复现函数捕获的真实断言失败与具体水位/向量行。调度wrapper仅控制时序，未替换TF-IDF/Leiden算法。

针对性正常路径验证：来源span/role、隔离/同提交引用、投影重建、Windows跨进程CAS、3种进程崩溃、真实TF-IDF/Leiden/旧generation回退，共 **8 passed（4.15s）**；完整命令见审计JSON，没有重复整个测试集。

讲解要点：档案manifest是权威与多文件可见性边界，SQLite为可重建投影；Record引用固定revision并由commit检查来源原文；向量按space严格区分，本地默认TF-IDF是真词面算法，Leiden是真群落算法；聚类节点是event根，解释感受可anchor回事件，软归属与模型命名独立于Leiden；Recall混合候选/RRF/typed路径与预算分层原文，不代表检索分数就是真实性。

明确限制：哈希不是对能改写整个档案的攻击者的签名；全档案扫描/全投影改写与精确全图重建仅为V1基线；`theme_materials.time_span`当前实际是record.created_at跨度，不应讲成Event.occurred_at跨度。上述限制与2个确认缺陷分栏记录，不冒充新增失败。

下一步：由主 Agent向用户讲解并确认修复方向；本轮不擅自改生产行为。无遗留进程。

## T12-LLM-ACT：临时状态由LLM判断激活

本轮允许：仅改 `src/myatri/persona/activation.py`、新增 `tests/test_llm_activation.py`、更新本文件；未改公共契约/依赖/context/engine/app/CLI。已检查项目、祖先、src/persona/tests的AGENTS文件，未发现适用规则。

接口：`ActivationSelector(store,index=None,*,gateway=None,llm_enabled=True)`；同步select保持兼容；新增 `await aselect_active_entries(context, snapshot=None,budget=600,max_entries=4,persist=True)`。有open候选且gateway启用才发结构化activation/v1请求；无open候选不调用。最多12条、候选JSON<=6000 UTF-8字节、情境<=2048字节，零词面唯一候选仍进入模型。模型仅选择已有ref及理由，程序拒绝未知/重复/非open/改写字段，按完整正文UTF-8预算及数量约束注入，允许选空及矛盾念头共存。

快照与一致性：固定初始snapshot，await后重读候选revision/status；改版或关闭者不得注入，并明确heuristic_fallback。激活trace以read_versions CAS提交，遇竞态重验；连续3次冲突返回安全空结果，明确trace未持久化。仅写activation记录，不改状态、人格或创建event/attempt；generator保留provider/model/prompt_version/run_id。默认Fixture defer/超时/非法JSON显式heuristic_fallback；有效Fixture结构结果标fixture及not-live limitation，不称LLM真实验证。版本化prompt不可用时用内联activation/v1并注明。

离线命令：`.venv/Scripts/python.exe -m pytest tests/test_llm_activation.py -q` → **18 passed（最终6.95s）**。覆盖无词面同义选择、选空、矛盾共存、超数量/完整正文预算、未知/重复/关闭refs和改写拒绝、timeout/defer/defaultFixture回退、API等待中撤回/改版、无候选不调用、候选/情境材料硬界限、CAS真实竞态与连续冲突安全空，另含持久activation trace重启字段读取、enabled=False确实无API。两个既有同步状态/上下文兼容检查也通过（2 passed，2.49s）。全部使用离线script provider或Fixture，只证明接口与并发安全，不证明真实模型语义质量；没有付费调用、凭据读取。主 Agent已确认有效Fixture结果标fixture即可，不需要改成heuristic_fallback。

按主 Agent要求只读核查异步Context集成：当前新代码已排除await期间撤回的temporary_state，回退selection_method不冒称API成功。另真实离线复现并报告旧summary绕路：固定旧snapshot，激活await期间discard后，独立summary区已omit，active=[]、旧state row也消失，但RecallBundle中的旧summary仍进入memory区，因为comprehension只过滤temporary_state。已建议主 Agent对memory中的summary同样比较state_refs/persona_ref当前版本；未改其context源文件。复现仅用普通合成assistant原文和同步摘录摘要，无外部API。

交回：主 Agent已接收旧summary过滤建议，并负责Gateway将activation/compaction调到foreground并发通道（保留业务role）及整体验证。本分工保持18项专项，不再追加测试；有效Fixture的fixture方法标记保留。实际live smoke由主 Agent按授权决定，本分工不执行付费API。当前无遗留进程。

## COMPARE-LOCAL-01：框架比较前的本地证据核对

只读最新STATUS/HANDOFF、reports/llm_context_upgrade.md、component_review.md、evaluation.md；不重跑测试、不访问凭据、不新增API请求、不改生产或公共文件。

可据证据描述的特点：精确原文span/版本来源；原始事件与解释分轨、重提/反思不自动增加外部根；统一临时状态的持久生命周期与版本激活；绑定证据/反例/A7确切hash的局部人格patch及原子change/consolidated/恢复；真实进程崩溃/CAS/投影重建检查；真实本地TF-IDF/BGE/Leiden；LLM语义压缩与状态激活最新116项回归及各1次官方合成smoke。人格patch语义仍主要是离线结构证据，真实A6/A7/长期连续性未验。

比较边界：上述是角色系统特定约束的定制组合，不是来源追踪、状态机、CAS、向量、Leiden、RRF或LLM摘要的独创/领先证明；未做与Letta/LangGraph/Mem0/Graphiti的同条件对比。现有36个关键词合成会话有明确负结果：图/主题、多视角并未稳定胜过单向量；旧激活消融不是本次LLM升级效果评估。

当前成熟度仍是可本地试用的有边界研究原型：M01旧快照未来关系、M02并发索引倒退、A05普通聊天行动/反馈归因缺口仍开放；A06全量后台材料预算、A01/A02主题/复审排程、A04无时区review_at、A07多实例共享额度待修。角色卡仅3条示例且身份未硬锁。最新升级修补了部分上下文元数据/失效摘要，不等于全V1无缺陷或完整日常闭环已验收。

## DOC-MEM-04：动态人物/技能索引与Embedding文档核对

已只读核对新 `docs/04_动态索引与技能记忆设计.md` 全文、规划0.3新增现状与§5.3/§6.2–6.8，以及contracts、memory/index/embeddings/themes/graph、retrieval、experience和本地ONNX provider。只修改本文件；不改生产/契约/公共文档，不重跑全套测试、不访问凭据、不调用API。

确认核心界线准确：当前人物仅Event.participants姓名字符串与精确过滤，实体身份消歧/Skill/Procedure未实现；默认char1–4 sublinear TF-IDF维度随词表、拟合语料/view决定新space，可选固定BGE INT8/CPU/CLS/L2为512维、tokenizer512 tokens直接截断。四个现有视角不含entity/skill；聚类根是event，感受解释可单根anchor。update仍全量rebuild，M01/M02未修。DMI是未纳入任务JSON的设计待办，检查表未勾选，不冒充已有验收。

向主Agent报告4项具体建议：规划§17与结尾残留“当前交付仅规划/从T00/没有运行”与新首页矛盾；§6.6时间跨度应限定当前为record.created_at而非事件发生时间；DMI-04复用BehaviorAttempt仍需工具执行结果契约适配（当前temporary.py只接受assistant raw_message行动来源），不能把聊天声称当Python实际执行；向量行绑定ref/revision与缓存按text_hash/view/model/revision/dimension/normalization/space跨记录复用应分开表述。主Agent统一决定并修改公共文档，本分工不越权落盘。

本轮结果为源码/文档逐项核对，不产生新算法或语义评估证据。无遗留进程；可由主Agent完成链接检查与公共交接。
