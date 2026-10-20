# 认知材料与长原文修复接续记录

2026-10-20，Asia/Shanghai。此记录对应 A06；不代表长期语义/拟人质量验收。

已接续之前中断的补丁，保留其 select_materials 接口与固定 revision 设计。A2/A3/A5/A6/A8 使用有限材料、原文摘录区间、候选数量/省略数量与局限；请求包含 schema、指令、元数据一起计入默认 16000 预算，超出时继续减材料。A6 必须完整看到当前人格与必要反例检索记录；A7 必须完整看到提案引用的全部材料，否则本地 defer，scope_ok/counterexamples_checked 均 false，不调用模型制造 accept。

A1 将原文按最多 3600 UTF-8 bytes、300 bytes 重叠窗口送入抽取，每轮最多新增 8 个窗口。每个成功窗口持久保存固定 message@revision、绝对 start/end、输出、候选来源和模型信息。中断/重启只继续尚无 checkpoint 的窗口。未全部完成时抛出 reason=ingest_pending 的 IngestProgressPending，不写 A1 完成记录或伪造完整处理；全部窗口完成后才提交事件提案。原文始终保留，source_coverage.complete 仅表示全文已提交抽取，不表示模型穷尽全文语义。

引用逐字核验并转为原文绝对字符区间。同一重叠区间去重不依赖模型 event_key；模型键本身也不再充当跨消息全局事件身份。跨消息语义合并必须显式引用本轮展示的 existing_event_ref。离线字面 fixture 保留其透明的相同文本重复规则。此修改更保守，候选未命中的语义重复仍可能产生两个待后续检查的事件，不能为消除重复而无证据合并不同时刻的经历。

补充修正：A1 预算缩减后的 selected_refs/partial_refs/omitted_count 与实际展示同步；IngestProgressPending 与运行时短延迟续批原因对齐；集成脚本 fixture 兼容 {materials, selection} 输入。归因、app、gateway 与公共契约由主代理/其他代理负责，此代理未改。

已验证：最终 **17 passed，19.52s**，覆盖 28/96 事件候选下 A1/A2/A3/A5/A6/A8 均进入 provider、请求在默认 16000 完整预算内，A8 generated_idea 正面提案并提交，A7 缺完整必需证据本地 defer，以及原生命周期、重启续批、重叠去重、碰撞键不误合并与显式候选重提。命令：`.venv/Scripts/python.exe -m pytest -q tests/test_cognitive_materials.py tests/test_experience.py tests/test_temporary_schema.py tests/integration/test_v1_lifecycle.py --tb=short --basetemp=reports/fix_cognition_final_tmp_v3 --junitxml=reports/fix_cognition_2026-10-20.xml`。所有测试用独立 reports 合成目录，没有读取实际运行库、密钥、调用外部 API 或安装依赖。

边界：候选目前采用可解释的字符相关性/近期性与有限反例预留，未证明语义最优；本地仍读取候选/档案元数据，长期规模下的 CPU/文件数开销另需实测。长于重叠区间的跨窗口依赖、模型未抽取的事件、身份消歧均不能由结构测试证明已解决。超大完整人格/审查提案允许 defer，需缩小提案后再审，不以提高上限替代有限注意。
