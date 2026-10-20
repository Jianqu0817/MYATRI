# 第三方来源与许可登记

0.1.3 新增 emotional-memory（MIT）的PAD回归、EMA、插值与距离局部改编，实际用于情绪状态投影。源码锁定8b84bf3725448f2545337c08e346434819c01628；完整许可为LICENSES/upstream/Emotional-Memory-LICENSE，改动与哈希见同目录manifest.json。未安装/接入其完整记忆系统。当前共三处上游改编，以下0.1.2说明保留历史含义。

0.1.2 起包含两处有实际生产调用的上游代码改编：A-MEM 的有界关联邻居去重内核，以及 Letta Code 的完整快照原子写入内核。其余参考仍为方法借鉴。不是整套框架移植，也未安装这些框架。逐段来源、修改和校验记录见 [复用清单](LICENSES/upstream/manifest.json) 与 [本轮报告](reports/upstream_reuse_2026-10-20.md)；初次独立实现记录 reports/source_audit.md 为历史状态。

| 项目 | 锁定提交 | 许可 | 采用方式 |
|---|---|---|---|
| gianlucamazza/emotional-memory | 8b84bf3725448f2545337c08e346434819c01628 | MIT | MoodField.regress/update与CoreAffect.lerp/distance局部改编；不采用存储与重复召回强化 |
| agiresearch/A-mem | ceffb860f0712bbae97b184d440df62bc910ca8d | MIT | search_agentic 的关联邻居去重/限量展开局部改编；其余方法参考 |
| letta-ai/letta-code | e8073d4e475ab7f56e76f9aaeea81a7618a92575 | Apache-2.0（保留完整上游 LICENSE） | writeAuthFile 的原子写入内核由 TypeScript 改编为 Python；不读取凭据 |
| letta-ai/letta（archive） | 56ba9c25552605eec89de8ed3dc6394b625c1993 | Apache-2.0 | 已读旧 Python 上下文/协议/分块与 JSON 处理；未移植 |
| alpaim/ashley | c2e0c0b5563773c80a5d2acc0c5fb007c04e4212 | MIT | 生命周期、局部人格修改、余波组织；未复制 |
| microsoft/graphrag | 5faaaf4f5685fa2056fa8c3bf9342cb089f2942f | MIT | Leiden 群落与摘要方法；未复制 |
| getzep/graphiti | 7b0182f94d27075db488636cd5456981ee10b987 | Apache-2.0 | 时间/证据、融合召回方法；未复制 |
| xybruceliu/thoughtful-agents | 4c8d5beb249f852465463ed236fbbff95e0b6b0d | Apache-2.0 | 念头池与激活方法；未复制 |

依赖许可以实际安装包 metadata 为准，交付前生成 reports/dependency_licenses.json。Leiden/igraph 包含 GPL 许可组件，分发需遵守其条款，不能推定都为 MIT；发行包不捆绑依赖，保留环境和依赖许可清单。LICENSES/README.md 说明源代码复制状态。

## 模型资产与独立验证

本次显式下载本地可选模型 Xenova/bge-small-zh-v1.5（固定提交75c43b069aac4d136ba6bc1122f995fedcfd2781，24MB int8 ONNX），其模型卡指向原始 BAAI/bge-small-zh-v1.5。原模型HuggingFace metadata实查license=mit，提交7999e1d3359715c523056ef9478215996d62a620；转换仓库metadata没有单独声明license，未将其推定为额外许可授权。模型文件仅本地可选缓存，不捆绑进wheel/sdist；分发模型前应保留并核验原始模型许可及转换来源。下载hash见reports/model_manifest.json。

真实安装依赖许可（包含67份包内license/notice）保存在LICENSES/dependencies；reports/dependency_licenses.json保留实际metadata与版本。igraph/leidenalg的GPL组件单列，不能把本项目方法参考的MIT等同依赖许可。构建包不捆绑科学库或模型权重。

## 已改编源码的许可材料

`LICENSES/upstream/A-MEM-LICENSE` 与 `LICENSES/upstream/Letta-Code-LICENSE.txt` 是对应固定提交的完整原始 LICENSE；锁定树均没有独立 NOTICE。改编文件在 `src/myatri/_vendor/` 标明版权、来源及修改。Letta Code LICENSE 的 Brand Assets Exclusion 原样保留，本项目未复制其标志、图片或 ASCII art。wheel 在 `myatri/_vendor/upstream/` 附带两份许可证和 manifest，sdist 保留 `LICENSES/upstream/`。
