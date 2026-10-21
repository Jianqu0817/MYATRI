> 2026-10-22：运行卡已逐字迁入 AstrBot 当前角色卡；此前 CLI 卡备份为 persona_before_astrbot_2026-10-22.md。功能迁移保留原 CLI 记忆，不导入微信群运行库。下文旧版本描述保留作历史参考。

# 小温暖角色配置

当前模板为角色卡2.0，此前曾人工保存为 `persona@17`（实际加载版本以运行库为准）：完整保留菅蘧提供的角色反应素材与六段真实群聊对话；身份问答可按情境留在角色中，涉及现实能力和记录时仍准确回答。

- `source.md`：用户提供的 1.0 原卡，逐字节保留。
- `persona.md`：MYATRI 可加载角色卡2.0。沿用稳定ID与记忆边界；完整收录用户提供的原话样例，区分反应素材与真实群聊记录，并把 AI 身份问答调整为不强制跳出角色。
- `style_update_2026-10-21.md`：本次用户提供的语气与性格补充及12个表达示例；不是已经发生的真实互动。

2026-10-21：当前运行人格已人工保存为persona@17；角色卡2.0完整加入原始反应素材及真实群聊对白。此前版本记录仍保留，当前以2.0为准。

在项目根目录双击 **启动小温暖.cmd** 即可，使用 `var/xiaowennuan`，以后启动延续同一份记忆。聊天显示名称为“小温暖”，系统身份由库中持久化角色卡决定。

2026-10-21 按用户要求，现有小温暖库已从 ATRI 原库完整继承记忆，并以 `persona@2` 载入本角色卡和记忆继承说明。历史档案、来源、时间及版本均未改写，内部 agent ID 继续使用 `atri`，以保持原校验和与引用有效；它是档案技术标识，不是当前角色名称。启动入口已同步使用此 ID。请勿用 `--agent xiaowennuan` 打开这份库，否则会进入另一个隔离域。

后续身份修复已保存为 `persona@3`：当前身份在上下文首尾明确为小温暖；继承的61条原始消息作为带来源、原角色、时间的历史档案提供，不再冒充当前助手的回复。旧身份自述和已发生的错误回答原样保留，不能覆盖当前身份。当前运行卡为模板15项加记忆继承说明，共16项。修改脚本后应关闭旧聊天窗口并重新打开。

角色卡1.1已在现有库人工版本化保存为 `persona@4`；语气更轻柔、灵动、文雅，亲近情境下含蓄主动、带一点狡黠与羞涩，减少客服腔和反复系统解释。旧人格版本、83条原话及记忆继承边界全部保留。

使用现有 Windows 凭据和 `config/live.local.toml`，无需再填写密钥。0.1.6采用每30轮完整诊断、50轮记忆/情绪/状态整理、约150轮反思、300轮人格审阅，投影约每60次提交/30轮检查点刷新；日额度50,000,000 tokens（50M）。单次上下文仍1M、压缩阈值650k，每条消息仍带发送时间。本机及公开配置均已同步；重启聊天加载新频率和额度。日预算按运行库计量，不是账号跨库总额。机制与性能基线见[运行开销优化](../../../docs/运行开销优化_0.1.5.md)。

原来的 `启动MYATRI.cmd` 和 `var/myatri-main` 保留，迁移前备份位于 `var/backups/ATRI-before-inheritance-20261021-003032.zip`。迁移详情见 `var/xiaowennuan/memory_inheritance.json`。小温暖可以继承并回忆这段数字互动历史，同时区分当时来自 ATRI 的发言与自己的当前身份。这不是角色卡中的生前经历。迁移完成后，两个库的后续对话分别保存，不自动同步；继续聊天请使用小温暖入口。

只检查准备情况、不调用模型（会在首次运行时创建新库，仍需要本机凭据）：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/start_myatri.ps1 -CheckOnly -Root var/xiaowennuan -Agent atri -PersonaFile config/personas/xiaowennuan/persona.md -DisplayName 小温暖
```

2026-10-21 启动兼容修复：CMD 使用纯 ASCII 内容、CRLF 换行和 Windows PowerShell 完整路径；中文显示名在 PowerShell 中生成。也可用简化自检命令 `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/start_myatri.ps1 -Character xiaowennuan -CheckOnly`。此预设继续使用继承记忆的 `atri` 内部域与 `var/xiaowennuan`。

如需手动离线检查：

```powershell
.venv/Scripts/python.exe -m myatri.interfaces.cli --root var/xiaowennuan --agent atri doctor
```

现有继承库无需再次初始化角色卡。以上仅检查库完整性；未来从空目录建立新角色时才使用 `init --persona-file`。

原命令行修改 `persona.md` 不会自动覆盖已启动角色库，已有库设定应通过 `persona edit` 产生新版本；微信群可在桥接项目8768页面点击“重载角色卡和提示词”。不要手改 records/commits。核心身份稳定目前由角色约束与现有提案流程维护，未新增程序级不可修改条目锁。原卡的记忆分类是内容原则，本次没有新增独立的记忆引擎。
