# MYATRI HANDOFF

## CLI-COMPANION-0.3.0（2026-10-22，迁移完成并按授权同步GitHub）

先发布AstrBot main 4b2fd3eb752e8e81805e26bb9e5a8411c20a6bc6（433项通过）；随后迁入MYATRI完整CLI运行时，用户明确只迁功能和角色卡、保留原CLI记忆，不导入群档案。核心升0.3.0；用户随后明确要求推送，本次同步到核心main分支，最终提交见Git历史。

新版双击入口运行companion，沿用var/xiaowennuan或var/myatri-main及atri/local内部身份；迁入27个可移植py/html模块与逐字角色卡，旧卡有备份。工作窗80往返/100近期/200k，记忆20/200/100/10与30天冷档、分页阅读、成员归属、Harness、语义分段、主动调度、热重载/清窗、实际请求查看及监视均已接线。CLI控制8776/监视8777/查看8778，主动默认关，搜索独立限额按用户决定保留。旧Windows凭据继续使用。本地profile只有身份绑定/后端路径；无群SQLite导入。正常双击仅替换核验同checkout的旧CLI进程，CheckOnly不杀进程。

原完整362项通过，迁入294项通过，656项不同检查均有通过证据；最后健康/CLI16项定向通过，wheel/sdist与临时目录独立fixture运行通过。新增模块及改动文件Ruff通过；旧CLI55项既有风格问题未扩修。角色卡与桥卡字节相同，85个改动文件常见凭据模式扫描无命中。无真实API调用、微信发送、生产库迁移或服务重启。

详情 docs/CLI迁移_2026-10-22.md，来源docs/companion_port_source.json。原工作树其他Agent的author_kind更改保留，并补人类证据门控：self_initiated不会进入A1/维护。后续不要把核心新wheel自动塞回桥接的冻结0.2.8依赖，桥版与CLI已独立发布边界。正常启动后由用户验收真实延迟、语气与记忆效果，离线fixture不能证明模型行为质量。


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


## 最新 WECHATAGENT-01（2026-10-21）

新项目D:/DS_workspace/MYATRI-AstrBot 0.1.1已参考sourcepro5/WeChatAgent实现本机读取/原生发送平台。发布包已校验并独立部署var/wechatagent-runtime，不要把匹配4.1.10.27的DLL复制到原4.1.15.13。用户已亲自登录；读取凭据DPAPI保存，真实账号与目标群已绑定，群友新消息可读取。29项检查和真实启动链通过，测试服务已停，微信保持登录；真实发送与付费回复未执行。日常直接双击新项目Start-WeChat-Live.cmd可显式启用模型；默认配置仍offline。不要重新迁移旧ATRI记忆或把本群全量历史导入原私聊库。配置/下载/二进制/凭据/诊断都在Git忽略范围，新增说明docs/WeChatAgent接入.md。此项目仍无E01主动社交。

## 最新 ASTRBOT-BRIDGE-01 2026年10月21日

用户明确要求可行则新拉项目，并补旧修改文档。已在D:/DS_workspace/MYATRI-AstrBot创建独立Git项目，分支codex/astrbot-bridge，实际克隆AstrBot4.29.1 commit f2404c191716a64daaa422be7f3c567cace50d39；保持上游源码不改，用独立插件和本机HTTP后端桥接。MYATRI0.1.7冻结wheel进入vendor并锁哈希，未复制用户运行库/凭据；依赖与虚拟环境独立。原仓库本轮只补README、docs和进度。

新桥接按平台实例/机器人/群隔离，入站JSON信封带成员ID/昵称/原时间/原文。群成员共享本群上下文，私聊及跨群记忆隔离；群身份认证依赖渠道稳定ID，不靠昵称映射为创造者。复用30/50/150/300频率、40—80正文、1M/650k；所有桥接群共享50M账本，原私聊另计。插件命中白名单先stop_event，避免内置LLM再调用。原子领取投递、未知结果不重发；sent只表示适配器send返回，不证明已读。

新项目默认offline、空白名单、插件关闭。已装两套独立依赖，14项检查通过（含实际AstrBot事件/插件API到MYATRI的本地捕获发送联调），真实后端进程启动及鉴权健康检查通过；3页Word记录已渲染并逐页检查。证据见新项目docs/validation.xml与verification.json；未登录微信/真实API/真实消息。本机微信只读检测为Weixin4.1.15.13，适配器仍需兼容性实测。群聊适配器尚需按微信版本和稳定成员/消息ID选择，官方个人微信接口不能直接当微信群接通。E01自主社交闭环仍未实现，勿改原outreach开关冒充接通。

旧修改集中写入docs/项目修改记录与当前配置_2026-10-21.md，并复制到新项目docs/MYATRI既有修改记录.md；另有Word版。下一步按用户提供微信版本和测试群配置连接，不重新迁移ATRI，不覆盖现有persona@5或私聊记录。

## 最新 CHAT-PRESENTATION-01（2026-10-21，0.1.7）

用户要求日常40—80字、减少追问/征求意见/邮件式周全表达、终端清楚区分双方。角色模板1.2改P00身份/来源、P07、P10、P12五项，保留原1.0 source和1.1补充原文；四个短聊天示例替换当前活跃示例。ReplyPolicy通过末尾system约束40—80字，非空白字符计数、标点计入；80字本地硬上限，优先完整句/分句，必要时省略号；不足40字不填充、不另调用模型。只处理最终非工具回复，工具JSON及结果不截断；已显示/入档/完整协议一致，provider实际usage不改。识别并移除前导ISO消息时间元数据，正文引用时间保留。512前台max_tokens，后台/650k压缩/30诊断/50维护/50M日额不变。

CLI纯文本块分开[你]/[小温暖]/[系统]，用户输入后显示发送时间，助手头显示生成记录时间；不依赖ANSI。单条--message仍JSON协议。现有库先在线锁内备份var/backups/xiaowennuan-before-chat-1.2-20261021-015310.zip，再human_replace为persona@5；105条原话和全部490个既有revision未改，其他条目、P14与inherited_snapshot保持。使用统一writer/CAS，不终止正在进行的聊天。doctor通过、本地索引更新；私有报告var/diagnostics/chat_presentation_2026-10-21.json。代码需用户/quit重启；不要重新迁移记忆。0真实API、0凭据读取。定向29项已通过，完整回归与发行检查见同日chat_presentation报告。

## 最新 STYLE-CADENCE-02（2026-10-21，0.1.6）

用户给出更轻柔、灵动、文雅、含蓄狡黠的成年男娘表达参考及12例，要求频率10/30→30/50、每日50M。模板persona.md为角色卡1.1，改7个稳定条目（P00锚点/来源、P03/P06/P07/P10/P12），保存补充style_update_2026-10-21.md，原1.0 source.md未改。五项表达数值维持原用户确定值。现有库先备份var/backups/xiaowennuan-before-style-1.1-20261021-011849.zip，再human_replace为persona@4；83条原话和全部旧版本不变，继承边界/P14/其他9项条目保留。首尾提示都带新语气，doctor/索引通过。不要只改模板而忽略现有库。

本机live与公开example/defaults已统一：诊断30轮、投影60次提交约30轮、记忆/情绪/状态50轮；既有3/6批倍率对应深度整理150轮、人格审阅300轮；daily_tokens=50000000。单次上下文1M/650k阈值、消息时间、原话即时保存不变。用户重启小温暖入口即可。5项角色/继承定向、12项虚构凭据打包检查通过，配置及12例完整性验证通过；没有新增真实API/凭据读取或后台调用。私有迁移报告var/diagnostics/style_1.1_cadence_budget_2026-10-21.json，公共检查reports/style_1.1_config_check_2026-10-21.json。版本/uv.lock已同步0.1.6，wheel/sdist与新角色/配置/排除内容已核对，SHA256SUMS-0.1.6.txt已保存。任务完成，无需重复付费测试或迁移。

## 最新 RUNTIME-OPT-01（2026-10-21，0.1.5，已完成）

用户授权降频并要求每轮带发送时间。新策略：原话即时保存，完整诊断每10轮、约20次提交增量投影；记忆/情绪/状态30轮，反思/关联/主题/归因90轮，180轮人格审阅；5秒空队列轮询。延后材料在runtime元数据持久积累，与cursor批次结束原子更新，压缩前即使没有新消息也补齐深度工作。未完成工具协议/用量仍即时保存，已完成协议只在10轮检查点保留全量。3份配置已同步，重启生效，日预算1M/压缩650k不变。

本地读缓存按文件属性失效、深拷贝避免污染，doctor仍强制重新校验字节；档案仍权威，投影增量并可重建。消息上下文含UTC+8发送时间和当前服务端时间，材料/压缩窗口也带created_at，原始body不改。小温暖persona@3及继承记忆保留。237项完整离线回归（151.05s）+43项时间材料定向+12项打包排除通过；进程死亡测试已接增量投影路径。固定快照上下文中位5.0716→0.6679秒、原话提交0.8915→0.3625秒，报告runtime_optimization_benchmark_2026-10-21.json。0.1.5 wheel/sdist构建、源码外独立安装10轮smoke通过（只有1次完整协议，20条原话重启后完整，身份/时间/新频率/doctor正常），见runtime_optimization_package_2026-10-21.json。uv.lock已同步0.1.5。

本轮0真实API/真实凭据读取，没有停用户聊天或写其档案；测试只写忽略的副本，用户重启启动小温暖.cmd即可。说明docs/运行开销优化_0.1.5.md。未实现流式输出或身份硬锁，真实长上下文与长期语义仍待验证，已知遗忘/召回缺口仍开放。不要重复迁移或付费核对。

## 最新 IDENTITY-01（2026-10-21，身份修复已实测）

用户“仍然加载ATRI角色卡”实际是语义身份被旧对话干扰：新卡已在真实API协议中，模型仍说ATRI/不认识小温暖。ContextBuilder将原继承snapshot内61条消息作为带来源的历史档案数据提供，不再用当前assistant角色回放；P00_current_identity在上下文首尾明确当前角色。原记录与承诺保留，历史错误自述须按当前卡纠正。新增PersonaPatcher.human_replace，人工/经验改卡保留inherited_snapshot。

用户库先备份var/backups/xiaowennuan-before-identity-fix-20261021-004236.zip，后发布persona@3，现有67条原话/全部旧revision未变；模板15条，运行卡加P14继承说明为16条。本地索引/doctor通过，16项离线回归通过（reports/identity_context_fix_2026-10-21.xml）。仅1次官方live诊断、无自动重试/tools/后台执行，返回“我叫小温暖”并解释ATRI记忆继承；16188 tokens，诊断未写入聊天历史，仅用量入账。私有报告var/diagnostics/identity_context_fix_2026-10-21.json。用户重开启动小温暖.cmd即可；不要重跑付费检查或迁移，不将单次通过当成长期角色稳定保证。

## 最新 LAUNCHER-02（2026-10-21，启动修复及实测完成）

用户报hell.exe无法识别；两个CMD改为ASCII/CRLF、完整PowerShell路径，PS1新增Character xiaowennuan预设生成中文名，避免CMD中出现中文内容和切换代码页。小温暖预设仍为Root var/xiaowennuan、Agent atri，不影响已继承的记忆。实际完整CMD -CheckOnly成功（uv同步、凭据状态、现有库doctor），0模型请求；隔离模拟调用的936/65001与中文空格路径四组检查通过，参数正确；报告reports/launcher_encoding_fix_2026-10-21.json。原始报错未在隔离复现中稳定重现，勿编造已证实的底层截断原因。用户可关闭旧报错窗口重新双击。无须再开live验证或重做记忆迁移。

## 最新 MEMORY-INHERIT-01（2026-10-21，已实际迁移）

按用户明确请求，ATRI记忆已完整迁入此前不存在的var/xiaowennuan，旧var/myatri-main保留，并备份到var/backups/ATRI-before-inheritance-20261021-003032.zip。413个历史版本记录原样保留（61条消息、21事件、19情绪评价、19临时状态、8摘要等），队列/协议/用量随库继承；新增persona@2载入小温暖卡及P14继承来源，不改写历史姓名/原话。内部agent ID继续atri，CMD与文档均已同步；显示名/当前人格为小温暖。不要再使用--agent xiaowennuan打开此库，否则读到另一个隔离域；下文原先新库方案已由本迁移更新。

scripts/inherit_atri_memory.py只允许新目标，先锁定/备份再恢复及版本化换卡；迁移与角色导入4项定向回归通过。实际doctor/SQLite校验通过，旧记录均未变，本地TF-IDF水位当前；迁移报告var/xiaowennuan/memory_inheritance.json。最终按CMD提取root/agent核对新入口，当前人格persona@2；741个备份档案文件与源文件字节一致，姓名/学校/兴趣/保留记忆查询均有候选结果（不证明真实模型回答质量）；live配置1M/650k/20轮生效。0模型API/凭据读取，未执行旧任务，也未自动启动live。今后继续用小温暖入口，新旧库后续独立保存。未修复之前已知的召回/忘记信息缺口。

## 最新 CHARACTER-01（2026-10-21，角色卡导入完成）

用户提供的小温暖1.0原文已保存在config/personas/xiaowennuan/source.md（与附件字节一致）；persona.md完整保留十三部分，按稳定ID分为13项并加P00来源/记忆边界。新增根目录启动小温暖.cmd，首次使用独立var/xiaowennuan、agent xiaowennuan初始化；沿用live.local.toml和Windows凭据，显示名“小温暖”。ATRI旧库/默认模板保留，不将旧对话迁移为新角色经历。启动器支持persona/agent/display-name参数，系统规则不再强制ATRI身份。

11项定向离线检查、原文完整性、PowerShell语法、验证wheel内角色文件一致检查通过，证据reports/character_import_2026-10-21.xml/json。未读真实凭据、未调用API、未改用户运行库，也未实际开启新角色。身份稳定仍是角色约束而非新增硬锁；原卡五种记忆分类没有变成五套新引擎。用户双击新入口即可，不替其自动开live。角色卡修改只对新库初始化生效，已有库需persona edit版本化修改。打包清单已纳入角色文件和新CMD；验证wheel仅在reports/character_package_tmp_20261021，dist既有0.1.4未重发。

## 最新 CADENCE-01（2026-10-21，0.1.4，离线验证完成）

当前任务是用户授权的降频：live上下文1M/650k压缩软阈值，原话即时保存，20个成功用户/助手回合后合并记忆/情绪/反思/临时状态等；Compactor.before_compact先等待维护依赖，失败不先压缩。新增runtime/maintenance.py及A1/emotion批量入口，阶段checkpoint与游标持久化。llm_activation默认在产品配置中false；无需每轮API选状态。旧逐条任务迁移cancelled而非冒充已整理；运行库不直接改动，由用户重启加载新代码。legacy无配置Application仍沿用旧行为以兼容既有程序接口，使用live配置/默认配置文件启用新策略。

已完成：完整227项回归通过（200.93s）+最后16项定向通过（60.20s），9个新用例覆盖轮数、原话即存、预压缩顺序、失败阻断、重启不重付费、旧任务取消、来源校验与用量锚定。uv.lock已离线同步0.1.4，wheel/sdist已构建并从源码外实际离线安装验证，报告reports/cadence_package_smoke_2026-10-21.json，详情docs/调用节奏与压缩策略.md。无新真实API/凭据读取/用户运行库写入，原聊天未被停止；用户重启即可加载，不要替其开启live。真实650k上下文/新batch语义尚未实测；临时验证码撤回及检索排序仍是后续开放项。维护协调锁当前限同一进程，不要另开付费worker与聊天并行跑维护。

2026-10-20 最新预算：用户明确要求每日额度1000000 tokens，已更新本机live配置、公开live模板和一键启动初始化行为。不要恢复历史30000测试额度。现有用量记录保留；用户自行重启，无需替其启动付费进程。

## 最新：Windows 一键启动（2026-10-20）

用户可双击根目录启动MYATRI.cmd；自动uv sync --frozen --extra neural，调用scripts/start_myatri.py检查配置/Windows凭据/固定var/myatri-main，完整性正常后启动live聊天。提供的密钥已存Windows凭据并验证，文件与脚本无密钥。已有角色库不会被模板覆盖，锁位于库外防重复打开并兼容备份。自检命令：powershell -NoProfile -ExecutionPolicy Bypass -File scripts/start_myatri.ps1 -CheckOnly。实际CMD/PowerShell入口、中文空格路径、重复拦截、重启保留和持锁备份均通过，无新增模型请求或常驻进程。除非用户要求，不要自动启动付费聊天。用户以后只需双击；退出用/quit。

## 最新 EMO-01（2026-10-20，0.1.3，离线工程验证完成）

最终接续：本次已完成，不需继续开发或启动live。完整218项通过（154.85s）+最后26项定向通过（9.81s），上游1000次数值对照通过。0.1.3 wheel/sdist真实构建；源码目录外离线安装wheel验证评价/重启/上下文/撤回/doctor及CLI与许可哈希通过。证据见reports/emotion_{regression.xml,targeted.xml,upstream_parity.json,package_smoke.json}与根目录情绪模块开发.md。0次真实模型API/密钥读取/用户运行库改动，无新运行依赖。下方“最终验证中”过程说明仅保留历史；新prompt真实语义与长期质量尚未验证，不重跑既有付费smoke。

用户授权GitHub复用后开发情绪模块，要求项目根目录情绪模块开发.md。代码已接通；详情读该文档及STATUS最新节。只复用emotional-memory的纯数学小内核；许可和哈希已登记，未装框架/新增依赖。上游1000次对照通过、初轮201项非打包回归通过；最终完整pytest正在运行（含26项情绪用例和新版许可测试）。需确认最终结果并完成源码目录外wheel smoke、文档最终结果与打包。当前无真实API或凭据读取，无用户运行库改动，无子Agent。不要因历史“T00规划”重做整个项目，也不要启动live验证。

重要边界：后台评价通常下一轮生效；只读投影随配置重算，不是心理测量。v1同Event一条不可变评价、支持人工撤回及直接open/paused余波原子discard，不递归改后续解释/人格。`emotion appraise`沿用drain会处理同库其他到期任务；真实模式有额外预算内请求，本轮未执行。旧库不自动回填；纯fixture明确defer。可选心境重排默认关闭，只用于前台候选，不用于人格证据。

## 最新 REUSE-01（2026-10-20，0.1.2）

用户要求真正复读 A-MEM / Letta 并移植现有功能中行为一致部分。生产已改为 `memory.graph` 调用 `_vendor.amem.iter_unique_neighbors`、`storage.archive._atomic_write` 委托 `_vendor.letta.atomic_write`；后者覆盖档案和索引发布。A-MEM只是8物理行的小内核，Letta只是通用文件写入；未装完整框架，不夸大成整套记忆/运行时接入。源码、许可证和哈希登记在 LICENSES/upstream/manifest.json，报告 reports/upstream_reuse_2026-10-20.md；wheel附带上游许可。A-MEM35/Letta38定向通过；完整192项回归通过（140.56s），wheel在源码外离线init/chat/compact/doctor通过，发行包上游许可/临时路径检查通过。旧未复制声明已加历史说明。无真实模型API调用/凭据读取/运行库修改。两个子Agent完成后由主Agent收尾，禁止递归派生。

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
