# 第三方来源与许可登记

本项目没有复制以下项目源代码；采用规划中的组织方法并独立编写 Python 实现。锁定提交、源码路径、上游许可证均见 docs/03_参考源码锁定.json；报告见 reports/source_audit.md。

| 项目 | 锁定提交 | 许可 | 采用方式 |
|---|---|---|---|
| agiresearch/A-mem | ceffb860f0712bbae97b184d440df62bc910ca8d | MIT | 参考事件笔记、近邻关联；未复制 |
| alpaim/ashley | c2e0c0b5563773c80a5d2acc0c5fb007c04e4212 | MIT | 生命周期、局部人格修改、余波组织；未复制 |
| microsoft/graphrag | 5faaaf4f5685fa2056fa8c3bf9342cb089f2942f | MIT | Leiden 群落与摘要方法；未复制 |
| getzep/graphiti | 7b0182f94d27075db488636cd5456981ee10b987 | Apache-2.0 | 时间/证据、融合召回方法；未复制 |
| xybruceliu/thoughtful-agents | 4c8d5beb249f852465463ed236fbbff95e0b6b0d | Apache-2.0 | 念头池与激活方法；未复制 |

依赖许可以实际安装包 metadata 为准，交付前生成 reports/dependency_licenses.json。Leiden/igraph 包含 GPL 许可组件，分发需遵守其条款，不能推定都为 MIT；发行包不捆绑依赖，保留环境和依赖许可清单。LICENSES/README.md 说明源代码复制状态。

## 模型资产与独立验证

本次显式下载本地可选模型 Xenova/bge-small-zh-v1.5（固定提交75c43b069aac4d136ba6bc1122f995fedcfd2781，24MB int8 ONNX），其模型卡指向原始 BAAI/bge-small-zh-v1.5。原模型HuggingFace metadata实查license=mit，提交7999e1d3359715c523056ef9478215996d62a620；转换仓库metadata没有单独声明license，未将其推定为额外许可授权。模型文件仅本地可选缓存，不捆绑进wheel/sdist；分发模型前应保留并核验原始模型许可及转换来源。下载hash见reports/model_manifest.json。

真实安装依赖许可（包含67份包内license/notice）保存在LICENSES/dependencies；reports/dependency_licenses.json保留实际metadata与版本。igraph/leidenalg的GPL组件单列，不能把本项目方法参考的MIT等同依赖许可。构建包不捆绑科学库或模型权重。
