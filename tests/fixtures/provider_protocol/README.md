# 离线协议fixture说明

普通测试只使用FixtureProvider与httpx.MockTransport；从不读取真实API key，也不调用外部付费服务。
- tests/test_gateway.py：限流重试、截断、结构错误、预算、reasoning_content协议字段往返。
- tests/test_protocol_recovery.py：工具调用/结果配对与运行库持久化，完整边界重启续接，协议字段不进入经历。
- tests/integration/test_v1_lifecycle.py：A5/A8/A6/A7脚本输出，验证提案/审阅/原子局部patch，语义质量未验证。
- reports/live_smoke.md：与真实本地向量/Leiden和未运行DeepSeek明确区分。
