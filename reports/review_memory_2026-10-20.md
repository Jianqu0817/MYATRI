# 存储、记忆与检索独立审查（2026-10-20）

范围：阅读 `docs/01_工程规划书.md`、`docs/04_动态索引与技能记忆设计.md`、ADR 0003、`reports/component_review.md` 和相关生产代码/测试；生产代码只读。未访问真实 `var` 数据、凭据或外部 API，未安装依赖。新探针使用 `reports` 下自动清理的临时目录和离线 FixtureProvider。

## 结果

### 新发现 R-MEM-03 / P1：合法历史证据被当成缺失，临时状态更新可持续阻断索引重建

- 根因位置：`D:\DS_workspace\MYATRI\src\myatri\memory\index.py:58-59,119-120`，`D:\DS_workspace\MYATRI\src\myatri\memory\graph.py:66-67`。
- 生产触发路径：`app.py:121-122` 把当前临时状态加入 A2 材料；`cognition/association.py:29-34` 允许边的 evidence_refs 引用材料中的状态。设端点是不可变事件 `a@1/b@1`，证据还含 `thought@1`。A2 提案合法提交并成功建立索引后，正常调用 `TemporaryStates.review` 生成 `thought@2`。
- `list_records` 只返回最新修订，因此新的 record_map 不含 `thought@1`；图校验将仍可从同一快照精确读取的历史证据当作不存在，抛出 `ValueError: Semantic edges require existing evidence`。端点仍可见，所以这条边不会被前面的端点过滤排除。
- 影响：该边保留在权威档案，之后每次 `index.update/rebuild` 都会遇到同一异常；新事件仍可持久保存并词面回退，但全局索引持续停留在旧水位。需要区分“当前投影成员”和“快照内可读取的历史证据”。这不是旧档案损坏，也不需要恶意输入；出现概率取决于 A2 是否选用状态作为证据。
- 本轮用真实 `AssociationAgent + Gateway(FixtureProvider) + Committer + TemporaryStates.review` 复现，离线输出：

```text
accepted_A2_evidence= ['a@1', 'b@1', 'thought@1']
historical_evidence_still_exists= thought@1 latest_state= thought@2
index_update_exception= ValueError Semantic edges require existing evidence
archive_integrity= []
watermark_stuck= True
```

可复制的核心探针（在项目虚拟环境运行，所有语义输出为显式合成测试数据）：

```python
import asyncio, json, tempfile
from pathlib import Path
from myatri.contracts import Edge, Event, Record, SourceSpan, TemporaryEntry
from myatri.storage import ArchiveStore
from myatri.memory import MemoryIndex
from myatri.persona.temporary import TemporaryStates
from myatri.cognition.association import AssociationAgent
from myatri.providers import FixtureProvider, Gateway
from myatri.runtime.commit import Committer

def event(store, name, text):
    raw = store.append_message('user', text, 'raw_' + name)
    payload = Event(fact_summary=text, source_spans=[SourceSpan(
        message_ref=raw.ref, start=0, end=len(text), quote=text)],
        event_fingerprint=name)
    row = Record(record_id=name, record_kind='event', source_refs=[raw.ref],
                 body_markdown=text, payload=payload.model_dump())
    store.commit([row], name)
    return row

async def run(directory):
    store = ArchiveStore(Path(directory))
    a = event(store, 'a', '一起约好周末散步')
    b = event(store, 'b', '后来对方取消周末散步')
    states = TemporaryStates(store)
    thought = states.create(TemporaryEntry(text='这次取消令人失落',
        origin_refs=[a.ref, b.ref]), entry_id='thought')
    edge = Edge(edge_id='event_relation', from_ref=a.ref, to_ref=b.ref,
        type='contradicts', evidence_refs=[a.ref, b.ref, thought.ref])
    provider = FixtureProvider([{'content': json.dumps({'decision': 'propose',
        'reason': 'synthetic schema-valid test', 'edges': [edge.model_dump()]})}])
    index = MemoryIndex(store)
    await index.rebuild()
    proposal = await AssociationAgent(store, Gateway(provider), index).propose(
        [a.ref, b.ref, thought.ref])
    Committer(store).submit_proposal(proposal)
    await index.update()  # succeeds
    states.review('thought', base_revision=1, status='settled', reason='已有理解')
    assert store.get_record('thought', 1).ref == 'thought@1'
    assert store.verify_archive() == []
    await index.update()  # raises ValueError in graph.py:67

with tempfile.TemporaryDirectory(dir='reports', prefix='review_memory_revision_') as d:
    asyncio.run(run(d))
```

### 新发现 R-MEM-04 / P2：文本中的非法日期使普通聊天直接失败

- 位置：`D:\DS_workspace\MYATRI\src\myatri\retrieval\service.py:73-76`；前台入口 `D:\DS_workspace\MYATRI\src\myatri\conversation\context.py:27`。
- 日期正则接受 `2026-13-40`、`2026-02-30` 等字符串，直接构造 datetime，未处理 ValueError。ContextBuilder 首轮组装调用 recall，不在工具参数的异常处理区内。
- 已实际调用 `Application(temp_directory, mode='offline').conversation.respond('我想查询2026-13-40那天的事情', message_id='invalid_date_turn')`：抛出 `ValueError: month must be in 1..12`，用户原文已保存，assistant 消息数为 0。
- CLI 交互循环 `interfaces/cli.py:120` 只捕获 ProviderError；ValueError 进入最外层 `:199` 后退出程序，不能在同一交互循环继续输入。
- 建议：只有成功解析的日历日期才转为结构化过滤；无效日期按普通查询处理或返回明确可恢复错误，不能让整轮上下文构建异常退出。

完整前台探针与实际输出：

```python
import asyncio, tempfile
from myatri.app import Application

async def run(directory):
    app = Application(directory, mode='offline')
    try:
        await app.conversation.respond('我想查询2026-13-40那天的事情',
                                       message_id='invalid_date_turn')
    except Exception as error:
        print('respond_exception=', type(error).__name__, str(error))
    print('stored_user=', app.store.get_record('invalid_date_turn').payload['role'])
    print('assistant_messages=', len([r for r in app.store.list_records('raw_message')
                                     if r.payload['role'] == 'assistant']))

with tempfile.TemporaryDirectory(dir='reports', prefix='review_memory_chat_') as d:
    asyncio.run(run(d))
```

```text
respond_exception= ValueError month must be in 1..12
stored_user= user
assistant_messages= 0
```

### 设计建议 R-MEM-05：先明确有效期/状态语义，再接通当前图与反证过滤

- 位置：`D:\DS_workspace\MYATRI\src\myatri\memory\graph.py:60-73,81-83`；消费端 `D:\DS_workspace\MYATRI\src\myatri\retrieval\service.py:178-183` 和 `D:\DS_workspace\MYATRI\src\myatri\memory\themes.py:84-85`。
- 公开 Edge 契约提供 `status/valid_from/valid_to`（`contracts/__init__.py:176-178`），A2 的输出 schema 和提交路径允许填写；实现仅校验类型、端点和证据，没有时间/状态筛选。
- 合成探针存入两个事件之间的 contradicts，设置 `status='retracted'`、`valid_from='2020-01-01T00:00:00+00:00'`、`valid_to='2020-01-02T00:00:00+00:00'`；当前 recall 仍返回两端 `counter_refs=['left@1','right@1']`，且所有涉及主题的 `theme_materials.counter_refs` 仍包含两端。对端程序编译事件因此被扩展进珊瑚潜泳回忆。
- 限定：文档未定义 status 的封闭词表或 valid_to 的精确检索规则，所以 `retracted` 只是公开模型可接受的值，不能声称已有“撤回边”业务流程失效。已确认的是这些元数据目前仅保存、对计算无作用；若要把它们用于关系失效或历史查询，需先定义语义并接通筛选/摘要失效。目前不得将其当成已实现的时间关系能力。

## 已知问题复验

本轮显式运行：

```powershell
.\.venv\Scripts\python.exe -m pytest tests/audit_memory_consistency.py -q --basetemp=reports/review_memory_tmp_20261020 -rx
```

结果：`2 xfailed in 1.55s`。这是两个严格预期失败仍成立，不能计为两个修复后通过。

- M01 / P1（已知未修）：`D:\DS_workspace\MYATRI\src\myatri\retrieval\service.py:169-183`，历史请求使用当前图，只限制端点可见。旧快照没有 later contradicts 记录，却出现它导出的 counter_refs。应按边记录本身的快照可见性筛选或回退。
- M02 / P2（已知未修）：`D:\DS_workspace\MYATRI\src\myatri\memory\index.py:142-145`，旧重建在较新重建后完成仍可覆盖 current 指针。写锁保证发布完整性，不保证水位单调；需要发布条件检查。档案无丢失，但新向量暂时缺失。

## 实现范围与其他意见

- 当前权威档案在 manifest 最后发布、哈希、跨进程写锁、同域来源/引用、版本单调与原始消息/事件不可改写方面已有明确代码与回归覆盖。本轮未证明它们存在新增破坏，不能因上述索引问题宣称原始档案丢失。
- 稳定 Entity/Skill/Procedure、长文分块、局部增量与规模优化在 docs/04 中明确是待实现设计，不按“现有实现坏了”处理。
- 本轮只覆盖指定模块和最小离线复现，不新增外部模型质量或长期行为有效性的结论。完整回归由主审查代理统一运行。
