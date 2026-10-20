# MYATRI 0.1.1：持久运行修复

2026-10-20（Asia/Shanghai）。本次修复由主代理集成；先后复用原三个分工、余额恢复后重新建立三个分工继续，未同时超过三个子代理。版本由 0.1.0 更新到 0.1.1，依赖版本不变。

## 当前结果

已修复此次代码审查确认的持续运行问题，并把日常表达/后续反馈接入生产后台。完整验证及发行包结果在本页末尾记录。本次没有读取真实用户运行库、密钥，未调用外部模型 API、启动付费常驻任务或外发消息。原有 live 报告保留为历史证据，不代表新归因 schema 或长期拟人质量已经 live 验收。

“像人类、持久化效果好”落实为可检查的行为：记住原话与变化经过，允许反思修正而不改写过去；注意有限但来源仍可恢复；想过、说过、做过、得到回应分别记录；可以暂缓、矛盾、放弃或保持未知，不按时间和次数自动成长。长期角色效果仍需独立场景评价。

## 修复对照

|审查项|现在的行为|证据入口|
|---|---|---|
|CTX-01 多次自动压缩|有摘要后仍可续压；按覆盖水位判断进展，最多有限轮次，避免无界递归。|test_context.py / test_llm_context.py|
|长历史语义整理|只把未处理的原文片段送模型；游标持久化，重启继续；旧要点逐条核对原文 span 后复用，未处理完不标 covered。失败保留已验证语义与未处理原文。|test_llm_context.py；fix_context_notes_2026-10-20.md|
|摘要注意力补修|5000B投影兼顾早期约定、最新变化、待解问题、查询相关材料及近期内容；不永远只显示最旧前缀。不自动裁定新旧认识冲突。|test_summary_attention.py|
|M01 历史快照|索引世代与请求快照不兼容时，跳过该代向量/主题/图，用请求快照原文及有类型语义边回退；历史查询不见未来关系或主题文字。|test_memory_consistency.py|
|M02 并发发布|在写锁内比较 manifest 序号，旧构建可保存世代但不能倒退 current；显式 rollback 仍可用。并发构建的旧保存文件也不继承未来主题摘要。|test_memory_consistency.py|
|R-MEM-03 历史证据|节点/向量使用当前投影，证据存在性校验使用该快照可读的固定 revision；thought@1 不因 @2 出现就丢失。|test_memory_consistency.py|
|R01 本地计算阻塞|同步档案/TF-IDF/构图/Leiden/序列化分阶段放到线程；异步外部 provider 仍在原事件循环 await，前台及心跳可推进。|test_memory_consistency.py / test_neural.py|
|A06 全历史模型输入|A1 有界相关旧事件候选、原文窗口与持久 checkpoint；A2/A3/A5/A6/A8 按完整 16000 请求预算选材并记录省略；A7 必需证据不全就 defer。|test_cognitive_materials.py / test_experience.py|
|A04 时间退出后台|新临时状态时间必须 aware 并转 UTC；合法旧无时区值按配置时区解释；坏旧记录单独报告到 scheduler_issues，不使整个后台退出。|test_reliability_integration.py|
|A01 主题饥饿|只对 needs_summary 排队，不再先切前八项而漏掉后方主题；队列按材料键去重。|test_reliability_integration.py|
|A02 到期复审/空闲|复审键包括状态与新证据 refs；同材料不因时钟产生新证据，新增证据可再次复审；持续空闲按活动边沿处理，不每秒重写 schedule。|test_reliability_integration.py / test_jobs.py|
|A07 共享日额度|同 runtime SQLite、同 provider scope 跨 domain/实例/进程事务预留；每次重试独立占额度。超时、取消、崩溃保持保守未知占用，UTC换日恢复新额度。旧日志升级导入。|test_shared_budget.py|
|R-MEM-04 非法日期|日期文字解析失败时保留普通查询，并说明未应用自动日期过滤；不退出聊天。|test_memory_consistency.py|
|PERSONA-01 巩固旁路|公共 create 拒绝直接 consolidated；必须走人格变化原子提交。discarded/consolidated 不得绕 settled 复活，重新考虑须新状态保留来源。|test_reliability_integration.py|
|A05 日常反馈归因|on_answer 持久入队，A1新事件触发反馈候选；语义模型仅提出有逐字来源的 expressed/反馈关联，统一提交并保留 unknown。|test_reliability_integration.py；prompts/attribution/v1.md|

A03 的 reality_scope/occurred_at/status 投影及失效摘要双路径过滤是前次升级已有修补，本轮保留并回归，不重复称为新修复。

## 日常归因的具体边界

助手回复先保存，后台再核对当时上下文是否已有对应 open 意图。后来产生的想法不能追认成早先的行动；激活不等于表达。这里只记录本地会话 expressed，不把聊天声称当工具执行或实际外发。

后续用户事件引用逐字 source_span 且消息时间晚于真实动作，才可作为反馈候选。观察到反馈表示不再“完全没有反馈”，不等于成功，也不决定正面或负面评价。状态已放弃时仍能补记当时表达与迟到反馈，不复活当前状态、不增加独立事件根、不直接修改人格。

候选按固定小批持久排队，事件/动作先占材料预算，避免候选多时必需事件被挤掉。planned/draft/unknown 或缺有效发生时间的历史记录不会进入已执行反馈归因。模型重复输出同一表达按稳定 ID 去重。保存结果后状态变化不会使纯历史表达永久 CAS 失败；同一实际表达的并发反馈只合并经过核验的事件集合，不重跑模型、不覆盖已有反馈。写入动作本身不同则拒绝合并。

失败任务现在可 `jobs retry <id>`，默认复用保存结果；需要重新选材/生成时显式 `jobs retry <id> --regenerate`。`jobs cancel <id>` 不撤销已经发生的模型调用或已提交档案。活跃租约和成功任务有保护。`doctor` 同时显示失败任务及调度问题。后台 worker 异常会被监督并报告，避免界面看起来仍在正常整理。

## 与持久化有关的取舍

- 原文、确切 revision、来源链和 manifest 仍是权威；向量、主题、摘要和归因都是派生内容。没有修改用户旧 records/commits。
- A1 窗口均提交抽取，表示材料覆盖，不代表模型穷尽语义。窗口 checkpoint 防止重启重复请求已保存结果，但无法保证网络已收费、结果尚未持久化时的绝对 exactly-once。
- 新 live A1 的事件身份不再只由模型 event_key 决定；跨消息归并必须引用本轮展示的旧事件，避免键碰撞把不同经历合成同一个。候选漏召回仍可能保守保留语义重复，需要后续有来源的归并流程。
- 反例与异质材料有预留；完整审阅超预算会 defer，不以裁掉证据换取 accept。有限注意不证明没有其他证据，遗漏数量/范围随 run 保存。
- 不兼容索引会保守回退，可能降低当轮语义召回能力；没有声称实时所有记忆都参与向量搜索。全量索引和部分档案读取仍有规模成本，没有实现 ANN、局部聚类或长文 BGE 分块。
- 共享预算仅覆盖同 runtime DB/scope，不是全账号跨 root 硬账单上限；各实例应统一额度策略。未知计费保持占用可能提前拒绝，真实 usage 超估计只能如实记录并阻止后续请求。
- 稳定身份硬锁、Entity/Skill/Procedure、工具执行学习与长期语义评估仍开放，未用本轮修复冒充新增功能完成。

## 运行验证

首轮完整回归：**172 passed，116.24 秒**，结果 [fix_full_regression.xml](fix_full_regression.xml)。此后交叉审查又补了归因规模、缺时间、重复输出和并发合并，以及摘要注意投影，以下最终回归优先。

定向证据：[上下文](fix_context_notes_2026-10-20.md)、[记忆/索引](fix_memory_notes_2026-10-20.md)、[认知材料](fix_cognition_notes_2026-10-20.md)、[共享预算](fix_budget_notes_2026-10-20.md)、[摘要注意](fix_summary_attention_notes_2026-10-20.md)。默认 pytest 已收集原 M01/M02 正常回归，不再依赖 audit_ 文件的 strict xfail。

最终完整回归：**178 passed，138.97 秒，0 failed/errors/skipped**，命令 `.venv/Scripts/python.exe -m pytest -q --tb=short --basetemp=reports/fix_final_all_tmp --junitxml=reports/fix_final_regression.xml`，结果 [fix_final_regression.xml](fix_final_regression.xml)。随后对最终的动作时间来源防护、历史表达及并发反馈做定向复测：**16 passed，26.41 秒**（[XML](fix_attribution_verified.xml)）；打包配置更新后凭据命名排除和真实构建专项再次 **12 passed，4.83 秒**（[XML](fix_package_security.xml)）。这些与全套有重合，不相加冒充独立场景数量。

`uv lock --check --offline` 成功，仍为锁定的56包，无新第三方依赖。版本源/pyproject/lock/本地editable安装元数据均为0.1.1。首次无隔离editable更新暴露本机缺少editables构建助手；按已安装Hatch源码支持设置显式src开发路径后离线更新成功，没有安装额外包。

wheel/sdist 使用 `.venv/Scripts/python.exe -m build --no-isolation` 构建；离线把实际 wheel 安装至独立 target，在 `C:/Windows/Temp` 用该安装副本验证新 attribution/activation/compaction prompt、普通聊天（含非法日期文字）、压缩与doctor通过，未调用凭据或API。归档成员检查确认没有私有 live.local 配置和本轮测试临时目录。包验证/校验和见 [package_smoke_0.1.1.json](package_smoke_0.1.1.json) 与 `dist/SHA256SUMS-0.1.1.txt`；后生成的包检查JSON不进入自身sdist，避免递归记录旧hash。

批量清理合成测试临时目录的命令被工具策略拦截；为保持其他修复交付不受影响，这些诊断目录保留在reports，并已通过构建排除规则和真实归档成员检查确认不进入发行包。它们不是实际用户数据。没有运行后台服务或遗留付费任务。当前本地结构修复已验收；新归因schema的真实模型判断、长期角色连续性及开放设计继续保持pending。
