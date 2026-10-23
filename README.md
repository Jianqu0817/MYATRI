# MYATRI · 本地持续记忆与角色运行时

MYATRI 是以本地档案为基础、使用 DeepSeek 生成回复的持续角色运行时。当前 **0.3.0** 提供完整命令行聊天：小温暖角色卡、近期上下文、来源可追溯的长期记忆、PAD 情绪、后台维护、联网搜索、Harness 电脑执行 Agent，以及本机监视窗口。

**无需安装或连接微信、AstrBot。** 本指南面向 Windows 10/11 x64，核对日期 **2026-10-23**。聊天数据默认保存在本机；真实模型回复需要网络和付费 API，不是离线大模型。

> **本机已经配置过？** 双击 `启动小温暖.cmd` 即可继续原记忆。换入口或删除 `var/` 会导致用到不同的库；升级时不需要重新初始化已有档案。

## 目录

- [与 AstrBot 版的关系](#与-astrbot-版的关系)
- [首次部署](#首次部署)
- [日常使用](#日常使用)
- [窗口与配置](#窗口与配置)
- [联网搜索](#联网搜索)
- [安装电脑执行 Agent](#安装电脑执行-agent)
- [记忆情绪与自动维护](#记忆情绪与自动维护)
- [Token预算与费用](#token预算与费用)
- [可选本地嵌入模型](#可选本地嵌入模型)
- [常见问题](#常见问题)
- [更新备份与迁移](#更新备份与迁移)
- [开发与维护](#开发与维护)

## 与 AstrBot 版的关系

| 项目 | 用途 | 默认运行数据 |
| --- | --- | --- |
| 本仓库 MYATRI | 独立终端聊天与内核开发 | `var/xiaowennuan/` 或明确指定的 root |
| [MYATRI-AstrBot](https://github.com/Jianqu0817/MYATRI-AstrBot) | 微信群聊，也能停止群聊后在终端延续原群库 | 另一个仓库的 `var/groups/` |

同步的是可移植实现，不自动复制群记录、私人记忆、身份和本机配置。两个仓库的同名角色不意味着共用一份记忆。同一 Windows 用户可复用凭据管理器中的 DeepSeek Key，但各项目的预算账本也不会自动合并。

如果要“暂时关闭群聊、直接在终端接着同一群上下文聊”，请用 **AstrBot 仓库的 `Start-Local-Chat.cmd`**；本仓库独立启动不会自动读取那个群库。

## 首次部署

### 1. 安装前置工具

- Windows 10/11 x64：完整双击启动、凭据管理器和电脑执行方案以此为部署目标。
- Git：`git --version` 可用。
- uv：`uv --version` 可用，用于安装 Python 和锁定依赖。
- Python **3.12**：项目要求 `>=3.12,<3.13`，可由 uv 自动安装。
- 真实聊天需 DeepSeek API Key、账户额度和可访问接口的网络。
- Node、pnpm、微信、AstrBot 均**不是基础聊天必需组件**。

按 [uv 官方文档](https://docs.astral.sh/uv/getting-started/installation/) 安装 uv：

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

然后重开 PowerShell。以下命令从项目根目录执行；使用 PowerShell，不要将命令直接粘到聊天输入框。

### 2. 克隆并安装锁定环境

```powershell
git clone https://github.com/Jianqu0817/MYATRI.git
Set-Location MYATRI
uv python install 3.12
uv sync --frozen --extra neural
```

首次需要下载 Python/依赖，耗时取决于网络。无需激活虚拟环境，后文直接调用 `.venv\Scripts\python.exe`。

仓库包含源码、角色卡、配置模板和锁文件，**不包含** Key、个人档案、运行库、模型权重和已安装的 Harness。克隆不会恢复另一台电脑的记忆。

### 3. 先做不调用 API 的演示（可选）

```powershell
.\.venv\Scripts\python.exe -m myatri.interfaces.cli --root var/demo companion --mode offline --message "你好" --no-ui
```

使用独立 `var/demo`，不混入正式小温暖库。`offline` 为固定测试模型，用于确认程序流程，不代表真实角色质量或本地大模型能力。这条命令不调用 DeepSeek，不要求微信。

### 4. 保存 DeepSeek Key

```powershell
.\.venv\Scripts\python.exe -m myatri.credentials store-deepseek
```

按提示隐藏输入并回车，保存到当前 Windows 用户凭据管理器，目标为 `MYATRI/DeepSeek/api.deepseek.com`。不写入项目、不在命令行参数传 Key。另一仓库已在同一用户下保存过时可复用。

该命令仅保存凭据，不调用模型；首次正常双击启动也会在缺少 Key 时提示隐藏输入。

### 5. 启动真实聊天

双击 **`启动小温暖.cmd`**。程序会：

1. 检查锁定依赖。
2. 缺少时从公开模板生成 `config/cli-engine.local.toml`，启用真实聊天；已有文件保留。
3. 初始化或检查 `var/xiaowennuan/`，保留既有档案，运行完整性检查。
4. 加载角色卡并进入 `companion --mode live`；启动监视与控制界面。

看到输入提示后聊天，输入 `/quit` 退出。**正常双击使用付费 API，后台摘要、情绪评价和维护也可能调用模型。**

只检查准备情况：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/start_myatri.ps1 -Character xiaowennuan -CheckOnly
```

`CheckOnly` 不调用模型、不停止当前聊天，但可能首次创建私有配置/角色库；并非完全只读。缺少 Key 会提示失败，可先执行第 4 步。

## 日常使用

### 入口与记忆库

| 入口 | 默认库 | 说明 |
| --- | --- | --- |
| `启动小温暖.cmd` | `var/xiaowennuan/` | 推荐日常入口，内部 agent 仍为 `atri` |
| `启动MYATRI.cmd` | `var/myatri-main/` | 另一份独立记忆，不会自动读取小温暖库 |
| 手动 `companion` | `--root` 指定 | 必须显式指定原 root/agent 才能延续原档案 |
| 旧 `chat` 子命令 | `--root` 指定 | 兼容旧接口，不含完整 companion 渠道能力 |

两个双击入口当前均进入完整 CLI；默认 companion 角色模板为小温暖，不能单凭文件名把 `启动MYATRI.cmd` 理解为旧版 ATRI 角色。首次升级加载磁盘卡时，会在原档案中形成新人格版本，旧版本保留。

正常双击会尝试替换**本项目的旧 CLI 服务**。同一库不要并发启动多个聊天写入者；两个不同库若使用相同 UI 端口，也会冲突。退出用 `/quit` 或 Ctrl+C，等待程序收尾。

手动指定私有配置与原库：

```powershell
.\.venv\Scripts\python.exe -m myatri.interfaces.cli --root var/xiaowennuan --agent atri --config config/cli-engine.local.toml companion --mode live
```

全局参数 `--root`、`--agent`、`--config` 放在子命令 `companion` **前面**。不要漏写 root，否则底层 CLI 默认是另一目录 `var/atri`。

### 聊天内命令

| 命令 | 用途 |
| --- | --- |
| `/quit` | 正常退出并保留已有记忆 |
| `/reload` | 重载磁盘角色卡/提示词，更新运行人格 |
| `/clear` | 清空工作上下文，不删除长期记忆 |
| `/context` | 查看当前上下文统计 |
| `/memory 关键词` | 本地检索原库记忆 |
| `/retry-memory` | 对摘要/记忆任务进行有限恢复 |
| `/compact` | 压缩上下文，live 时可能调用模型 |
| `/pc 任务 目标` | 已启用电脑 Agent 时发起执行 |

`/clear` 不是“彻底忘记”，旧长期条目以后仍可能被检索。不要把失败回合当作成功执行；根据终端错误和任务回执排查，避免重复提交有副作用的电脑任务。

## 窗口与配置

聊天运行后，可打开：

| 地址 | 功能 |
| --- | --- |
| `127.0.0.1:8776` | 本机控制 API，带 Bearer 鉴权 |
| <http://127.0.0.1:8777/> | 运行监视、今日 Token、记忆/情绪与维护状态 |
| <http://127.0.0.1:8778/> | 实际请求与上下文、重载/清窗等控制 |

`Monitor-Context.cmd` 与 `View-Context.cmd` **只打开浏览器**，不启动服务器。先运行完整 companion；使用 `--no-ui` 时不会启动这些界面。端口与 AstrBot 仓库的 8766—8768 不同。

| 文件 | 用途 |
| --- | --- |
| `config/cli-engine.toml` | 公开配置模板，`allow_paid=false` |
| `config/cli-engine.local.toml` | 双击入口使用的私有配置；首次生成后保留 |
| `config/personas/xiaowennuan/persona.md` | 当前小温暖角色卡模板 |
| `config/cli.local.toml` | 运行时生成的界面路由配置，不是模型主配置 |
| `var/cli-token.txt` | 本机界面令牌 |
| `config/harness/executor.local.json` | 电脑 Agent 本机 skills/MCP 扩展 |

手动 companion 不带 `--config` 时依次选择本机私有 CLI 配置、公开 CLI 配置等默认来源；配置按所选文件读取，不是把所有文件逐层合并。部署时建议显式指定。修改配置通常需正常重启；修改角色卡后用 `/reload`，只改 Markdown 不等于运行人格已变化。

默认 `[companion].capture_requests=true`；实际采集包含发给模型的角色卡/上下文。需要关闭时在私有配置的现有表内修改，再重启。查看器不能补采关闭期间的旧请求。

所有端口默认只在本机回环使用，不要直接开放到公网。

## 联网搜索

不需要安装电脑 Harness。编辑 `config/cli-engine.local.toml` 已有表：

```toml
[companion.web]
enabled = true
backend = "deepseek-api"
timeout_seconds = 25
max_results = 3
daily_limit = 40
cache_ttl_hours = 24
```

重启后可说“查一下网上……”。直接调用 `https://api.deepseek.com/v1/tools/search`，复用模型凭据，只传检索参数。接口需要对账户可用，权限/限额按真实返回处理；默认 40 次/日与 24 小时缓存。

搜索次数额度不等于聊天 Token 硬预算，费用以供应商账单为准。公开模板默认关闭联网；有旧本机配置时检查其原后端和路径，不自动覆盖。

## 安装电脑执行 Agent

### 1. 明确本机 owner

先正常启动或检查一次，生成 `config/cli-engine.local.toml`。编辑其中 `[companion]`：

```toml
owner_id = "local-owner"
owner_name = "菅蘧"
```

这是独立本机终端身份，沿用原稳定 ID 即可，不需要虚构微信 ID。已有身份不要随意更换；电脑表中的 owner 必须相同。名字字段需为菅蘧，真正授权使用稳定 ID。

终端是可信本机入口，能够操作此终端的人也能使用该 owner；名称不是密码。

### 2. 安装 Harness

准备 Node.js **22 x64，至少 22.19**，确认 `node --version`、`npm --version` 正常。使用 JavaScript 版 pnpm 10，参见 [pnpm 安装说明](https://pnpm.io/installation)；安装脚本需要 JS 入口，不能传 `pnpm.exe` 或 `pnpm.cmd`。

```powershell
npm install --prefix "var/harness-bootstrap" pnpm@10
$harnessNode = (Get-Command node.exe).Source
$harnessPnpm = (Resolve-Path "var/harness-bootstrap/node_modules/pnpm/bin/pnpm.cjs").Path
.\.venv\Scripts\python.exe scripts/setup_computer_control.py --node "$harnessNode" --pnpm-js "$harnessPnpm" --full
```

按仓库锁文件安装 DSH **0.2.1-rc.2** 到 `var/harness/`，绑定现有 owner、启用 full Agent，做不调用模型的组合探测。下载依赖需要网络；不自动启动聊天，也不自动执行真实任务。

需要 skills/MCP 时，首次创建：

```powershell
Copy-Item config/harness/executor.example.json config/harness/executor.local.json
```

已有文件不覆盖。正常重启聊天加载新设置。基础 PowerShell、文件等工具不要求额外 MCP。

### 3. 调用和报告

```text
/pc 任务 查询本机内存总量和可用内存，只读取
/pc 任务 检查 Python、Git、Node 的版本并整理
/pc 状态 完整任务ID
/pc 暂停 完整任务ID
/pc 继续 完整任务ID
/pc 取消 完整任务ID
```

也支持绑定 owner 的自然语言电脑请求。主小温暖生成 instructions，子 Agent 执行 Harness；实际结果通过原工具调用返回原聊天回合，由小温暖生成终端最终报告。不会把“已入队”当作任务完成。

`full` 可使用 PowerShell、文件读写/编辑/搜索、后台任务、skills 和已配置 MCP，在当前 Windows 账户权限内工作，**不是文件沙箱，也不自动取得管理员权限**。点击桌面、截图、外部设备等仍取决于实际工具接入。

任务检查点保存在原库，集成模型调用共用原预算；重启恢复原任务/原工具回合，执行结果不明时不自动重做。受阻看真实回执、缺失条件与 `chat_report`，不要反复新建同一任务。`Harness.cmd` 独立 CLI 不等同于聊天任务，其调用不应被假定全部纳入本项目账本。

## 记忆情绪与自动维护

本地原始档案/版本化记录是依据，索引是可重建的检索层；检索到一句话不等于已证实事实。

- 近期监听、确认对话、摘要和长期条目分别处理，原始出处与人物身份保留。
- 身份不明、支持不足、校验失败的候选隔离；合格条目可独立推进，不把整批错误当真。
- PAD 情绪与较慢变化的心境会衰减；长期人格更新与临时情绪分开保存。
- 默认每 50 个完成往返触发一批维护，深度/人格维护按批次安排；不是每句都立即产生长期记忆。
- `[companion.recovery].enabled=true` 默认启用有限恢复，恢复有预算与重试边界，保留原文/历史失败，不等于把告警数归零。
- 主动发言公开模板默认关闭、影子模式开启。启用前检查 `[companion.proactive]`；这里只向当前终端展示，不提供微信/邮件外发。`[outreach].enabled` 保持关闭，双击入口会拒绝旧的外发配置。
- 电脑任务最终结果回传不依赖主动闲聊开关。

运行库中的 `runtime.sqlite3` 不只是可删缓存，还含任务、协议、账本等状态；`<root>/cli-runtime/` 保存渠道侧上下文/维护资料。备份应完整保留 root，不能仅留向量库。

## Token预算与费用

当前公开默认值：

| 项目 | 默认值 |
| --- | --- |
| 每日模型额度 | **50,000,000 Token** |
| 单请求上下文预算 | 1,000,000 |
| 压缩阈值 | 650,000 |
| 工作上下文窗口 | 200,000 |
| 对话/近期消息选材上限 | 80 组往返 / 100 条消息 |
| 模型 | `deepseek-flash`，以实际账户可用性为准 |
| 思考 | 开启，`reasoning_effort="low"`，组合上限 8192，超时 120 秒 |

容量参数是限制，不是每轮必填长度。模型、能力与价格随供应商变化；改模型时要核对思考参数和实际上下文能力。

主回复、后台摘要/情绪/维护及集成电脑 Agent 都可能计费。监视页“今日 Token”取本地账本，不等于整个账户账单，不自动合并 AstrBot 库、独立 CLI 和搜索；估价价格默认 0 表示未配置，不代表 API 免费。

如需调整，在私有配置中修改已有 `[budget]` / `[chat]` / `[context]`，保留价格依据，正常重启。不要删除账本绕过限制。

## 可选本地嵌入模型

没有模型权重也能启动：默认 `embedding.backend="auto"` 在缺少已核验 BGE 时退回本地 TF-IDF。依赖 `--extra neural` 与模型权重是两回事；聊天不会暗中自动下载权重。

需要 BGE 时显式执行：

```powershell
uv sync --frozen --extra neural
.\.venv\Scripts\python.exe -m myatri.interfaces.cli models download --path var/models/bge-small-zh-v1.5
.\.venv\Scripts\python.exe -m myatri.interfaces.cli --root var/xiaowennuan --agent atri memory rebuild-index --space bge --model-path var/models/bge-small-zh-v1.5
```

下载需要网络，重建会写入选定库的新索引。与正在使用同一库的聊天错开执行；不需要 GPU。只想最低部署可跳过整个部分。

## 常见问题

| 现象 | 处理 |
| --- | --- |
| 找不到 uv | 安装后重开终端，确认 PATH；默认安装也可能位于用户 `.local/bin` |
| Python 版本错误 | 使用 `uv python install 3.12` 与项目锁文件，不沿用其他项目的 venv |
| 依赖下载失败 | 修复网络后重跑 sync；不要删除正式记忆库 |
| Key 缺失/无效、401 | 执行隐藏凭据保存命令；确认当前 Windows 用户、真实 Key 与供应商返回 |
| 429/余额不足 | 依据供应商错误处理额度/限流，不通过反复重启增加重试 |
| 付费/能力配置错误 | 核对所选配置、供应商能力与运行模式；完整 companion 的显式 live 会启用真实模型，旧 chat/worker 还会检查付费配置 |
| 不认识以前的事 | 先核对启动器打印的绝对记忆目录与 agent；两个入口不是同库 |
| 双击检查通过却没聊天 | 使用了 CheckOnly；正常双击不加该选项 |
| 浏览器连接拒绝 | 先启动完整 companion，检查是否 `--no-ui`、端口冲突或进程退出 |
| 改角色卡没生效 | 输入 `/reload`，核对实际加载文件与人格版本 |
| 清窗后仍记得旧事 | `/clear` 只清工作上下文，长期记忆仍保留 |
| BGE 不存在 | auto 会用 TF-IDF；强制 bge 则需显式下载核验模型 |
| 告警仍有失败/隔离 | 查看具体任务与来源；有限恢复不抹除历史，不能手删记录“修复” |
| 电脑任务说无权限 | 核对 companion owner、电脑 owner、enabled/agent_enabled 和 live 模式 |
| 任务执行后无最终报告 | 查看任务回执/同轮续接状态，正常重启加载当前代码；不要重复执行 |
| 完整性检查失败 | 先保留全库备份，运行 doctor 看具体问题，避免删除 SQLite 或原始记录 |
| 有锁/端口占用 | 退出原窗口，等待收尾；不要删除锁强开同库 |

最低诊断命令：

```powershell
.\.venv\Scripts\python.exe -m myatri.interfaces.cli --root var/xiaowennuan --agent atri doctor
.\.venv\Scripts\python.exe -m myatri.interfaces.cli --root var/xiaowennuan --agent atri cost inspect
.\.venv\Scripts\python.exe -m myatri.interfaces.cli --root var/xiaowennuan --agent atri emotion show
```

`doctor` 检查结构与完整性，不证明长期记忆语义质量或付费模型可用。对外发日志/实际请求前去掉对话、Key、令牌和个人信息。

## 更新备份与迁移

### 更新

退出 CLI 后备份，然后：

```powershell
git status --short
git pull --ff-only
uv sync --frozen --extra neural
```

有自己的已跟踪修改时先保留并解决，不用 `reset --hard` 清理。随后打开原来的启动器，使用原库。私有配置不会被模板覆盖，新功能默认值需要和公开模板对照核对。不要同时更换 root、agent 和角色卡来测试升级。

### 备份与恢复

最直接的备份：**正常退出后完整复制当前 root**（如 `var/xiaowennuan/`），另备份角色卡、私有配置、Harness 本机配置与需要保留的工具资料。备份放仓库外，不上传个人档案到 GitHub。

也可使用内核档案备份命令：

```powershell
New-Item -ItemType Directory -Force -Path "D:/MYATRI-backups" | Out-Null
.\.venv\Scripts\python.exe -m myatri.interfaces.cli --root var/xiaowennuan --agent atri backup --output D:/MYATRI-backups/xiaowennuan.zip
.\.venv\Scripts\python.exe -m myatri.interfaces.cli restore --input D:/MYATRI-backups/xiaowennuan.zip --target var/restored-xiaowennuan
```

恢复目标必须是**尚不存在的新目录**，不覆盖正式库。内置 ZIP 备份单独保存根 `runtime.sqlite3`，其他 SQLite 会被过滤，因此不能代替完整 CLI 渠道状态的冷备份；要完整延续上下文/任务，优先停机复制整个 root。私有配置/工具资料另备份，重复备份使用新文件名。

换电脑后重新 `uv sync`，复制完整运行库并显式使用原 root/agent，修正绝对路径，重新安装 Harness；Windows 凭据不能靠复制项目迁移，需在新用户下重新保存 Key。保留原机器备份直至确认恢复。

## 开发与维护

代码：`src/myatri/`；完整渠道：`src/myatri/companion/`；配置/提示词：`config/`；启动与安装：`scripts/`；定向验证：`tests/`。

接手先读：

- [项目总览与 Agent 维护指南](docs/项目总览与Agent维护指南.md)
- [当前状态](docs/progress/STATUS.md) 与 [接续说明](docs/progress/HANDOFF.md)
- [CLI 迁移说明](docs/CLI迁移_2026-10-22.md)
- [Harness 结果回传移植](docs/Harness结果回传移植_2026-10-22.md)
- [通用执行与双仓边界](docs/Harness通用执行与双仓迁移_2026-10-22.md)

原始记录/版本化档案是权威来源，索引可重建；不要手改记录或以相似度当支持证据。开发使用锁定环境，按实际改动跑定向测试。文档更新检查链接、命令入口和 diff 即可，不需要付费模型调用或生产重启。

本仓库未把所有构想都实现为工具：桌面视觉/设备、额外 skills/MCP 必须有实际配置；自动维护机制通过不代表长期人格与记忆效果已完成实证。第三方依赖及引用的资源按各自许可使用，来源与实现边界见维护文档和仓库内 `LICENSES/`。
