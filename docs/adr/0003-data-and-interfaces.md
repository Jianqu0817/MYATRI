# ADR 0003：契约与接口

2026-10-20。公共模型见 src/myatri/contracts/__init__.py，Pydantic v2，schema 1.0，UTC ISO 时间，agent_id/user_id 隔离。不可变 Record 使用稳定 ID 与 revision，引用 ID@revision；内容 hash 为 body_markdown/payload 规范 JSON SHA256，存储另校验完整档案字节。新修订需 supersedes_revision。来源引用在提交时校验存在、隔离与版本；同一 manifest 可引用其中的新记录。

Record 为权威信封，payload 由 Event/TemporaryEntry/BehaviorAttempt/PersonaPatch 等各模块模型验证。运行规则不进入人格。近期感受是 TemporaryEntry 视图。注意激活只是投影，表达/行动必须真实消息来源。自发想法引用 cognitive_run，不增加事件根。公共 Proposal 传 read_versions，单写提交执行 CAS，语义冲突不盲重试。
