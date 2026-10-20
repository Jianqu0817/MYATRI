# MYATRI HANDOFF

## FIX-PERSIST-01 最终检查点（2026-10-20，0.1.1本地修复已验）

用户已授权修复审查问题；余额中断后已完成接续。不要退回只读审查或重做规划。ADR0006记录有限注意、原文来源、允许不改变、真实表达/后续反馈与共享预算设计。最终报告reports/persistence_fixes_2026-10-20.md：178项完整回归（138.97s）+最终归因16项复测+打包专项12项均通过。0.1.1 wheel/sdist真实构建、源码目录外实际wheel聊天/压缩/doctor通过，package_smoke_0.1.1.json和dist/SHA256SUMS-0.1.1.txt记录包验证。旧0.1.0留存，当前源码editable也已离线更新至0.1.1，无新第三方依赖。

app接on_answer持久归因队列/后续Event反馈；归因仅expressed，必须来自当时context中的意图/实际助手原文，反馈是动作之后的逐字用户来源，不自动记成功或成长。planned/无时间记录隔离、候选分批、同批重复去重、历史表达不绑定当前状态CAS、并发反馈对同一动作合并不重生成。TemporaryStates.prepare_attempt_feedback供原子提案；默认手动新动作仍验证当前open。Gateway预算同runtime.sqlite3/scope跨domain共享，未知计费不退款；不同root仍不共享账号硬额度。scheduler使用新证据+状态ref键和空闲边沿；新时间要求aware，旧review_at按配置时区兼容，坏记录隔离。

当前完整验收仍不包括新schema真实API语义、长期拟人连续性、Entity/Skill/Procedure/BGE分块与规模优化。只改本地代码/说明/合成测试，没有访问真实用户库或密钥、未付费调用。所有子代理已交回，无遗留服务。测试临时目录保留于reports但打包排除；旧scripts/finalize_status.py已保护，不能用旧80/116测试重置当前任务状态。下一轮按新报告pending推进，不重复已验离线修复或旧live smoke。

## DOC-MEM-04文档检查点（2026-10-20，已完成文档同步）

当前授权是把最近的人物/技能动态索引及Embedding讨论写回MD。DOC-MEM-04已完成；DMI-00–05全部待实现，T00–T17和M01/M02/A05等既有缺口状态不因文档更新而改变。

1. 实际文件：主Agent改README、docs/01_工程规划书.md（0.3）、docs/交付与限制.md、新增docs/04_动态索引与技能记忆设计.md及公共进度；memory子Agent仅更新docs/progress/agents/memory.md。生产代码/schema/config/依赖没有变更。
2. 关键设计：稳定人物/项目/地点/技能入口与动态主题互联，首次有来源即可暂定建入口；实体身份歧义保留pending；技能目标/材料/步骤/尝试/验证分开，不能用总结证明掌握。字段与接口是草案，不存在于当前record_kind。
3. 代码边界：人物仍为participants字符串；TF-IDF默认、BGE可选512维/512tokens截断；当前全量重建；向量行绑定revision，但缓存按内容/view/模型/空间复用。theme_materials时间取created_at。现有record_attempt_feedback只接受assistant原始消息作行动来源，技能工具执行需新契约/适配，不可伪装成聊天消息。
4. 已运行：Get-Content/rg交叉核对源码、独立子Agent审查；通过.venv/Scripts/python.exe运行文档检查脚本，4文档UTF-8/围栏通过，32本地链接0坏链，13条待验收均未勾选。没有业务逻辑变化，故未重跑pytest、模型推理或真实API；116回归与最新2次live来自之前报告，不能当本次新结果。
5. 环境/恢复：Windows PowerShell、项目.venv与依赖保持不变，无安装、密钥读取、外发或后台进程。文档直接读取即可，不需要启动worker；dist未重建，旧发行包不含本轮新增设计稿。
6. 下一步：用户可直接修改04第8节，按第7节审查目标；继续编码时先把0.3/DMI依赖同步正式任务JSON（当前仍0.2，源码锁定不变），再修DMI-00/M01/M02并针对性回归，然后主Agent锁定实体/技能/执行结果契约，分派DMI-02/03独立工作。不要从T00重做，也不要把文档草案接口当可运行API。

最新讨论：已对照官方LangGraph持久化、Letta当前SDK记忆/MemFS/Dreaming、Mem0当前README及Graphiti文档，报告reports/framework_comparison.md。不要延续“其他框架只存静态事实/没有后台反思/没有来源”的错误概括；Letta新SDK有版本化记忆仓库和后台整理，Mem0当前ADD-only路线且托管/OSS有区别。我们的差异是角色领域约束组合，完整实践反馈链仍缺日常归因，不能据116测试/15条已记录请求声称长期或性能领先。本轮只做公开资料查阅/本地只读核对，没安装/运行竞品或新增付费请求。

最新用户授权/待定产品输入：最多4个Codex子Agent（覆盖此前2个上限），默认1个，独立任务再增加，子Agent不再创建子Agent，按实际工具并发容量调度。用户当前问还有何需准备：已有技术prompt和可启动默认值，正式角色卡需其确定。已检查config/persona_template.md仅P01/P02/P03示例，其中“先迁就”不是正式用户决定；RUNNING_RULES仍硬编码ATRI，persona patch目前无不可修改条目清单（prompt约束不等于程序硬锁）。可请用户按docs/角色设定填写表.md提供来源/身份/关系/语气/固定与可变设定/对话样例；不用其手写工程prompt或重复配key。本轮只改说明/授权记录，不新增API调用或生产逻辑。

## 最新已实现：语义压缩与状态激活API

用户最新明确授权修改建议2/3。主 Agent改compaction/context/engine、App/CLI、ActivationSnapshot新增可选selection_method/limitations/generator字段、Gateway前台通道、配置及prompt/公共文档；memory子Agent复用负责activation.py和test_llm_activation.py，禁止递归委派。ActivationSelector新增gateway/llm_enabled及async aselect_active_entries，保留同步select；Compactor新增async acompact，ContextBuilder新增async abuild_context，前台/自动压缩/manual compact及/compact/context均已接通。默认context两开关true，真实调用仍需显式live+paid开关；普通Fixture会透明降级。

实际范围：语义摘要从原始raw分批，不递归旧摘要；模型要点必须给本批逐字quote，后端核验并计算SourceSpan；保留原文/preserve和模型generator信息，有效缓存复用。激活有界open候选，模型仅回ref/reason，允许选空；代码限制数量/正文预算，await后复查revision/status，trace带CAS。两个role使用foreground通道，不排后台长反思；usage仍记录业务role。旧summary独立摘要区和回忆区两条注入路径都过滤状态/人格失效，回忆投影补reality_scope等。失败/defer/预算/离线明确降级，不算模型成功。不扩大到行动反馈归因、M01/M02等其他问题。

验证：`.venv/Scripts/python.exe -m pytest -q --junitxml=reports/pytest_results.xml`→116 passed/49.64s，0失败/错误/跳过（新增36：18 activation+18 context）；首次41项集成通过。真实`.venv/Scripts/python.exe scripts/live_context_smoke.py`→2次deepseek-flash各测一个新schema，两项passed，输入1003/输出239，峰值估价USD0.0005877非账单。原13次测试独立保留，累计已记录15次。没有真实联系人发送、部署或常驻worker；无DeepSeek开发子Agent。报告存在会阻止再次调用，恢复时不要为“确认”重复付费。

环境不变/无新依赖。手动live压缩：`.venv/Scripts/myatri.exe --config config/live.local.toml --root <角色库> compact --mode live`；context --mode live有open候选会付费，普通offline不读key。语义选择12候选/6000B、情境2048B，激活4条/600B；压缩9000B批次/最多8批，超过范围降级摘录，语义摘要注入5000B并保留省略ref，暂无增量语义缓存。大显式preserve仍可能超预算；程序明确拒绝而不裁掉规则。长期质量未验证，旧评估是原基线。

发布检查：python -m build --no-isolation成功；uv pip在var/package-check/.venv reinstall wheel，C:/Windows/Temp外部工作目录验证新prompt、CLI mode、离线compaction fallback、doctor通过。reports/package_smoke.json与dist/SHA256SUMS.txt更新。最终python -X utf8 scripts/verify_secret_exclusion.py→309文件/397归档成员、0密钥匹配，覆盖新var/live-context-smoke-20261020。本轮报告reports/llm_context_upgrade.md、live_context_smoke.json；决策docs/adr/0005-llm-context.md。无遗留本轮进程。下一步可按新测试指南体验，其他审查项按component_review优先级继续；不要把两次短smoke当A6/A7或长期人格质量验收。

最新用户偏好：取消DeepSeek API开发子Agent，开发协作继续用Codex子智能体；这不影响项目本身使用DeepSeek进行真实对话。用户当前问如何测试，已新增docs/测试上手指南.md（独立目录+离线/恢复/自动化/真实体验分层）。只核对CLI与本机路径，未启动新API调用或重新跑无变化测试。不要将指南中的可选live命令当成已执行；后续开发仍按component_review待修项推进。

## 最新接续：组件解释与审查（2026-10-20）

用户最新目标是解释八模块实际工作方式，同时检查代码，并让用户确认还需修改之处。当前不是扩大付费测试。主 Agent 审查 app/runtime/providers/conversation/persona/cognition；memory 子 Agent 复用、只读审查 storage/memory/retrieval，禁止子代理继续创建代理。当前生产代码未改；新增离线诊断和组件审查文档由主 Agent 管理。已看到需验证的集成风险：主题只切前8项再过滤、后台全量输入预算、到期复审输入去重、聊天与行为反馈API未接通、上下文材料丢业务元数据。不要将这些尚待审查的路径当作已无问题。

已完成：scripts/audit_components.py临时目录7项探针均复现，reports/component_review.json保存结果；reports/component_review.md逐组件解释实际流程/边界、9项问题与建议。memory子 Agent确认2项一致性缺陷，reports/audit_memory_2026-10-20.json和tests/audit_memory_consistency.py（strict xfail）保留来源与水位观测。

实际修改仅审查脚本/诊断测试/报告及公共说明和任务状态，没有生产源、依赖、配置修改；现有dist未重建且仍含发现的问题。README、docs/交付与限制.md、reports/acceptance.md追加更正；任务清单global=implementation_present_component_audit_open，相关任务implemented_audit_open，status_before_component_audit保留原状态与历史证据。T03存储原文/CAS/恢复等保护仍有通过证据，不因后续索引缺陷误称档案丢失。

命令结果：scripts/audit_components.py→7项观察confirmed=true、paid=0；pytest test_gateway/test_context/test_persona_lifecycle/test_jobs/test_protocol_recovery→19 passed/12.14s，XML component_regression.xml；子 Agent来源/隔离/投影、跨进程CAS、3崩溃点、实际TF-IDF/Leiden与回滚→8 passed/4.15s；audit_memory_consistency→2 xfailed strict/5.88s，是未修缺陷、不能计入成功验收。普通pytest默认不收集audit_前缀文件，需显式运行；修复后应去xfail并转为正常test_回归文件。无付费调用或密钥访问，无遗留本轮进程。

下一步：本轮按用户意图先讲清组件并核对修改方向。优先M01（retrieval/service.py169历史快照用未来边）、M02（memory/index.py141旧重建覆盖新current）、A03（ContextBuilder丢reality_scope等）、A04（review_at任意字符串导致aware比较异常），再A01（主题先切8再过滤）。之后A05补日常行动/反馈有来源归因、A06增量/邻域预算选材、A02复审证据水位/空闲边沿、A07共享预算或单实例限制。不要用mock成功冒充真实语义验收；不按时间/次数把人格巩固写死。可与用户核对初始角色卡及是否锁定身份条目、行为归因自动化、到期复审规则；默认不擅自重写产品设定。完整命令/文件/优先级见component_review.md。不要无理由重跑付费smoke或访问key。

更新：2026-10-20。工作区D:/DS_workspace/MYATRI，Python3.12.7 Windows，uv。先读STATUS.md、本文件、任务JSON；规划0.2语义仍有效。当前无适用AGENTS.md，无Git仓库；全部产物已落盘。

## 1. 完成与未完成的任务

T00–T17本地实现已完成；官方Flash生成/JSON/tools/thinking协议smoke本轮实际通过。任务状态v1_live_protocol_verified_semantic_pending。T01/T04标记官方live协议已验；T16/T17短认知链恢复完成，长期语义仍pending。E01联系人投递未实现/禁用，不属于V1内部闭环。

**最新用户授权**：安全保存用户提供的key，允许官方DeepSeek-V4.1-Flash小规模付费测试。上轮“所有付费未授权”已被本次明确授权取代；联系人真实消息/外部部署仍禁止。本轮已完成13次生成，不自动扩大付费运行；真实人格A6/A7和长期人工评价仍未验证。

## 2. 实际实现/当前改动

八模块源码src/myatri/{providers,storage,memory,retrieval,persona,conversation,cognition,runtime}与app.py/CLI均贯通。原62项覆盖真实进程崩溃/CAS、来源/隔离、精确向量/Leiden、多视角/主题、临时状态/反馈/撤回/压缩/局部P03原子patch/恢复。模型与长期质量分层报告，默认offline是明确fixture演示。

本轮新增/修改：
- credentials.py：Windows Credential Manager generic target MYATRI/DeepSeek/api.deepseek.com，隐藏终端输入、按需读取，status不显示key；没有项目密钥文件，测试用fake API不碰真实存储。
- providers/gateway.py：读取env或WinCred，官方HTTPS endpoint限制、无redirect；JSON mode真实传schema到模型再本地验证；thinking低effort可配，capability_probe仅供显式测试，普通App仍需要已验开关。
- security.py、interfaces/inspect.py、.gitignore、pyproject：私密路径排除含大小写/.env/local/JSON/YAML/私钥，backup排symlink/junction，restore提取前拒绝；sdist明确公开allowlist，wheel只包含4个公开config，不强制装入整个config目录。
- cognition/temporary_state.py：完整TemporaryEntry与update schema，不再泛object；新候选只open，非法active/extra字段拒绝。prompts/temporary_state/v2.md、load_prompt版本参数与cognitive_call prompt版本、App/scheduler任务幂等版本升v2，已知同材料旧任务不伪装重试成功。
- scripts/live_smoke.py：显式合成live测试，检查点避免重复付费，20请求/USD0.10保守cap，异常费用预留、无自动重试；scripts/verify_secret_exclusion.py实际key排除只报计数，不输出key/hash。
- config/live.example.toml公开paid=false；config/live.local.toml本机ignored，只有模型/已验开关/30000日token小预算、无key；config/defaults.toml仍paid=false。hatchling加入dev以离线构建安全回归，不是运行依赖。
- 新测试credentials/secret_exclusion/temporary_schema；memory子Agent只改自身测试/进度，不接触key。公共源/配置/文档由主统筹。

## 3. 关键决策

权威Record用ID@revision和来源hash，manifest最后发布，SQLite/向量投影可重建，运行队列另备份。模型只提交Proposal；事件原文不改，解释另存；激活/反思不增加外部根。临时状态统一权威，实际assistant消息才支持尝试，无反馈unknown，撤回后可追加迟到反馈但不复活。

人格patch绑定条目旧hash/版本、外部事件根、反例检索run和确切A7审阅，原子提交persona/change/consolidated；human_edit与自然成长分开。现在真实合成材料不足以支持人格成长，模型defer合理，不能为了通过强制写人格。

真实live暴露A8状态active和多余字段：初次失败正确拦截，无无效状态提交；v2完整schema后只重放A8，其他成功API结果不重复调用，历史failed留存。不能删除失败记录声称首轮全过。JSON语法模式不等于schema自动约束，必须实际告诉模型字段。

密钥在Windows凭据管理器、项目外；不得复制进README/.env/config/tests/logs/档案/发行包。API只官方api.deepseek.com。普通项目上传不包含OS凭据；本机live配置也被排除。没有整机安全审计承诺，实际扫描只限定项目与对应归档/合成运行目录。

## 4. 已运行与结果

- GET https://api.deepseek.com/models →HTTP200，deepseek-flash/name DeepSeek-V4.1-Flash，所有生成response.model=deepseek-flash。
- `python scripts/live_smoke.py --phase basic`：真实MYATRI_OK；protocol：JSON/schema、tools、本地只读lookup_memory、thinking+tools必要reasoning_content往返均通过。
- cognition：A1/A2/A3/A5真实调用成功，A8 v1 schema不足失败；recovery：A8 v2定向任务成功，归档/来源0错误、persona@1不强制改、临时状态defer没有条目；actual_leiden_runs=0（该短输入不足以跑社区优化），真实Leiden成功证据仍在原独立算法测试，不混淆。
- 合计13次生成、13成功HTTP响应，prompt6664/completion1999，保守峰值USD0.004247472（约0.0043，非账户扣款）；运行器cap20次/USD0.10，未用满不需要继续花费。reports/live_smoke.json/md、live_models.json保留逐请求用途/usage/latency与历史失败。
- `.venv/Scripts/python.exe -m pytest -q --junitxml=reports/pytest_results.xml` → **80 passed in47.45s，0failed/errors/skipped**。其中fake sentinel安全12项真实构建临时wheel/sdist；凭据4项用fake Windows API；2项覆盖本次A8失败形状与v2生成run来源。普通pytest不读真实key、不调用API。
- `.venv/Scripts/python.exe scripts/verify_secret_exclusion.py`：实际凭据在源码/配置/文档/报告/测试/发行归档/合成运行数据中0匹配；最终发行包重建后复核，结果reports/secret_exclusion.json（不包含key或其hash）。
- uv.lock真实56项解析；dev hatchling实际安装；依赖许可54包71份notice保留。源包/独立安装和包内prompt复验按最终构建记录执行。

原本地评估36会话24开发12留出，真实TF-IDF/BGE512维/Leiden，保留图和多视角负结果；B4仅fixture结构条件，不冒充真实人格消融。结果evaluation.md/json，完整合成局部P03轨迹demo_trace.json/demo_archive.zip。

## 5. 启动/恢复/凭据

`uv sync --frozen`；可选BGE `uv sync --frozen --extra neural`。`.venv/Scripts/myatri.exe --root var/atri chat --mode offline`是演示。真实API需显式：`.venv/Scripts/myatri.exe --config config/live.local.toml --root var/atri-live chat --mode live`，这会付费且可运行后台任务，**本轮没有启动该常驻命令**。公开默认paid=false；key存在不会自动发请求。

凭据状态 `.venv/Scripts/python.exe -m myatri.credentials status`只显示configured；轮换store-deepseek隐藏输入，不把值写命令行；delete-deepseek删除本机凭据。跨机器需重新配置，key不在备份或包中。

BGE var/models/bge-small-zh-v1.5本地24MB固定rev，manifest见reports/model_manifest.json，普通运行不自动下载。memory rebuild-index --space bge显式配置，TF-IDF自包含恢复。备份backup到root外新zip，restore到不存在的新目录，doctor校验；源档records/commits不可手改，runtime.sqlite3含队列/usage/必要工具协议须单独备份。

## 6. 已知问题与进程

没有API密钥文件或值出现在仓库文档。真实API请求已结束，没有常驻付费worker/渠道消息/部署。var/live-smoke-20261020只有合成材料，保留一个v1 failed历史任务及v2成功链；不要拿该测试目录当实际用户角色库。私有配置仅本机，不打包。

仍未完成：真实A6/A7人格语义审查、长期人工连续性、真实网络故障注入与实际账单；不能从13次短smoke/有效defer推导长期人格成功。普通本地BGE否定弱点、多视角负收益、状态噪声与全图扫描规模限制仍存在，详见交付与限制。

## 7. 下一步

本轮用户“安全存key+官方Flash测试”已完成，最终保存/打包/无泄漏复核后结束，不继续无理由付费调用。用户希望实际使用时按显式live命令启动；想继续深入语义评估时另安排合成/独立样本的A6/A7与长期人工判断，先约束预算和范围。不会自动开启E01。恢复Agent必须先读最新live报告和本文件，不再把旧“0付费/未授权”当现状，也不要重复已成功付费case。

最终操作已完成：uv build+独立环境reinstall成功；在源码目录外WinCred status只显示configured，包内temporary_state/v2 prompt存在，离线doctor ok=true。实际key扫描276文件/379归档成员0匹配；本地live配置不入包，SHA256SUMS与package_smoke.json已保存。无本项目运行进程；API请求数仍13，不需要再调用。结束本轮。
