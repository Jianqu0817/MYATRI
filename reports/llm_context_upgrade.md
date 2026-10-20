# 语义压缩与临时状态激活升级

2026-10-20；用户指定建议2/3，实际修改生产代码，不是新增DeepSeek开发子Agent。主 Agent负责接口、压缩、集成、配置与验收；复用memory子Agent负责activation.py及18项专项，不递归委派。

## 实际改变

- 前台实际await异步语义选择；候选先用便宜算法排序，再由LLM判断，包含零词面命中的候选，支持选空/矛盾共存。返回仅ref和理由，程序控制状态、版本、数量和预算。await期间撤回/改版不注入，激活trace有模型信息和CAS。
- 手动/自动会话压缩通过LLM提取重要要点，每条有本批原文的逐字证据，程序算字符区间。摘要为模型转述，原文/preserve保留，重启可回查。材料未变的有效语义摘要可复用，避免重复请求。
- 引入compaction/v1、activation/v1版本prompt；context配置两开关缺省true。API是否可付费仍由显式live和原paid gate决定，不把key写文件。
- 自动压缩、交互/compact、CLI compact --mode live、context --mode live均接通。原同步接口仍为离线基线。旧source-excerpts摘要兼容；模型错误/defer/离线均明确降级。
- 模型准备上下文使用foreground配额，避免等后台长反思；usage仍记录各自role。失效摘要从独立摘要区与回忆区同时过滤，回忆投影保留Event.reality_scope等关键标记。

## 验证

`.venv/Scripts/python.exe -m pytest -q --junitxml=reports/pytest_results.xml` → **116 passed，49.64s**。新增36项离线用例（18 activation +18 context），包括无词面同义选择、空选择/非法ref/预算/超时/defer/禁用、等待期间撤回/改版与CAS、重启trace、160字符后的约定、原文分批/未知证据拒绝、人格变动时摘要拒绝、生产聊天与自动压缩入口、旧summary回忆旁路、官方HTTP适配schema（模拟传输）、前后台通道独立。

`.venv/Scripts/python.exe scripts/live_context_smoke.py` → **2次官方deepseek-flash请求，两项passed**：

- activation/v1确实选择了合成日程意图，method=llm。
- compaction/v1实际生成agreement和uncertainty要点；保留合成约定原文，逐字来源校验通过。
- prompt1003/completion239 tokens；按配置峰值估算USD0.0005877，非账户实际扣款。无重试，限制2次/USD0.03保守预留；报告存在时脚本不重复调用。
- 档案校验0错误，人格/临时状态版本不变；无事件根/行为反馈伪造，无常驻worker、真实联系人消息或部署。此前13次官方请求独立保留，新2次累计已记录15次，不是账号全部用量统计。

完整live逐请求用量和来源在live_context_smoke.json；使用var/live-context-smoke-20261020纯合成目录，不当真实角色库。普通pytest无网络、不读真实key；HTTP mock不是live证据。

## 使用与限制

正常live聊天会使用两项能力；有open状态时多一次语义选择，触发压缩时按批增加调用。独立手动语义压缩：

```powershell
.\.venv\Scripts\myatri.exe --config config/live.local.toml --root var/atri-live compact --mode live
```

禁用某项可在本机配置添加[context] llm_compaction=false或llm_activation=false。有效缓存可继续读取；禁用阻止新的相应API请求。默认离线Fixture会defer，清楚标记来源摘录/启发式回退。

当前有界处理：激活12候选/6000B材料，情境2048B，默认最多4条/600B正文；压缩9000B原文分批/最多8批，过大或失败回退摘录，不伪称语义成功。语义摘要上下文投影另限5000B，省略的来源ref明确保留。没有增量语义缓存、没有证明每个转述语义必然正确，完整原文仍为权威。

原evaluation.md是历史词面/图与启发式激活基线，没有用同一批标签反复调参，也不是本次LLM升级效果评估。A6/A7真实人格语义及长期连续性仍待验；component_review中M01/M02、行动反馈集成等仍开放。
