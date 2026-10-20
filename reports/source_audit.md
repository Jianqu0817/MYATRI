# T00 来源审计

历史记录：本报告描述初次独立实现时点。0.1.2 的来源复读及两处实际改编见 [本轮复用报告](upstream_reuse_2026-10-20.md) 与 [逐段清单](../LICENSES/upstream/manifest.json)，下文“当前无复制”不再代表最新版本。

检查日期：2026-10-20。初始工作区仅 README 和三份规划文件；父目录 D:/、D:/DS_workspace/ 及本项目未发现 AGENTS.md，无已有代码或进度可续接。本次四份指定文档均已阅读。

锁定清单包含 A-MEM、Ashley、GraphRAG、Graphiti、Thoughtful Agents 的提交、源码路径、许可证和静态检查范围。实施采用独立 Python 代码，不复制上游源码，不安装这些完整框架。故本次未执行它们、不把其 README 能力当作运行结果。引用定位沿用锁定清单；如未来复制代码须再次获取锁定版本及 LICENSE/NOTICE，当前未发生移植。

DeepSeek 当前官方 thinking/tool/chat 文档已于实施时重新查阅（只读网页，无 API 调用）：
- https://api-docs.deepseek.com/guides/thinking_mode/
- https://api-docs.deepseek.com/guides/tool_calls/
- https://api-docs.deepseek.com/api/create-chat-completion/

网关显式传 thinking enabled/disabled；工具请求保存 reasoning_content 在临时协议历史，不能入角色经历；strict beta 默认不启用，结构化输出使用 JSON mode + 本地 schema 校验。模型名由配置给出，工具/thinking live 能力开关默认 false。付费调用仍禁用。来源锁定的网页说明与本次实际实现/运行范围分开记录。

T00 验收：来源及采用方式已登记 THIRD_PARTY_NOTICES.md；当前无复制片段；原规划保留。依赖许可证另由真实安装 metadata生成，不从上游总许可证推断。
