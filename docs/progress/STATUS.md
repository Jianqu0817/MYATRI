# MYATRI STATUS

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
