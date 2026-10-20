# A-MEM 局部源码移植记录

2026-10-20。负责范围：`src/myatri/_vendor/amem.py`、`src/myatri/memory/graph.py`、`tests/test_upstream_amem.py` 及本记录。没有修改公共清单或依赖，没有调用模型、读取凭据或派生代理。

## 已核对来源

仓库 `agiresearch/A-mem`，实际 checkout HEAD 为 `ceffb860f0712bbae97b184d440df62bc910ca8d`。读取三个核心文件及 `tests/test_memory_system.py`、`test_retriever.py`、`test_utils.py`、`conftest.py`。用实际文件 UTF-8 `splitlines()` 计数：

|核心文件|实际物理行数|
|---|---:|
|`agentic_memory/memory_system.py`|727|
|`agentic_memory/retrievers.py`|303|
|`agentic_memory/llm_controller.py`|97|

原许可证 MIT，Copyright (c) 2025 AGI Research。移植文件头记录仓库、固定提交、文件、原函数/范围、许可证及改动；原始许可证由主代理统一放到 `LICENSES/upstream/A-MEM-LICENSE` 并接入发行包。

## 候选判断与排除

未发现可以原样替换本地 A1/A2/网关/检索完整模块的行为等价代码。`analyze_content` 只生成 keywords/context/tags，且上游 `add_note` 不调用它；本地 A1 抽取带原文 span、现实范围和版本来源的事件，不能为复用额外接入另一轮分析。`process_memory` 的 strengthen/update_neighbor 不是本地有证据类型边和原子提案，不能沿用直接修改旧邻居 context/tags。

排除上游初始化 `client.reset()`（memory_system.py:109-117）、可变 MemoryNote/CRUD、Chroma 与自动 SentenceTransformer 初始化、字符串 metadata 推断转换和同步 OpenAI/Ollama 控制器；它们与本地权威档案、embedding space/revision、异步网关/额度契约不等价。还观察到 `process_memory` 使用查询排名索引定位插入顺序内存表（687-716），不能复制这一行为。

## 实际移植及生产接入

来源是 `AgenticMemorySystem.search_agentic` 的 linked-memory bounded deduplication 段（memory_system.py:554-583）；实际提取其计数、seen-ID 去重、受限追加机制。适配为 `iter_unique_neighbors(candidates, seen_ids, k)`，接入 `MemoryGraph.get_subgraph()`；`RecallService.recall()` 的现有类型图扩展在 retrieval/service.py:200 实际调用这一生产路径。

这是一个很小的局部改编，不能称为完整 A-MEM 记忆系统接入。此前工作消息称“约9行内核”；当前真实 vendor 函数为 amem.py:18-25，共 **8个物理行**（含1行 docstring，7行代码），没有为凑行数添加功能。文件总计25行，包括来源说明。

MYATRI 仍按原 edge-first 顺序产生候选，保留默认/显式类型过滤、双向遍历、深度、数量上限、路径和全部 incident-edge 输出（包括重复边、自环两次触达）。适配内核接收有序 `(origin, target)`，不依赖 MemoryNote；额度用尽后仍消耗候选以保留原 incident-edge 行为。路径及下一层 frontier 由原调用方持有，不复制全量邻接表。

上游完整函数最后 `return memories[:k]`（585）会在seed已满k时截掉新增邻居；此行不移植。也不复制内存 mutation、Chroma 或任何模型调用。移植只保证本地原遍历契约兼容，不能宣传获得完整 A-MEM 演化或性能提升。

## 验证

新增测试以冻结的移植前 BFS 作完整输出对照，覆盖多 seed、重复 seed、反向边、自环/循环、重复边、tight/负 limit、多个 depth、默认/空/显式/未知类型及120张确定性随机图。单独检查新增邻居不会被上游截断缺陷抹掉、耗尽额度后仍消费 incident candidates；真实 ArchiveStore + RecallService 场景核验生产调用、关联目标、类型路径和原文来源。

命令：`.venv/Scripts/python.exe -m pytest -q tests/test_upstream_amem.py tests/test_memory.py tests/test_retrieval.py tests/test_memory_consistency.py --tb=short --basetemp=reports/amem_reuse_test_tmp_20261020 --junitxml=reports/amem_reuse_regression.xml`。

已读取完整 XML：**35 passed，12.718秒，0 failures/errors/skipped**（含4项新移植测试）。没有执行上游依赖真实 OpenAI/模型下载的测试，也没有将本地兼容回归当作上游完整项目验收。尚需主代理统一许可证/manifest/打包和总回归。
