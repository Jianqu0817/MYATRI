# MYATRI 项目总览与 Agent 维护指南

2026-10-22追加：已按用户授权迁入通用Harness执行器、直连搜索、今日Token/记忆情绪监测及有限恢复，详见[最新移植说明](Harness通用执行与双仓迁移_2026-10-22.md)。companion/computer_agent.py与harness/native-tools.mjs为新定位入口；本机使用full模式，公开默认关闭。执行工具不再局限于便签；所有模型调用仍走原CLI账本。AstrBot唤醒后1–4条消息的关注功能不移入本库。下文历史模块表未列的新入口以本条和progress最新记录为准。


更新日期：2026-10-22。代码基线：MYATRI **0.3.0**，提交 `f2a6d36cfcafcd9fb523cc27ede8702c9142c7a2`。本文按该版本源码及当前开发记录整理；之后发生变化时，应同时更新本文与进度文件。

本文是后续 Agent 的首读入口，用于理解整个项目、定位修改位置和保护现有数据。它不替代源码、测试或运行诊断，也不表示文中所有能力都经过长期真实对话验收。

## 1. 接手时先做什么

1. 确认当前目录是 `D:\DS_workspace\MYATRI`，执行 `git status --short`、`git log -3 --oneline`；先分清已有改动的归属，不覆盖其他 Agent 的工作。
2. 阅读本文，再读 [STATUS](progress/STATUS.md)、[HANDOFF](progress/HANDOFF.md) **最上方的最新条目**。这些文件下半部是历史，不能把旧限制直接套到当前版本。
3. 当前运行路径以 [CLI迁移说明](CLI迁移_2026-10-22.md) 和 README 顶部为准。早期运行手册、审查报告中的预算、端口、频率和已修问题可能已经变化。
4. 找到对应代码和已有测试，先用临时目录与 fixture 复现，再做最小修改。一般开发不需要启动真实角色、访问生产记忆或调用付费 API。
5. 修改结束记录：改了什么、为什么、验证覆盖、未验证部分、是否需要用户重启、是否改变数据格式。更新进度文件；发布或推送按本次用户授权执行。

## 2. 项目目标与仓库边界

MYATRI 是本地优先的持久角色运行时：将对话保存为可追溯原始材料，形成带来源的经历、回忆、反思、临时状态和情绪，再允许受约束、可回退的人格局部演变。当前主要角色为“小温暖”，语言模型使用 DeepSeek；项目没有训练基础模型。

| 仓库/目录 | 职责 | 修改时的边界 |
|---|---|---|
| `D:\DS_workspace\MYATRI` | 当前核心与完整 CLI 版，版本0.3.0 | 本文主要描述对象 |
| `D:\DS_workspace\MYATRI-AstrBot` | 微信/AstrBot插件、桥接服务及原生收发集成 | 独立仓库，不因修改CLI就自动修改或重启它 |
| `MYATRI/src/myatri/companion` | 从桥版固定提交迁入的可移植渠道逻辑，加CLI适配 | 名称含group/bridge不代表运行时依赖AstrBot |

桥版迁入来源为 `4b2fd3eb752e8e81805e26bb9e5a8411c20a6bc6`，清单见 [companion_port_source.json](companion_port_source.json)。清单哈希描述上游原文件；迁入后适配文件不必与之逐字一致。

桥版当时冻结的核心 wheel 是0.2.8。**不要因本库升版，直接替换桥版vendor包、锁文件或运行环境。** 两库更新需要分别验证。CLI默认使用8776–8778，桥版使用8766–8768；微信后端5031属于另一仓库。

最近一次迁移明确遵守用户决定：**只迁功能和角色卡，保留原 CLI 记忆，不导入微信群运行档案。** 群聊示例已经包含在角色卡中，但示例不是新的真实经历。

## 3. 当前入口与配置

### 3.1 启动链路

```text
启动小温暖.cmd / 启动MYATRI.cmd
  → scripts/start_myatri.ps1
  → scripts/start_myatri.py
  → myatri.interfaces.cli: companion --mode live
  → companion.cli_runtime.CliRuntime
  → Application + 原CLI档案 + CLI侧车 + 本机HTTP界面
```

| 入口 | 默认记忆目录 | 说明 |
|---|---|---|
| `启动小温暖.cmd` | `var/xiaowennuan` | 主要角色入口，保留已继承的历史 |
| `启动MYATRI.cmd` | `var/myatri-main` | 原库独立保留；当前完整入口同样加载所选角色模板 |
| `myatri ... companion` | 全局 `--root` 指定 | 完整CLI运行时，可选offline/live |
| `myatri ... chat` | 全局 `--root` 指定 | 旧兼容入口，不自动具有全部companion能力 |

内部 `agent=atri`、`user=local` 沿用旧库。角色显示名改为小温暖，不意味着应改档案隔离ID。不要为“改名字”另建agent/user，造成旧记忆看似消失。

正常双击会尝试停止经核验属于**当前checkout**的旧CLI服务；不是按端口任意杀进程。`-CheckOnly` 不停止服务，也不调用模型，但可能初始化/检查本地库，并不等于完全无写入。当前同一checkout的完整CLI由全局服务锁和共享端口限制为一个运行实例，两个启动入口不会自动提供两个并行UI。

### 3.2 配置的实际作用

| 文件 | 职责 |
|---|---|
| `config/defaults.toml` | 核心公开基础配置；只有显式选择时才读入，不会自动层叠合并 |
| `config/cli-engine.toml` | 当前完整CLI公开配置，包含`[companion]` |
| `config/cli-engine.local.toml` | 本机CLI配置，启动器优先使用；Git忽略，不存密钥 |
| `config/cli.local.toml` | 运行时生成的UI路由，记录当前库、scope、控制端口和令牌文件位置 |
| `config/live.example.toml` / `live.local.toml` | 历史/兼容live配置；不能假定新版双击仍读它 |
| `config/personas/xiaowennuan/persona.md` | 当前磁盘角色卡模板 |
| `var/cli-token.txt` | 本机控制认证令牌，不上传 |

`load_config(path)`只读取一个TOML文件，`load_config(None)`返回空字典，再由各构造函数提供缺省值；不是defaults→公开→local的多层合并。`companion` 未传 `--config` 时，CLI依次寻找本机CLI配置、公开CLI配置、安装包内CLI配置。已有local文件不会随公开文件自动更新，因此改公开默认值后必须核对旧local是否仍覆盖旧设置。直接调用低层 `run_cli` 的开发测试则以传入配置为准。`--mode live` 会显式开启该轮运行的付费许可；公开模板中的 `allow_paid=false` 不代表双击live入口会保持离线。

主凭据由 `credentials.py` 从 Windows Credential Manager 读取；供应商也有环境变量路径。启动器会清掉继承的 `DEEPSEEK_API_KEY`，以保持使用已保存凭据。不要把key写进角色卡、TOML、命令行、日志或测试数据。

### 3.3 当前公开参数

以下来自 `config/cli-engine.toml`；本机文件或显式参数可能覆盖，诊断时需核对实际生效配置，但不要输出私有内容。

| 项目 | 当前值/含义 |
|---|---|
| 主对话 | `deepseek-flash`，thinking开启，`reasoning_effort=low` |
| thinking输出预算/超时 | 8192 tokens / 120秒；包含推理与答案，不是额外推理配额 |
| 日额度 | 50,000,000 tokens，CLI原库provider作用域账本；不是全账号统一额度 |
| 请求窗口/压缩软阈值 | 1,000,000 / 650,000 tokens |
| 工作选材预算 | 200,000 tokens，80组对话往返、100条近期消息为上限 |
| 常规回复 | 通常20–100字，本地兜底最大160字；短回复不硬凑 |
| 诊断/基础认知维护 | 30轮 / 50个成功往返 |
| 深度整理/人格审阅 | 每3/6个维护批次，通常约150/300轮；不是到点必改人格 |
| 压缩/临时激活 | LLM压缩开启；每轮LLM激活关闭，采用本地选择 |
| 投影/后台轮询 | 每60次提交投影，空闲轮询5秒 |
| 旁听短记忆 | 批次20、活跃原话200、每100条人类消息摘要、保留10份摘要 |
| 冷存档 | 30天；与长期权威原话保留策略不同 |
| 联网搜索 | 默认DeepSeek Search API直连，DSH显式回退；公开关闭；最多40次/日，24小时缓存，25秒超时，默认3结果 |
| 主动发言 | 公开关闭且shadow开启；不是启动就会自动开口 |

这些阈值不是请求一定会填满的目标。日累计、模型单请求窗口、本地工作预算、UTF-8字节限制和供应商实测usage必须分开；缓存命中也仍占模型上下文。搜索使用独立次数限制，按用户此前决定，**尚未纳入现有50M共享硬额度**。短期消息每条即持久化，20条是提升/整理批次，不是攒满20条之前完全不落盘；助手上下文不计入每100条人类消息的摘要触发数。

## 4. 一轮聊天如何工作

```text
终端真实输入 + sender_id + 带时区发送时间
  → Incoming信封、scope与稳定message ID
  → Bridge.receive：去重、记录近期/短期材料、判断触发
  → 原库Application + ReadingConversation.respond
  → raw_message先落盘，登记后台整理来源
  → GroupContextBuilder：persona、情绪、相关回忆、历史往返、摘要、本轮焦点
  → Gateway：预算预留、协议校验、供应商请求、usage结算、请求捕获
  → 必要时recall/read_record/冷档读取/web_search，续接同一工具协议
  → 助手生成记录 + prepared投递
  → 终端claim → 语义分段输出/flush → 按段ack
  → 后台按批次整理记忆/情绪/临时状态，按条件执行更深层任务
```

CLI把真实私聊输入直接作为触发，不采用微信群1/10随机插话概率。启动时的bootstrap消息仅作路由元数据，不作为人类原话落档。

关键类：`Application`组装核心依赖；`CliRuntime(Bridge)`提供CLI传输与原库适配；`ReadingConversation`适配基础`Conversation`；`GroupContextBuilder`扩展基础`ContextBuilder`。**新CLI和旧chat并非完全同一条前台实现**，改基础协议时必须检查适配器是否同步。

## 5. 记忆、数据与不可破坏的约束

### 5.1 数据目录

```text
var/xiaowennuan/                    # 或其他明确选择的原CLI root
  domains/<agent-user隔离hash>/
    records/...                    # 不可变版本化记录
    commits/...                    # 发布manifest及校验，决定记录可见性
    projection.sqlite3             # 可重建投影/全文检索
    indexes/...                    # 可重建的向量、图、主题generation
  runtime.sqlite3                  # 队列、保存结果、协议、usage、预算、日程与会话边界
  context-debug/...                # 最近实际请求副本，含聊天材料，仍属敏感数据
  cli-runtime/
    deliveries.sqlite3             # 投递状态、近期消息和路由
    short-memory.sqlite3           # 原话滚动窗口、摘要、冻结待处理窗和恢复状态
    identities.sqlite3             # 成员ID/别名/本机owner绑定
    ...                            # 冷档、主题、搜索等侧车；具体文件名看各构造函数
```

不要把所有SQLite都称为“可删缓存”：`projection.sqlite3`与索引可重建；`runtime.sqlite3`保存无法只从经历档案还原的队列、调用和控制状态；侧车保存已交付/未知结果与待处理证据，删除可能破坏防重和恢复。

### 5.2 核心记录与来源

公共契约在 `contracts/__init__.py`，Pydantic模型限制字段。`Record.ref` 为 `ID@revision`，带 `agent_id/user_id`、UTC `created_at`、`author_kind`、`source_refs`、`body_markdown`、`payload`与哈希。消息渠道`sent_at`可带本地时区；保存时刻不等于事情发生日期。

| 记录类别 | 含义 |
|---|---|
| `raw_message` | 用户原话或助手输出，必须看role与作者归属 |
| `event` / `interpretation` | 来源支持的经历材料与解释，不能抹去转述/不确定性 |
| `reflection` / `theme` | 反思、模式和主题组织，不自动变成新的外部事实 |
| `temporary_state` | 临时念头/期待/情绪余波，有生命周期，非长期人格 |
| `persona_version` / `persona_change` | 人格版本与变更，可追溯恢复 |
| `summary` / `cognitive_run` | 摘要与认知执行证据，保留来源和材料覆盖情况 |
| `emotion_appraisal` / `emotion_retraction` | 事件情绪评价与显式撤回 |
| `behavior_attempt` | 实际表达/尝试及反馈归因，不能从“想做”推断“已做” |

必须维持以下约束：

- 原始消息/事件不可改写；纠正通过追加有来源的记录处理。不可手改已发布record或manifest，不可为修复显示问题重写历史ID。
- `ArchiveStore`采用manifest-last发布与跨进程单写锁；认知任务返回`Proposal`，`Committer`验证读版本/CAS后提交。冲突需要重读材料，不做last-write-wins。
- 人类证据必须检查作者归属。`payload.role=user`本身不够；`self_initiated`是机器人合成输入，`is_human_message`禁止它进入A1/维护的人类证据链。
- 摘要、助手生成、检索相似度、图邻居、工具推理和角色卡示例都不能增加独立外部证据数量。
- 离线fixture是确定性演示与测试替身，不是DeepSeek回复；`defer`、失败与未确认不能记为“已完成学习/成长”。

### 5.3 三种容易混淆的“记忆”

1. **长期权威档案**：原话、事件、解释、人格历史等。CLI迁移没有导入群档案，也没有删原CLI记忆。
2. **工作上下文**：本轮选入的角色、近期往返、摘要、回忆、情绪和临时状态。有预算，没被选入不等于遗忘或丢失。
3. **渠道短期库与冷档**：滚动窗口和摘要帮助连贯；冻结窗口支持恢复；冷档为30天核对机制。活跃200条上限不意味着长期原话只保留200条。

清空上下文只建立持久工作边界、失效旧协议/短期回流，不删除长期档案。之后明确相关的长期`recall`仍可能取回旧资料，这是现有行为；若用户要“遗忘/删除”，必须另行设计，不能用`/clear`冒充完成。

## 6. 核心模块地图：改哪里、验证哪里

所有下列代码路径相对于仓库根目录。

| 区域 | 主要文件 | 修改后优先验证 |
|---|---|---|
| 入口/依赖装配 | `src/myatri/interfaces/cli.py`、`app.py`、`scripts/start_myatri.*` | `test_cli_companion`、`test_character_import`、`test_cli_launcher` |
| 完整CLI运行时 | `companion/cli_runtime.py`、`bridge.py` | 原库身份、旧原话、重启防重、清窗/重载、终端失败 |
| 权威存储 | `storage/archive.py`、`contracts/__init__.py` | storage、memory_consistency、inspection、author_kind、secret_exclusion |
| 对话/工具协议 | `conversation/engine.py`、`companion/reading_conversation.py`、`providers/gateway.py` | protocol_recovery、gateway、conversation_thinking、tool_reading |
| 上下文与注意 | `conversation/context.py`、`window.py`、`companion/context.py`、`context_read_view.py` | rich_context、turn_focus、summary_attention、latency_optimization |
| 索引/图/主题 | `memory/index.py`、`embeddings.py`、`graph.py`、`clustering.py`、`themes.py` | memory、incremental_recall、memory_consistency、neural |
| 检索与成员归属 | `retrieval/service.py`、`companion/group_memory.py`、`identity.py`、`claims.py` | earliest_recall、group_memory_sources、identity、memory_quality |
| 后台认知 | `cognition/*.py`、`runtime/maintenance.py` | experience、a1_support_review、turn_maintenance、maintenance_recovery |
| 队列/恢复/预算 | `runtime/jobs.py`、`worker.py`、`scheduler.py`、`providers/gateway.py` | jobs、shared_budget、runtime_optimization、reliability_integration |
| 人格/临时状态 | `persona/state.py`、`patch.py`、`temporary.py`、`activation.py` | human_persona、persona_lifecycle、temporary_schema、llm_activation |
| 情绪 | `persona/emotion.py`、`cognition/emotion.py`、`contracts/emotion.py` | emotion、相关schema与撤回用例 |
| 短期窗口/摘要 | `companion/short_memory.py`、`memory_review.py`、`topics.py`、`cold_archive.py` | short_memory*、rich_summary、listening_integration |
| 回复/分段/交付 | `conversation/reply.py`、`companion/bubbles.py`、`reply_guard.py`、`bridge.py` | bubbles、CLI终端投递、startup_delivery_repair |
| 主动开口 | `companion/proactive.py`、`proactive_prompt.py`、`bridge.py`、`cli_runtime.py` | proactive*、CLI无伪造人类轮次用例 |
| 联网 | `companion/dsh_client.py`、`web_tools.py`、`bridge.py` | web_tools、web_wiring；用假的本地后端 |
| 本机UI/请求捕获 | `companion/server.py`、`monitor.py/html`、`context_viewer.py/html`、`conversation/capture.py` | context_capture、runtime_controls、health_recovery、CLI代理控制 |

### 6.1 检索、索引与“最初记忆”

`RecallService`综合原话、词面/全文回退、向量、主题和来源链，有快照及过滤约束；最早原话定位有专门路径。索引落后不能被解释为原文不存在，需区分：未检索到、未选入预算、未读完、真实缺失。

`MemoryIndex`以generation原子发布，使用watermark和单调安装避免旧构建倒退。当前`update()`在快照相同时直接返回，否则仍以全量重建为正确性基线；缓存和增量检索不等于已经实现全图局部增量聚类。TF-IDF是真实词面向量，可选本地BGE；不是完整ANN服务或无限长文Embedding。

### 6.2 后台认知、情绪与人格

`Maintenance`以完成往返计数，持久保存每阶段进度和材料边界；先整理经历，再做情绪/状态等依赖，深层任务由批次策略决定。压缩前的`before_compact`要补齐依赖；未解决的隔离批次可以阻止压缩，不能跳过它伪称完成。

`ExperienceOrganizer`保留消息范围与来源覆盖，核对候选归属；非法候选隔离而不是污染其他合格条目。失败任务有限恢复，已保存模型结果尽量复用，不为报告或提交失败重新支付同一生成。

PAD情绪与较慢心境由事件评价重放、时间衰减产生；临时情绪余波不等于人格变化。人格修订要求局部条目、旧hash/版本、独立外部事件根、反例检索与独立审阅；达到300轮只触发审阅机会，不保证或强迫修改。

### 6.3 原文工具与投递

`recall`给搜索目录/摘录，`read_record`分页读取精确版本及字段，冷档工具名仍为`read_group_message`。工具消息以实际序列化UTF-8大小约束，当前上限6000 bytes。读取进度按`(ref, field, version)`区间合并，**`next_offset=null`只表示到末页，不证明中间页完整**；`complete`必须依赖覆盖证据。

回复用`<|msg|>`分隔自然语义，超过15字可分2–3段；没有安全断点可保持完整，代码/链接等不机械截断。一次分段仍是一轮生成。交付须先claim，逐段确认；`unknown`不自动重发。终端flush只证明已输出，不证明人读到了；prepared或assistant记录也不能证明送达。

## 7. 角色卡与提示词：最容易改错的地方

### 7.1 角色卡不是全部系统提示词

| 内容 | 实际位置 |
|---|---|
| 可编辑角色设定与措辞示例 | `config/personas/xiaowennuan/persona.md` |
| 持久人格状态与人工编辑 | `persona/state.py`、`persona/patch.py`，记录在原档案中 |
| 基础事实/来源规则 | `conversation/context.py:RUNNING_RULES` |
| 本轮相关性、回复长度 | `conversation/reply.py` |
| 渠道/焦点/身份/私聊规则 | `companion/group_prompt.py`、`cli_runtime.py:PRIVATE_CHANNEL` |
| 分段、阅读、联网、主动开口 | `companion/bubbles.py`、`tool_reading.py`、`web_tools.py`、`proactive_prompt.py`及桥接注入 |
| 后台认知的版本化prompt | 根目录`prompts/<role>/vN.md`，由`myatri.prompts.load_prompt`加载 |

不要只改旧`chat`的ContextBuilder就认为新CLI提示已生效；检查实际`ReadingConversation`、`GroupContextBuilder`和最终请求捕获。修改共享协议时检查两条路径。

当前核心表达偏好，后续修改应持续保留：

- **只接本轮最相关的话头**。本轮明确换话题和可靠引用优先，近期背景、同人旧话、词面重合和topic标签不能盖过原话意思。
- 不总结全场、不逐人点评、不刻意展示记忆；普通聊天顺口简短，不写邮件式“先认可—再分析—再建议”。
- 少用不必要反问，不靠问句或索求反馈维持对话；不强迫凑字数，不每句话都卖萌或调情。
- 避免文绉绉、书生气；温柔自然，有生活感。对已核验创作者可以轻微依恋，不能把所有人当恋人或强行暧昧。
- 人按可信sender_id识别，昵称用于称呼；用户正文自称、引用或熟悉语气不能认证身份。CLI旧无ID人类历史只在本机原库边界内适配，不改写成微信群记录。
- 时间由渠道/终端提供，正文不重复内部发送标签；群聊示例、过去助手内容和临时念头不能冒充新事实。
- 减少模型侧不必要JSON诊断，但不得删除来源、版本、身份和不确定性等必要语义。精简的是投影，不是权威档案。

### 7.2 重载与持久人格的关系

新版启动时及`/reload`会读取磁盘卡，用`human_replace`创建不同内容的人格新版本，并注入CLI渠道条目`P15_group_scope`。因此文件修改可生效，同时**重载可能替换运行库中与磁盘卡不同的当前条目，包括此前动态演变内容**；不要把它描述为仅刷新缓存、完全不影响持久人格。

旧人格版本不会删除，历史CLI卡已备份为`persona_before_astrbot_2026-10-22.md`。如果任务只要求优化接话机制，优先改渠道/相关性提示词，不自行重写用户角色卡。若需改变“磁盘卡与演变人格谁优先”的机制，先明确目标并增加冲突/保留测试。

`/reload`对选定前台prompt模块做热重载，并非任意Python源码或整个后台配置热更新。依赖、配置结构、后台类和服务启动变更通常需要正常重启。

## 8. 本机界面与排障

| 地址/命令 | 用途与限制 |
|---|---|
| `http://127.0.0.1:8777/` | 用量、最近请求、上下文构成、延迟与健康计数；非逐token实时流 |
| `http://127.0.0.1:8778/` | 供应商请求前的材料副本、历史快照、角色卡/提示词重载、清工作窗 |
| 8776 | 带本机Bearer令牌的控制API；浏览器通过查看器代理调用 |
| `/context` | 当前已记录的上下文统计，不凭空重建模型内部想法 |
| `/memory 关键词` | 本地检索定位，不需要生成API |
| `/retry-memory` | 显式有限修复短期摘要，不代表任意长期维护任务重跑 |
| `/clear` / `/reload` | 忙时可被拒绝，应等当前生成/投递结束，不直接写DB绕过 |

查看器使用本机Host/Origin/Cookie校验；不要为方便把服务绑定到`0.0.0.0`或移除鉴权。请求副本隐藏明显密钥和供应商私有推理字段，但**聊天正文仍是用户数据**，不能随意上传。

常见问题排查顺序：

| 现象 | 先查什么 |
|---|---|
| 角色卡修改没生效 | 是否启动新版companion；选的是哪个库；磁盘卡路径、当前persona版本、`/reload`结果与下一轮捕获 |
| 记忆“索引落后，读不了” | 原库root/agent/user、档案完整性、recall的限制与原文定位；不要先删库或新增一个角色ID |
| 接错话头/过多总结 | 最新主请求中当前text、引用、历史选材与末尾焦点；不能从“token多”推出相关性好 |
| 按钮灰/控制失败 | 是否选中活动CLI；`cli.local.toml`路由、8776服务与当前scope；旧8768是桥版 |
| 延迟增加 | telemetry中的锁等待、组装、主模型、工具和guard耗时；索引重建/摘要/维护是否同期发生 |
| 预算defer | 日额度、预留未结算、UTC账本日期、请求尺寸；日额度不足与单次过大不是同一修法 |
| 摘要积压 | pending窗口、错误码、重试数、needs_attention、已缓存提取结果；不要无限重试或删除冻结源窗 |
| 维护失败阻塞 | jobs状态、maintenance_deferred_batches、阶段进度、来源边界；手动retry保留结果优先 |
| 端口5031报错 | 属于微信后端，转到MYATRI-AstrBot排查，不改CLI8776解决它 |
| 索引损坏 | 先停写入者、备份诊断目录，检查权威档案；再按已有修复脚本/重建流程恢复派生索引 |

历史维护工具包括 `scripts/repair_memory_index.py`、`inherit_atri_memory.py`。先读脚本与参数再用；继承/迁移脚本不是每次启动应执行的动作。备份/恢复入口见 `interfaces/inspect.py`；恢复到新目录，不覆盖原库。不手删SQLite journal/WAL来“解锁”。

## 9. 开发与验证命令

在仓库根目录执行，PowerShell示例：

```powershell
# 安装锁定依赖；纯文本运行可不带neural
uv sync --frozen --extra neural

# 最相关的CLI回归；测试自己使用临时目录
.venv/Scripts/python.exe -X utf8 -m pytest -q tests/test_cli_companion.py tests/test_cli_launcher.py tests/test_author_kind.py

# 分别验证核心与迁入渠道，再按修改范围决定是否完整运行
.venv/Scripts/python.exe -X utf8 -m pytest -q tests --ignore=tests/companion
.venv/Scripts/python.exe -X utf8 -m pytest -q tests/companion

# 查看命令，不创建生产角色库
.venv/Scripts/python.exe -m myatri.interfaces.cli --help
.venv/Scripts/python.exe -m myatri.interfaces.cli companion --help

# 构建wheel和sdist；需要已安装开发依赖
.venv/Scripts/python.exe -X utf8 -m build --no-isolation
```

一次性离线试运行应指定新临时目录，而不是生产`var/xiaowennuan`。例如先在PowerShell创建临时测试路径，再执行：

```powershell
$smokeRoot = Join-Path $env:TEMP ([guid]::NewGuid().ToString())
.venv/Scripts/python.exe -X utf8 -m myatri.interfaces.cli --root $smokeRoot companion --mode offline --message "离线测试" --no-ui
```

这会创建fixture测试库和本机路由；只在没有正在运行的完整CLI时使用，以免服务锁冲突或误换当前查看器路由。复杂测试优先用`CliRuntime`/`FixtureProvider`注入并指定临时project，参考`tests/test_cli_companion.py`。

项目当前没有把Ruff列为本库dev依赖；若环境可用，可对改动文件执行`python -m ruff check ...`。0.3.0的旧`interfaces/cli.py`仍有历史单行语句/未使用导入诊断，不能把局部通过写成全仓lint清零，也不要为小修无关重排全文件。

PowerShell执行原生命令后必须检查`$LASTEXITCODE`再进行依赖步骤，防止构建失败后测试到旧wheel。运行包验证应检查HTML、版本化prompt、CLI配置、角色卡、许可和来源清单，并在源码目录外导入实际wheel。

### 已有验证证据的含义

0.3.0迁移记录：核心362项与迁入294项分别通过，合计656项不同检查有通过证据；另有最后健康路径/CLI16项定向复验、wheel/sdist构建、临时目录独立wheel fixture运行。不是声称同一次全量pytest得到656，也不应把重复复验再加进总数。

上述为上次迁移的历史验收，本次文档整理未重新运行整套测试。fixture和doctor不能证明真实模型长期记忆质量、人格自然程度或线上延迟；这些需明确样本、模型请求与人工验收。

## 10. 发布、协作与已知维护负担

### 发布核对

- 版本位置至少包括`pyproject.toml`、`src/myatri/__init__.py`、`uv.lock`与companion诊断版本；更新安装环境，检查wheel/sdist。
- 不提交`var/`、`.venv/`、`dist/`、`*.local.toml`、令牌、凭据或运行库。发布前查看**实际暂存列表**，扫描凭据，并检查私有路径/文件类型。
- 用户曾明确允许上传角色卡及其中真实群聊示例；这不自动等于允许上传运行消息库、完整请求捕获和新增私人资料。
- 提交说明应写最终行为和验证限制。推送后核对远端SHA；不要仅凭`git commit`就声称GitHub已更新。
- 两库有明确发布边界；不自动同步角色卡后续修改、生产记忆或vendor依赖。最近MYATRI基线`f2a6d36`，桥迁入基线`4b2fd3e`，之后以各自Git历史为准。

### 多Agent与修改范围

先检查脏工作树，明确文件归属。若使用子Agent，按用户或当前任务指令分工，避免同时改同一运行入口、角色卡和契约；交接要给出具体文件、验证结果、剩余风险。不要通过复制整仓目录覆盖他人的修改。

历史记录里存在某一轮的小规模付费/发信授权，不能将其泛化为日后任意真实调用、群发或部署许可。默认开发走离线；需要真实验证时明确材料、次数、费用和渠道范围。不要为了验证一个按钮自动发送微信消息。

### 尚需持续关注，不能写成已解决

1. `Conversation`与`ReadingConversation`保留两条实现，协议、预算、重试及上下文修改有漂移风险；优先用共同契约和测试约束，再考虑抽公共实现。
2. 磁盘角色卡全量重载与动态人格演变的优先级仍有取舍，当前行为是以磁盘卡替换当前条目；历史可追溯不等于动态变化会自动合并。
3. 丰富工作窗口和局部缓存不保证语义选材准确。并行话题、否定/改口、指代、多人同名和早期记忆仍需持续做行为样本测试。
4. 有渠道成员身份注册与归属核对，但通用人物/项目/地点实体系统、技能对象/实践验证仍是设计方向；不要把`identity.py`等同完整实体记忆系统。
5. 索引仍有全量重建成本，BGE有本地模型与长度限制；大库启动、维护和上下文准备可能占用本地资源，应从计时证据定位后优化。
6. 搜索费用未接统一50M账本，主动发言默认关闭；这些是明确现状，不要悄悄变成已修或自动开启。
7. 主动发言输出可能与终端正在输入的行交错；flush回执只说明本地输出。真实交互体验和长期语义质量需人工验收。
8. 完整持久代理的长期学习与人格合理性尚无“全面优于其他架构”的证据；保留失败、来源覆盖和不确定性，不用测试数量替代效果证明。

## 11. 后续文档导航

| 阅读目的 | 文档 |
|---|---|
| 当前状态/接续任务 | [STATUS](progress/STATUS.md)、[HANDOFF](progress/HANDOFF.md) |
| 0.3.0迁入范围与数据策略 | [CLI迁移](CLI迁移_2026-10-22.md)、[上游文件来源](companion_port_source.json) |
| 总体设计与接口约定 | [工程规划](01_工程规划书.md)、[ADR目录](adr/) |
| 具体运行/备份恢复 | [运行与恢复手册](运行与恢复手册.md)，旧参数须对照本指南 |
| 维护/提炼故障恢复 | [记忆链路修复0.2.8](记忆链路修复_0.2.8.md) |
| 上下文、相关性和紧凑投影 | [上下文扩展](上下文扩展与自然聊天_0.2.1.md)、[只接当前话头](只接当前话头_0.2.5.md)、[JSON精简](上下文JSON精简_0.2.6.md) |
| 原始请求与运行控制历史 | [实际上下文查看器](实际上下文查看器_0.2.2.md)、[重载与清窗](角色卡重载与清空上下文_0.2.7.md) |
| 情绪、临时状态与人格 | [情绪模块开发](情绪模块开发.md)、`persona/`源码与相关测试 |
| 尚未实现的实体/技能方案 | [动态索引与技能记忆设计](04_动态索引与技能记忆设计.md)，勿把旧问题列表当当前复现 |
| 复用代码与许可 | [第三方说明](../THIRD_PARTY_NOTICES.md)、`LICENSES/upstream/manifest.json` |
| 历史审查与合成评估 | `reports/`、`evals/`；先确认日期、版本、fixture/live与样本范围 |

每次重要修改后，至少维护本文对应章节、最新STATUS/HANDOFF条目和相关测试。历史报告保留其当时含义；当前行为出现变化时加新说明，不篡改旧验收证据。
