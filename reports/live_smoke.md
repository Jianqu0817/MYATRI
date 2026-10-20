# 官方 DeepSeek live 验证

2026-10-20。用户已追加授权：安全保存密钥、调用官方 DeepSeek-V4.1-Flash 进行小规模测试。真实联系人消息/渠道投递/外部部署仍未启用。

## 密钥与模型

密钥通过隐藏输入存入 **Windows Credential Manager**，目标 MYATRI/DeepSeek/api.deepseek.com，仅按需读入当前进程。没有项目内的密钥文件，不写入源码/配置/命令行参数/经历/日志。源码只包含凭据读取代码。当前凭据实际回验成功，实际密钥排除检查见 secret_exclusion.json（源文件、报告、运行目录及发行归档，0匹配；不是整机安全审计）。

GET https://api.deepseek.com/models 实测 HTTP200：id=deepseek-flash、name=DeepSeek-V4.1-Flash、owned_by=deepseek。13次生成响应的model均为deepseek-flash，未切换其它模型或第三方转发。凭据仅可发往官方HTTPS主机，HTTP重定向关闭。

## 实际结果

|项目|结果|范围|
|---|---|---|
|基础生成|通过|真实返回MYATRI_OK|
|JSON mode + Schema|通过|schema传入模型，结果本地验证|
|工具调用/结果往返|通过|lookup_memory只读本地合成记录，调用/结果完整配对|
|thinking + tools|通过|真实返回必要reasoning_content字段并在下一请求回传，未将其作为经历/角色念头|
|真实认知任务链初测|A8格式失败一次|A1/A2/A3/A5实际调用成功；旧A8泛object契约导致模型返回active与不支持字段，程序拒绝写入|
|A8 v2定向恢复|通过|补齐真实TemporaryEntry字段/枚举和v2 prompt，仅重放受影响任务；历史失败保留，新任务成功|
|隔离数据与恢复后完整性|通过|合成材料，archive/source校验0错误，人格仍persona@1；模型可defer，未强制产生念头或人格变化|
|A6/A7真实人格判断/长期效果|未验证|本次合成材料不足以支持真实人格变更；相关路径仍靠离线fixture验结构，不冒充成功|

实时checkpoint与每次用途/用量/耗时/finish_reason见 live_smoke.json；模型可用性见 live_models.json。初始real_cognitive_pipeline失败仍保留；cognitive_pipeline_recovered_v2通过，不能把历史失败删掉伪装初次全通过。A8恢复选择defer、没有新临时条目，属于有效保守决策。

## 用量与开销

共 **13次生成请求，13个HTTP成功响应**；输入6664 tokens，输出1999 tokens。按官方峰值价及返回的cache hit/miss用量保守估算 **USD 0.004247472**（约0.0043美元），不是读取账户的实际扣款；空闲时段实际费用可更低。

本轮运行器最多20次生成、估价上限USD0.10，输出单次最多2048 tokens，不自动重试付费case，异常结果未知时保留费用预留。已完成case不会重复调用。没有启动常驻付费worker，没有联系人消息或部署。

## 本地使用

默认config/defaults.toml仍allow_paid=false，普通offline不会读取凭据。仅本机忽略文件 config/live.local.toml 保存模型/已验证协议开关/小预算，**不含key**。可显式使用：

```powershell
.venv/Scripts/myatri.exe --config config/live.local.toml --root var/atri-live chat --mode live
```

这会真实调用付费API；未运行该常驻命令。key状态：`.venv/Scripts/python.exe -m myatri.credentials status`（不显示值）。轮换时使用隐藏输入store-deepseek；delete-deepseek可移除本机凭据。

Git忽略、sdist显式公开allowlist、wheel配置逐文件allowlist与大小写敏感路径排除均已验证；12项fake sentinel回归覆盖.env/local配置/JSON/YAML/私钥、backup/restore与真实临时wheel/sdist。config/live.local.toml和Windows凭据不会进入项目发行包。跨机器不携带密钥，需新机器自行配置。

官方来源（实施时复查）：
- 模型ID：https://api-docs.deepseek.com/api/list-models/
- 模型/价格：https://api-docs.deepseek.com/quick_start/pricing/
- thinking工具协议：https://api-docs.deepseek.com/guides/thinking_mode/
- 4.1 Flash更新：https://api-docs.deepseek.com/updates/
