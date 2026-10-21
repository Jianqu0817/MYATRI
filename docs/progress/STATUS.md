# MYATRI STATUS

## AUDIT-REPAIR-0.2.8（2026-10-21）

按审计复核实施修复：core维护同task版本化一次恢复、失败隔离后新批继续、旧批人工重试不倒退游标且未解决隔离阻止压缩；A1非法归属候选保留checkpoint与typedreason，合格条目独立审核，覆盖明确validation_complete=false。桥接摘要持久升额、100条冻结窗分两段缓存、候选上限100/最终30项与超额隔离、4次失败停车、旧长退避一次解除；新增健康阈值、投递枚举原因/耗时、防重自然修补、鉴权Retry-Memory入口。两项目版本/锁/安装/vendor wheel一致0.2.8，角色卡未改，未重启现有服务，未提交或推送GitHub。

测试：core348项、桥290项各有通过证据（全量初跑的旧异常预期失败已定向复验，未将重复分组相加）；桥全目录和core改动Ruff、JS语法、wheel源码核对通过。真实5窗口仅fixture结构回放5→0；真实模型仅旧100窗口隔离验收，4实际调用含首遍maxItems失败，合计37,505tokens计入共享日预算，最终17摘要项/9event/9interpretation，生产档案未写。运行中0.2.7仍需正常重启Start-WeChat.cmd，8767也需重开；旧积压下一启动自动有限恢复。新失败4次暂停时用户可Retry-Memory.cmd显式重试。详情core docs/记忆链路修复_0.2.8.md与桥docs/记忆链路修复与恢复_0.2.8.md。

首遍离线回放遗留临时short.sqlite3，清理被自动审批blocked by policy拒绝，未绕过；精确路径已列桥文档与本轮交付。隔离真实验收资料留桥var/diagnostics/summary-recovery-live-1792583795，不上传。

## REVIEW-AND-GITHUB-SYNC-0.2.7（2026-10-21）

用户要求核对其他窗口改动、完善文档并同步两个仓库；另明确同意上传角色卡及其中真实群聊片段。已核对私聊卡2.0、群卡2.4和非运行备份2.0、桥主对话high/8192/120s、微信后端预检；角色卡正文未修改。README改为当前0.2.7入口并保留历史说明。完整核心340+1旧预算断言失败、桥270+3兼容/旧烟测失败；修补后摘要3项、桥34项通过，当前341/273各项均有通过证据。修复整条ack响应兼容，更新真实AstrBot合成烟测支持分段；桥全目录及核心改动Ruff通过，未改核心文件另有68项历史lint。当前额度未变。准备按授权提交/推送main，原始库/本机配置/令牌/旧本地wheel不提交；无真实模型调用、微信发送或服务重启。详情docs/本次改动核对与GitHub同步_2026-10-21.md，最终sha见Git历史与本轮结果。

## UI-CONTROLS-AND-BUBBLES-0.2.7（2026-10-21）

已完成微信专用分隔符<|msg|>语义2—3段、15字阈值、逐段确认/进度/失败unknown不重发，同一回复仍一轮；并新增8768重载角色卡/系统提示词、清空当前群工作窗口两按钮。清窗持久snapshot+旁听seq/ID边界，长期档案不删，旧协议/旧摘要不自动回流，队列生成/发送忙拒绝操作。私聊无HTTP控制，按钮禁用须重启；core支持clear_context但查看器不越过运行进程直写档案。两环境及vendor/锁/hash统一0.2.7，插件已复制。152项联合+新增排队竞态复验（153不同检查），Ruff/JS检查通过；无付费生成、微信发送、卡/README改写或GitHub上传。仅查看器重启尝试被自动审批blocked by policy拒绝，进程未变；初次需用户正常重启桥接/AstrBot及关闭旧8768后重开。详见docs/微信语义分段发送_0.2.7.md与docs/角色卡重载与清空上下文_0.2.7.md。

## LEAN-JSON-0.2.6（2026-10-21）

用户要求减少不必要JSON占用。核心compact_json/去检索渠道诊断但保留evidence_notes；桥接精简消息信封、去重复成员/主张/摘要字段与本地排序信息，保留正文/ID/时间/引用/证据，工具仅紧凑外层，分页源文本不变。两环境0.2.6/wheel/hash/冻结锁/实际安装一致。181项首次定向+补充3项证据用例后的29项复验通过（合计184不同检查），Ruff通过；100条合成消息信封字节减少50.7%，不等于全请求/真实Token效果。未触碰角色卡/README/真实记忆；未重启/付费调用/微信发送/GitHub上传。详见docs/上下文JSON精简_0.2.6.md，用户从原入口重启后生效。

## TURN-FOCUS-0.2.5（2026-10-21）

用户重点要求只接最相关话头，减少全场总结/展示记忆。核心RELEVANCE_RULES、群聊末尾独立聚焦system、信封先背景后当前字段、已有条件式审查v4同步；保留明确总结/回忆/多问题例外和已核验创作者轻微依恋。无删历史、改角色卡/README、改容量/排序或新API。两环境0.2.5和冻结wheel/锁/hash/安装一致；64项离线定向及Ruff通过，非真实语义验收。未重启/微信发送/付费调用/GitHub上传。使用与来源见docs/只接当前话头_0.2.5.md；原启动入口重启后生效，查看器需重新打开以加载新分类。

## AFFECTION-0.2.4（2026-10-21）

自然聊天为主，已确认创作者可偶尔轻微暧昧/依恋；同名/自称/机器人输出不获得该关系指引。核心/群提示/已有审查同步，角色卡未动。0.2.4安装包与锁一致，33项定向及Ruff通过；未重启、付费调用、微信发送或上传。详见QQ-agent提示词文档0.2.4补记。

## PROMPT-FOCUS-0.2.3（2026-10-21）

用户授权参考QQ-agent优化系统提示词，余额中断后已接续收尾。固定参考提交fdfd325e148d91845a0aeea3dfdff4cf92fc61a1，独立改写普通聊天、群聊焦点与并行话题、原有条件式回复审查。明确当前意图/澄清优先、可靠引用定位、同人/相邻/字面重合不能自动消歧；只说相关一点，减少全场汇总/展示记忆/强行暧昧，保持真实AI身份与事实准确。未改其他窗口角色卡/原始数据/选材算法/触发与维护频率。核心与桥接0.2.3、冻结wheel/依赖锁/安装一致；69项定向回归及Ruff通过。没有付费模型、微信发送、服务重启或GitHub推送。详情docs/QQ-agent参考与对话提示词改进_0.2.3.md；用户重启入口后生效，真实语义质量仍需试用确认。

## CONTEXT-VIEWER-0.2.2（2026-10-21）

用户要求直接看实际上下文以排查串话。已新增独立本机8768全文查看器（桥接View-Context.cmd）、最近5次主对话/审查请求的可选捕获、按trace回执和选材依据。旧30轮检查点明确标旧；本机私聊和群聊捕获已开启，但原服务未重启，新请求捕获需用户正常重启后生效。公共默认关闭；原始档案与其他窗口角色卡未修改。捕获非模型内部思考、非服务器已接收证明。测试与使用详见docs/实际上下文查看器_0.2.2.md。0.2.2核心wheel与桥接冻结锁同步，无本轮付费调用/群发送/GitHub上传。

## RICH-CONTEXT-0.2.1（2026-10-21）

用户批准十项优化（含回复长度），并授权两个子Agent并行QA。已扩大群完整往返80轮、近期100条，按成员/话题/引用选旧往返并去重；共享200k保守工作窗口；放宽核心召回/摘要/继承历史及压缩后80轮原话；丰富摘要v2、通常20—100字/兜底160字；每轮无正文context_stats及监视组成。650k压缩/1M单请求/50M日额度和原维护频率不变。核心/桥接0.2.1及冻结wheel同步。详见docs/上下文扩展与自然聊天_0.2.1.md。

核心60项关键回归、桥接完整212项及最终相关60项定向回归通过；两项窗口性能剖析复测通过，详情见更新文档验收补记。本轮未主动调用付费模型/发微信，未重启用户服务/上传GitHub。用户另一窗口正在改README/角色卡，本轮不拥有这些文件，不可覆盖或顺带提交。当前在运行的服务仍需用户重启后加载新代码。

## GITHUB-PUBLICATION（2026-10-21）

用户已明确确认上传两个项目的当前改动。发布范围为0.2.0核心/桥接升级、早期记忆读取修复及10%随机回复配置，包含现有角色卡模板但不改写其内容。密钥、真实聊天档案、冷档、本机配置和诊断仍留本机；旧阶段的“等待确认/未上传”描述保留为当时记录。

## EARLIEST-MEMORY-REPAIR（2026-10-21）

早期原文完整；两份私聊与当前群索引已在本机重建。增加明确初识/最早聊天查询的时间定位、嵌套human_import来源追溯，以及索引维护信息不等于记忆丢失的提示。检索/分页相关31项、桥接160项及Ruff通过；新核心包与实际安装、锁文件一致。随机回复本机与默认改为10%。用户需重新打开私聊及群机器人；无API调用、微信发送、角色卡改动、自动重启或GitHub发布。详见docs/最早记忆读取修复_2026-10-21.md。


## GROUP-QUALITY-0.2.0（2026-10-21，待用户验收）

核心与桥接升级0.2.0；索引基础/增量、成员候选前置筛选、显式引用来源、群聊语义支持审查、可选只读渠道工具和针对性回复审查已接入。桥接拆分收信与生成，增加话题注意力、带更正链的个人投影、用户选定的本机30天冷档。角色卡继续由用户另一程序管理，本轮不修改；不commit/push、不自动重启实时服务。完整验证与人工验收见相邻MYATRI-AstrBot/docs/群聊质量升级与人工验收_0.2.0.md；200个合成来源评测不能当回答质量或市场领先证明。

最终验证：核心283项、桥接160项回归和Ruff通过；核心源码/wheel/实际安装及两份锁文件一致。8个群库quick_check正常，96条既有消息回填复跑新增0。合成API冒烟通过且无微信发送；待用户关闭旧机器人窗口、重新运行Start-WeChat-Live.cmd后验收。

## 最新 CASUAL-MEMORY-01（2026-10-21）

主项目0.1.8、桥接0.1.2、角色卡1.3：取消书卷气、文雅措辞和文学性指标，更新两边模板及私聊persona@6、群persona@3。用户追加授权私聊记忆迁入当前群；135条消息、526个历史版本一致性备份至桥接var/imports，追加带原记录与映射来源链的历史投影，原私聊和群内43个既有版本保留。当前群P15/P16解释身份与授权范围，旧状态/心情/任务不激活，不给别群自动共享。每轮历史数据块本地限额选择，其余可检索。246项主回归、29项桥接回归、2项新增迁移检查及Ruff通过；无API调用或微信测试发送。当前长运行服务未停止，用户需重启聊天和机器人服务，微信可保持登录。详情见docs/日常口语与记忆迁移_0.1.8.md；历史记录以下方原样保留。


## 最新 WECHATAGENT-01 2026年10月21日

独立项目MYATRI-AstrBot已更新0.1.1，参考sourcepro5/WeChatAgent 0.3.9的认证读取SSE与原生发送契约，新增AstrBot平台、真实群/成员标识、回执确认及一键启动。发布包SHA256与1370个文件哈希通过，配套4.1.10.27微信腾讯签名有效；运行组件仅放新项目var，未覆盖原4.1.15.13安装。用户已亲自完成配套微信登录，读取凭据DPAPI保护，真实账号与唯一测试群绑定通过，已读到群友新发@消息。原私聊库和引擎源码未改。

29项本地检查通过；完整启动链读取端/SSE/AstrBot/离线桥接健康通过，在observe-only模式验证后停止服务，微信保持登录。没有真实模型调用或发送群消息，因此真实回复/服务器回执仍待验证。原有通用桥接“无平台”状态已被本节取代，E01自主社交仍未实现。新入口Open-WeChat、Setup-WeChat、Start-WeChat、Start-WeChat-Live；说明在独立项目docs/WeChatAgent接入.md。群昵称/群ID/账号/凭据不提交Git。

## 最新 ASTRBOT-BRIDGE-01 2026年10月21日

用户明确要求可行则新拉项目，并补旧修改文档。已在D:/DS_workspace/MYATRI-AstrBot创建独立Git项目，分支codex/astrbot-bridge，实际克隆AstrBot4.29.1 commit f2404c191716a64daaa422be7f3c567cace50d39；保持上游源码不改，用独立插件和本机HTTP后端桥接。MYATRI0.1.7冻结wheel进入vendor并锁哈希，未复制用户运行库/凭据；依赖与虚拟环境独立。原仓库本轮只补README、docs和进度。

新桥接按平台实例/机器人/群隔离，入站JSON信封带成员ID/昵称/原时间/原文。群成员共享本群上下文，私聊及跨群记忆隔离；群身份认证依赖渠道稳定ID，不靠昵称映射为创造者。复用30/50/150/300频率、40—80正文、1M/650k；所有桥接群共享50M账本，原私聊另计。插件命中白名单先stop_event，避免内置LLM再调用。原子领取投递、未知结果不重发；sent只表示适配器send返回，不证明已读。

新项目默认offline、空白名单、插件关闭。已装两套独立依赖，14项检查通过（含实际AstrBot事件/插件API到MYATRI的本地捕获发送联调），真实后端进程启动及鉴权健康检查通过；3页Word记录已渲染并逐页检查。证据见新项目docs/validation.xml与verification.json；未登录微信/真实API/真实消息。本机微信只读检测为Weixin4.1.15.13，适配器仍需兼容性实测。群聊适配器尚需按微信版本和稳定成员/消息ID选择，官方个人微信接口不能直接当微信群接通。E01自主社交闭环仍未实现，勿改原outreach开关冒充接通。

旧修改集中写入docs/项目修改记录与当前配置_2026-10-21.md，并复制到新项目docs/MYATRI既有修改记录.md；另有Word版。下一步按用户提供微信版本和测试群配置连接，不重新迁移ATRI，不覆盖现有persona@5或私聊记录。

## 最新 CHAT-PRESENTATION-01（2026-10-21，0.1.7）

用户要求日常40—80字、减少追问/征求意见/邮件式周全表达、终端清楚区分双方。角色模板1.2改P00身份/来源、P07、P10、P12五项，保留原1.0 source和1.1补充原文；四个短聊天示例替换当前活跃示例。ReplyPolicy通过末尾system约束40—80字，非空白字符计数、标点计入；80字本地硬上限，优先完整句/分句，必要时省略号；不足40字不填充、不另调用模型。只处理最终非工具回复，工具JSON及结果不截断；已显示/入档/完整协议一致，provider实际usage不改。识别并移除前导ISO消息时间元数据，正文引用时间保留。512前台max_tokens，后台/650k压缩/30诊断/50维护/50M日额不变。

CLI纯文本块分开[你]/[小温暖]/[系统]，用户输入后显示发送时间，助手头显示生成记录时间；不依赖ANSI。单条--message仍JSON协议。现有库先在线锁内备份var/backups/xiaowennuan-before-chat-1.2-20261021-015310.zip，再human_replace为persona@5；105条原话和全部490个既有revision未改，其他条目、P14与inherited_snapshot保持。使用统一writer/CAS，不终止正在进行的聊天。doctor通过、本地索引更新；私有报告var/diagnostics/chat_presentation_2026-10-21.json。代码需用户/quit重启；不要重新迁移记忆。0真实API、0凭据读取。定向29项已通过，完整回归与发行检查见同日chat_presentation报告。

## STYLE-CADENCE-02：角色卡1.1与30/50、50M配置（2026-10-21，0.1.6）

按用户提供的明确补充，更新小温暖P00身份锚点/来源、P03性格、P06表达说明、P07语言、P10十二个示例、P12最终锚点，共7项。轻柔、灵动、文雅，亲近时含蓄狡黠、羞涩与主动交织，减少模板化客服/系统解释；成年男性/独立判断/真实能力边界与继承记忆保留。原1.0 source.md未改，新增style_update_2026-10-21.md保存用户补充，五项表达数值沿用65/10/50/35/45。

现有var/xiaowennuan先备份var/backups/xiaowennuan-before-style-1.1-20261021-011849.zip，再人工发布persona@4。所有旧revision和83条原话不变，P14/inherited_snapshot保留，其他9项条目未改；新版语气同时进入首尾系统区域，索引/doctor通过。私有报告var/diagnostics/style_1.1_cadence_budget_2026-10-21.json。

3份配置统一：trace_every_turns30、maintenance_turns50、projection_every_commits60、deep_every_batches3（约150轮）、persona_every_batches6（约300轮）、daily_tokens50000000。上下文1M/压缩650k/即时原话/5秒轮询不变，用户重启加载新配置。5项角色/继承定向及12项假凭据打包检查通过，12例均进入模板，报告reports/style_1.1_{targeted_2026-10-21.xml,packaging_2026-10-21.xml,config_check_2026-10-21.json}。本轮0真实API/凭据读取，未执行后台认知。版本/uv.lock已同步0.1.6；wheel/sdist已构建并核对新版角色文件、30/50与50M配置、私有路径排除，SHA256SUMS-0.1.6.txt已生成。

## RUNTIME-OPT-01：运行降频、缓存与消息时间（2026-10-21，0.1.5，完成）

按用户授权选择X=10做完整诊断及约10轮投影检查点；原话仍每条即时提交。记忆/事件情绪/临时状态30轮，反思/关联/主题/归因每3批约90轮，人格审阅每6批约180轮；不足条件defer。延后材料持久累积、结束批次时与cursor原子更新；即使无新原话，压缩前也补齐积压深度审阅。普通批次只在末尾更新索引；后台空队列每5秒轮询。config/defaults、live.example、本机live.local已同步，窗口需重启。

ArchiveStore缓存已校验文件和最多4个快照，以文件属性变化失效、返回深拷贝防嵌套污染，doctor强制重新哈希；投影按约20次提交批量增量追加，正常退出/维护/doctor刷新，崩溃后从原档恢复。完整协议按10轮留检查点，其余完成轮只存简要状态；未完成工具协议与预算记账仍即时。每条上下文历史消息带发送时间（Asia/Shanghai），本轮提供服务器时间；记忆/反思材料、压缩窗口和新摘录也带原记录UTC时间，原文不加前缀以维持逐字来源跨度。

237项完整离线回归通过（151.05s，runtime_optimization_regression_2026-10-21.xml），43项时间材料定向通过、12项假凭据打包排除通过。新增6项缓存隔离/跨实例可见性/篡改/投影恢复/诊断降频/分层维护积压与时间测试；进程死亡投影测试改接新增量发布路径。固定快照三次本地中位：上下文5.0716→0.6679秒，原话提交0.8915→0.3625秒；不是API性能保证。0.1.5 wheel/sdist及源码外独立安装10轮离线smoke通过，消息重启/角色锚点/时间/新配置/doctor通过。版本与uv.lock同步。

详见docs/运行开销优化_0.1.5.md，报告reports/runtime_optimization_{benchmark,package}_2026-10-21.json。本轮0模型API/真实凭据读取、未改用户档案或停止现有聊天；只改本机运行配置，测试对话仅存在忽略的隔离副本。未实现流式输出、身份硬锁；真实650k压缩与长周期语义仍未验证，既有遗忘/检索问题不因此关闭。后续不要重跑付费smoke，用户重启加载即可。

## IDENTITY-01：继承记忆后的身份上下文修复（2026-10-21，真实核对通过）

用户反馈仍是ATRI；实际检查发现并非读错库：小温暖库67条消息、persona@2及已发送协议确含新卡，但模型自称ATRI、否认知道小温暖。根因证据是61条继承原话仍用user/assistant消息直接续接，旧助手身份强烈干扰当前自述；此前只验证卡存在不足以验证语义效果。ContextBuilder现将继承边界内原话投影成带ref/时间/原角色的历史数据，原档不改；新P00_current_identity在上下文首尾明确当前身份，要求纠正历史中的错误自述。PersonaPatcher新增人工完整换卡方法，人工及经验更新均保留继承边界元数据。

已备份var/backups/xiaowennuan-before-identity-fix-20261021-004236.zip，再将现有卡新增身份锚点为persona@3（16条目，模板15条加继承说明）。67条原话和所有既有revision均未变，本地索引已更新、doctor通过。16项定向离线测试通过，证据reports/identity_context_fix_2026-10-21.xml。1次官方deepseek-flash真实诊断返回“我叫小温暖。ATRI 的那段历史记忆我保留着”，prompt16134/completion54/total16188；不启用tools/retry/后台任务，不写入用户聊天历史，只记录用量与私有诊断var/diagnostics/identity_context_fix_2026-10-21.json。仍不等于长期身份语义验收。用户关闭旧窗口、重开启动小温暖.cmd加载修复；不要再重迁移记忆或额外付费复测。

## LAUNCHER-02：Windows CMD 兼容修复（2026-10-21）

用户报告启动时hell.exe无法识别，位于Python之前的命令入口；原有文件静态字节检查与隔离复现未稳定重现原错误。已将两个CMD改为纯ASCII/CRLF、显式SystemRoot下Windows PowerShell路径，移除CMD内中文与代码页切换；中文显示名由ASCII PowerShell的Character xiaowennuan预设生成，内部atri域/已继承库保持不变。gitattributes新增CMD强制CRLF。实际完整启动小温暖.cmd -CheckOnly已通过环境同步/凭据状态/库完整性检查，未调用模型或改写人格/原话。隔离模拟外部调用，在936/65001初始代码页、中文空格路径上两个入口四组参数检查均通过；证据reports/launcher_encoding_fix_2026-10-21.json。不能据此断言已精确复现原始CMD截断机制。

## MEMORY-INHERIT-01：ATRI 记忆继承（2026-10-21，已实际迁移）

用户明确要求将 ATRI 记忆转移给小温暖，以兑现保留记忆的承诺。目标库尚不存在；已先锁定两库、备份原库到var/backups/ATRI-before-inheritance-20261021-003032.zip，再完整恢复到var/xiaowennuan，并原子发布persona@2载入小温暖卡及P14_memory_continuity来源说明。原库/全部413个历史revision字节内容与引用均保留：61raw_message、21event、19emotion_appraisal、19temporary_state、8summary等；队列/协议/用量亦随SQLite备份继承。迁移脚本scripts/inherit_atri_memory.py拒绝覆盖既有目标；合成回归通过，证明旧人格版本/原话/运行元数据/记忆检索保留且源档不变。

内部agent ID继续使用atri，避免重写档案身份与历史snapshot；小温暖CMD已改为Agent atri、显示名仍小温暖。README和角色说明同步，以此节优先于下方“独立新agent/不迁移”的历史记录。实际迁移doctor与SQLite完整性检查通过、本地TF-IDF已重建至当前水位；报告var/xiaowennuan/memory_inheritance.json。没有API调用/真实凭据读取/执行旧付费任务。后续请用小温暖入口，新旧库不会自动同步。未声称修复既有遗忘/召回问题。

## CHARACTER-01：小温暖角色卡导入（2026-10-21）

用户提供1.0完整角色卡，已逐字节保存至config/personas/xiaowennuan/source.md；可加载persona.md完整保留十三部分并分成稳定条目，补P00来源/背景与真实经历边界，共14项。新增启动小温暖.cmd，使用独立var/xiaowennuan、agent xiaowennuan、本机live配置及凭据；第一次启动才初始化，不覆盖ATRI库或迁移旧对话。启动器新增agent/persona-file/display-name透传；系统规则改为遵循持久化人格身份，CLI显示名可配置。未新增身份硬锁或五套记忆存储。

11项定向离线检查通过（reports/character_import_2026-10-21.xml）；原文与附件字节一致，十三部分完整性、PowerShell语法及wheel内角色文件字节一致检查通过（同名json）。仅在reports/character_package_tmp_20261021构建验证wheel，未覆盖dist既有0.1.4发行包。没有真实API/凭据读取/用户运行库改动；未自动启动新角色，用户双击启动即可。使用与后续版本化修改说明见config/personas/xiaowennuan/README.md。

## CADENCE-01：按轮次维护与长上下文（2026-10-21，0.1.4，离线验证完成）

用户要求少调用模型、约650k再压缩、压缩前完成依赖工作；反思/情绪可约20轮运行一次。已接20个成功对话轮次的持久批处理（原话始终即时落盘），合并A1抽取与情绪评价，再做反思/临时状态/归因/人格审阅和索引；压缩前强制等待同一路径。live配置上下文上限1M、软阈值650k、日额度仍1M；每轮临时状态激活使用本地启发式，不再额外请求LLM。API usage锚定上下文估计，新增/改变块保守按UTF-8上界；不是精确tokenizer。旧逐消息任务在批处理策略下取消并保留原始数据/结果，由批处理接续；不再按空闲/夜间/周期触发新认知。

最终验证：完整227项通过（200.93s，cadence_regression_2026-10-21.xml），最后小改后的16项定向通过（60.20s，cadence_targeted_2026-10-21.xml）。包含9项新增轮数/压缩前依赖顺序/阶段失败重启去重/伪造来源拒绝等测试。0.1.4 wheel/sdist已构建，wheel离线安装独立target并从源码目录外启动，原话/维护/压缩/doctor/配置均通过，见reports/cadence_package_smoke_2026-10-21.json。源码包和wheel包含新维护模块与公共配置。未停止现有用户进程、未修改角色运行库、未新读密钥或调用真实API；由用户重启加载。说明见docs/调用节奏与压缩策略.md。尚未修复上一轮诊断的临时信息停止召回、所有自然问法检索排序等问题，不得将降频视为这些缺口已解决；650k真实长上下文与新batch prompt真实语义尚未验证。

2026-10-20 启动预算补记：按用户要求，本机config/live.local.toml与公开live模板的daily_tokens已改为1000000；一键启动器不再将模板额度改回30000。重启生效，保留已记录用量，不启动新API调用。

## Windows 一键启动（2026-10-20）

用户要求简化启动，并提供本机密钥用于配置。已通过内存标准输入保存并回读验证 Windows 凭据；未将密钥写入文件或命令行参数。新增根目录启动MYATRI.cmd、scripts/start_myatri.ps1 和 scripts/start_myatri.py；uv frozen同步（含neural）、固定var/myatri-main、初始模板/已有角色保留、doctor阻断、重复启动锁、live聊天与原有后台任务。默认不自动开始聊天，用户双击入口才启动付费模式。

本机完整启动自检通过；独立合成目录验证实际CMD/PowerShell入口、中文及空格路径、重复启动拦截、重启保留记录、持锁时备份成功。锁文件放在角色库外，避免影响备份。补齐Python stderr UTF-8输出。README已更新，源码打包清单已加入CMD入口（本轮未重建发行包）。没有新增模型API调用、没有常驻进程；本机角色库只做初始化/完整性自检，未灌入测试对话。当前虚拟环境版本0.1.3。

## EMO-01：情绪连续性模块（2026-10-20，0.1.3，离线工程验证完成）

最终结果：完整218项通过（154.85s，0失败/错误/跳过）；上下文硬预算兜底后26项定向复测通过（9.81s）。reports/emotion_regression.xml、emotion_targeted.xml、emotion_upstream_parity.json及emotion_package_smoke.json记录证据。0.1.3 wheel/sdist构建成功；wheel实际离线安装至源码外临时target，评价/重启/上下文/撤回/doctor与CLI正常，完整MIT许可哈希一致。本轮0次真实API/凭据读取/用户运行库修改，无常驻进程；真实语义和长期表现仍pending。以下过程检查点保留历史，当前以本补记和根目录情绪模块开发.md为准。

用户明确要求GitHub现成代码复用并开发，单独记录《情绪模块开发.md》。主Agent独立完成，无本轮子Agent。主要改编MIT gianlucamazza/emotional-memory的MoodField.regress/update和CoreAffect.lerp/distance，固定8b84bf3725448f2545337c08e346434819c01628；原始许可/源码哈希/改动加入LICENSES/upstream/manifest.json。对照读emotion-engine的衰减与词面appraisal，未复制；affect-kernel克隆失败，未当作已审源码。

新增contracts/cognition/persona emotion模块、emotion/v1 prompt；新Event后台任务、不可变逐字来源评价、PAD/慢心境只读回放、emotional_echo、前台有界注入、人工撤回与CLI已接。默认心境重排关闭，不改变普通recall/人格反证检索。无定时模型调用/人格自动升级/外发；默认离线defer。旧库不自动批量回填。开发方案在项目根目录情绪模块开发.md。

已有证据：上游250组/1000次数值对照通过，最大误差2.22e-16；初轮201项非打包回归通过。新增26项最终情绪用例与包含发行许可的完整回归正在跑；最后一次新增恢复测试修正为队列支持的retry_wait。0.1.3首次wheel/sdist构建成功，最终包smoke待跑。0次新真实API/密钥读取/真实用户运行库修改。最终结果完成后在此补记，不将当前检查点误读为完整验收。

## REUSE-01：A-MEM / Letta 等价局部改编（2026-10-20，0.1.2）

用户已授权源码复读和等价功能复用。已读取 A-MEM 三个核心文件/测试、Letta 当前 TypeScript 与 archive Python 相关实现；仅移植 A-MEM 小型关联去重内核、Letta Code 原子快照写入内核，实际接入图回忆和档案/索引发布。领域原文、版本、类型边、统一提交与预算契约保留。固定来源、许可、改动及未采用理由见 reports/upstream_reuse_2026-10-20.md 与 LICENSES/upstream/manifest.json。

A-MEM定向35项、Letta定向38项通过；192项完整回归通过（140.56s），实际wheel在源码目录外离线init/chat/compact/doctor通过，源码包/wheel许可哈希和敏感/临时路径排除检查通过。无新模型API/真实凭据读取/用户运行数据改动。两完整框架未安装/运行，不能宣传整套记忆系统复用或语义提升。下文FIX-PERSIST-01仍为有效修复基线，旧“未复制任何代码”仅指初次实现时点。

## FIX-PERSIST-01：持续运行修复已完成本地验证（2026-10-20，0.1.1）

用户授权修复最新代码审查，并强调角色自然与持久化。余额中断后已接续并完成：重复增量压缩/摘要注意，快照与单调索引发布/历史证据，有限认知选材/A1窗口checkpoint，调度/时间隔离，跨实例日额度，以及日常表达/迟到反馈归因和原子重放。178项完整回归通过（138.97s）；最后归因时间防护16项定向复测与打包排除12项专项通过。0.1.1 wheel/sdist已构建，实际wheel在源码目录外普通聊天/压缩/doctor成功。详细证据与限制见reports/persistence_fixes_2026-10-20.md；设计见ADR0006。

M01/M02/CTX-01/R-MEM-03/R-MEM-04/R01/PERSONA-01与A01/A02/A04/A05/A06/A07已本地修复，A03前次修复继续保留；任务JSON已同步规划0.3与修复状态。下文同日旧检查点保留历史，不代表这些问题仍未修。当前pending为新归因真实模型质量、长期角色连续性、实体/技能/工具学习、BGE长文分块及规模优化。没有新付费API/凭据读取或真实用户数据修改，没有常驻服务。合成临时测试目录保留在reports且已排除打包。

文件分工：主app/runtime/公共契约/persona临时API/attribution/文档；memory子代理memory/retrieval与索引回归，cognition子代理材料/A1/A2/A3/A5/A6/A7/A8；budget子代理Gateway/JobQueue。原context子代理的33项定向证据已保留，新增摘要注意投影检查独立处理。

## DOC-MEM-04：动态索引与技能记忆文档同步（已完成文档检查，2026-10-20）

用户要求按当前讨论更新既有MD，便于后续修改与检查。主Agent已更新README、docs/01_工程规划书.md（0.3）、docs/交付与限制.md，并新增docs/04_动态索引与技能记忆设计.md（165行，含现状矩阵、实体/技能字段与流程草案、Embedding实现、DMI-00–05依赖、13项未执行验收及用户修改表）。memory子Agent只读核对源码/新文档，只更新agents/memory.md。其4项建议已修：旧“仅规划/从T00”措辞、主题时间实际取created_at、技能工具结果不能直接复用现有assistant行动来源、向量行revision与内容缓存键分开。另修正规划的实际文件布局、多视角/全量重建边界与开发协作授权。

验证：通过.venv/Scripts/python.exe执行只读文档脚本，4份产品文档UTF-8/代码围栏通过，32个本地链接存在、0坏链；13项拟议验收全部未勾选。源码参数交叉核对TF-IDF char1–4、BGE512维/512tokens、k5/threshold0.08、视角0.7/0.3及Leidenseed17/resolutions0.5/1.25。没有重跑业务pytest或算法/API测试；116回归与2次新增短live仅引用既有证据。本轮无生产契约/配置/依赖改动，无新依赖、密钥读取、API调用或常驻进程，未重建dist。

完成只指文档同步，不指新功能实现：稳定Entity/Skill/Procedure、消歧、执行结果适配、长文分块均待实现，M01/M02/A05仍开放。任务JSON与来源锁定保持原0.2排程；实际编码前先同步plan_version与DMI正式任务，不把新编号算作T00–T17已完成项。下一步可按04第8节检查/修改需求；若继续编码，先DMI-00一致性修复与针对性回归，再锁定公共契约。

框架比较补记（2026-10-20）：按用户问题查阅官方LangGraph/Letta当前SDK/Mem0/Graphiti资料，复用memory子Agent只读核对本地证据，新增reports/framework_comparison.md。定位为可追溯角色演化的定制原型；不主张持久化/来源/后台反思独创或跑分领先。M01/M02/A05和规模/长期语义不足仍开放。未改生产、安装外部框架或新增模型API调用。

最新协作授权（2026-10-20）：用户允许最多4个Codex子Agent，替代此前最多2个的上限；默认仍用1个，有独立文件归属和任务时再增加，实际受可用并发约束，子Agent不递归委派。当前用户核对上线试用所需角色卡/提示词；已有技术prompt，无需用户手写整套。初始角色卡仍为3条示例，固定身份条目尚无程序硬锁，运行规则仍写ATRI；正式角色设定确认后再据此配置/补齐。详见docs/角色设定填写表.md。本轮仅核对与说明，没有新API调用或生产逻辑修改。

## 当前结果：T11-LLM-COMPACT / T12-LLM-ACT（已完成本地与短live验证）

用户已明确要求上条建议2/3改用LLM API：会话语义压缩、临时状态语义激活。本轮主 Agent拥有conversation/{compaction,context,engine}.py、app.py、CLI、公共契约/配置/prompt、Gateway通道、集成测试与公共文档；复用memory子Agent仅改persona/activation.py、tests/test_llm_activation.py及自身progress。保持现有同步接口用于兼容/离线检查，生产异步路径接现有Gateway；无候选不调用、模型出错/defer/离线明确降级，不伪称真实语义成功。无关的已知审查问题仍开放。已在既有官方测试授权下完成必要的2次新schema合成验证，没有启动DeepSeek开发子Agent。

最终证据：两个异步入口已接前台、自动/手动压缩与context；新增版本prompt、配置开关、来源引文校验与状态CAS，修补失效summary从回忆区再注入的旁路。首次集成41 passed，全套116 passed（49.64s，0失败/错误/跳过，pytest_results.xml）。scripts/live_context_smoke.py实际官方请求2次，两项passed，prompt1003/completion239，峰值估价USD0.0005877（非账单）；无重试、cap2/USD0.03，报告存在不重跑。旧13次报告独立保留，累计有记录15次，不代表账号全部请求。

包已重建并reinstall独立环境，在源码目录外验证两个新prompt、CLI mode、离线fallback与doctor通过，包未含live.local配置，见reports/package_smoke.json与dist/SHA256SUMS.txt。新增reports/llm_context_upgrade.md及live_context_smoke.json、ADR0005与手册已更新。最终实际密钥排除扫描309个文件/397归档成员，0匹配，包含新合成live目录；未将key写文件。当前无常驻worker/未结束操作，语义长期质量与其他audit findings仍待处理。

测试入口补记（2026-10-20）：用户决定继续使用Codex子智能体，取消DeepSeek开发子Agent方案。未实现或启动该方案。新增docs/测试上手指南.md，按实际CLI提供独立离线库、来源检查、压缩/进程恢复、备份/恢复、正常pytest与已知xfail、合成demo及可选live步骤；已核对本机venv/CLI/local配置/BGE目录存在，未启动测试或新增API请求。生产逻辑、已知缺陷和验收开放状态不变。

## 当前接续：组件讲解与审查（2026-10-20）

用户要求按实际组件详细解释并检查代码、确认待修改项。主 Agent 审查网关/上下文/人格/认知/调度及集成；复用 memory 子 Agent，只读审查存储/索引/检索。审查已完成，未改生产逻辑、不新增付费调用。此前80项通过是已有基线，本轮27项正常定向检查通过；7项离线观察复现，2个strict xfail确认未修一致性缺陷。完整验收重新开放；本节和最新审查报告优先于下文旧的“完成”措辞。

本轮产物：scripts/audit_components.py、reports/component_review.md/json、reports/component_regression.xml；子 Agent产物tests/audit_memory_consistency.py、reports/audit_memory_2026-10-20.json及自身progress。README/交付限制/验收报告/任务JSON均追加更正，历史测试证据保留。归属无重叠。

待修：M01历史图快照、M02索引发布倒退；A01主题待办饥饿、A02到期复审键/持续空闲、A03上下文丢业务元数据、A04无时区时间退出后台、A05日常行为反馈归因未接通、A06全量材料预算溢出、A07多实例不共享日额度。详见component_review.md对应源码与复现。本轮无遗留运行进程；下一步与用户核对角色卡/身份条目保护、行动归因和复审策略，然后按报告顺序修复并针对性验证；密钥无须读取，现有包仍含待修问题。

更新：2026-10-20（Asia/Shanghai），版本0.1.0。当前主Agent统筹，复用memory子Agent做安全/打包独立验证，没有新增用户聊天。

## 当前结果

- V1本地八模块与真实本地BGE/Leiden已交付；本轮新增Windows Credential Manager、官方host限制、JSON schema真实提示、A8 v2完整契约与安全排除。
- **80 passed，0 failed/errors/skipped（47.45s）**；62项原测试继续通过，新增凭据/打包/备份/真实A8失败形状回归。
- 官方GET/models HTTP200：deepseek-flash / DeepSeek-V4.1-Flash。基础生成、JSON schema、tools完整往返、thinking+tools均实测通过。
- 13次生成、13成功HTTP响应；prompt6664 / completion1999，保守峰值估价USD0.004247472（非账户实际扣款）。上限20次/USD0.10；没有自动重试已尝试付费case。
- 真实认知链A8初测因active非法状态失败一次并被正确拒绝；完整schema与prompt v2修复后，仅受影响任务重放通过。历史failed保留，新任务成功；模型可defer，没有伪造临时状态或人格成长。

## 密钥与文件归属

密钥已通过隐藏输入存Windows Credential Manager，回验成功；无项目密钥文件。默认offline不读key，只有显式live访问官方HTTPS API。config/live.local.toml仅存开关/模型/小预算、不含key且Git/backup/wheel/sdist排除。实际key排除扫描0匹配，见reports/secret_exclusion.json。普通项目上传不包含Windows凭据。

主Agent：credentials/security/providers、公共schema/prompt/config/依赖、真实API测试、文档/集成。memory Agent：tests/test_secret_exclusion.py与自身进度；12项fake sentinel覆盖大小写/YAML/私钥/备份恢复/真实wheel+sdist构建，通过；未读取真实凭据或调用API。

## 任务与剩余验证

T00–T17本地完成；T01/T04追加官方协议smoke已验。T16/T17更新为协议验证完成、短认知恢复完成、长期语义pending。E01未实现且禁用，联系人真实发送/部署未授权且未执行。

未验：A6/A7真实人格判断、长期人工角色连续性、真实网络故障/账单扣费。不能把13次短smoke当作长期质量或完整人格语义验收。当前授权的小规模测试已完成；无常驻付费worker或部署。最终包及记录重建后结束本轮。

文档：reports/live_smoke.json/md、live_models.json、secret_exclusion.json、pytest_results.xml；docs/运行与恢复手册.md、docs/progress/HANDOFF.md。默认配置仍paid=false，实际live使用本机私有配置且须--mode live。

最终检查点：发行wheel/sdist已重建，独立环境安装包内v2 prompt与凭据status/离线doctor通过；实际密钥扫描276个文件和379个归档成员，0匹配。本机live.local配置未入包，dist/SHA256SUMS.txt与reports/package_smoke.json已更新。生成请求最终固定13，没有遗留本项目Python/uv进程或常驻付费worker。本轮要求已完成。
