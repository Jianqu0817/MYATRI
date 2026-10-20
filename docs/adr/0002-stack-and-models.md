# ADR 0002：实际环境与模型

2026-10-20。Python3.12.7 + uv，Windows本地环境。uv.lock来自实际解析与安装；初次PyPI科学包下载耗时约9分钟，改用清华镜像安装可选CPU推理包和兼容范围SciPy1.13–1.15，最终实际版本以uv.lock/reports/environment_smoke.json为准。后续 uv sync --frozen --extra neural 可复原，默认无需神经模型依赖。

Embedding比较：默认真实中文char ngram TF-IDF，完全离线且空间由语料/词表版本决定；不称神经语义模型。可选 Xenova/bge-small-zh-v1.5 固定提交75c43b069aac4d136ba6bc1122f995fedcfd2781，约24MB int8 ONNX，CPU CLS pooling/L2，512维。本次明确告知后下载并真正推理，无付费调用。原模型 BAAI/bge-small-zh-v1.5 的方法/模型卡：https://huggingface.co/BAAI/bge-small-zh-v1.5；ONNX转换来源：https://huggingface.co/Xenova/bge-small-zh-v1.5。下载校验清单位于var/models/bge-small-zh-v1.5/manifest.json，交付报告另保存副本。运行时不自动下载。

中文smoke：电影取消失落 vs 临时取消约会难过 cosine=0.6847；不喜欢频繁确认 vs 喜欢频繁确认 cosine=0.8820。否定能力不足，故向量只能候选，不能替代支持/反驳审查。TF-IDF与BGE比较及情感多视角结果见evaluation.json，选择默认词面基线是为低成本复现，不声称优于BGE。BGE可配置用于实际语义向量；跨空间/维度拒绝混查，保留generation回退。

真实igraph/Leiden已运行，非LLM手工分组。使用全图重建作为V1正确性基线；局部增量优化留待规模测量，不声称局部算法等同全局最优。

DeepSeek静态协议适配已实现，当前官方文档示例模型为deepseek-flash，可配置。thinking/tool能力经live smoke前默认禁用；JSON mode加本地schema验证，无严格beta能力宣称。未使用密钥、未付费调用，真实DeepSeek质量、价格、usage与网络错误仍需用户后续授权和配置。模型开关与价格不硬编码业务逻辑。

## 2026-10-20 追加决定：Windows凭据与真实协议smoke

用户已授权官方DeepSeek-V4.1-Flash小规模付费测试与安全密钥保存。新增Windows Credential Manager后端，不生成项目密钥文件；官方host限制、禁止redirect、惰性读取，不在offline访问凭据。JSON mode必须把实际schema传给模型，不能仅本地验证。

模型id=deepseek-flash经官方GET/models实际核验；生成/JSON/tools/thinking+tools通过，实际认知链A8发现弱schema缺陷，升级完整schema及prompt v2后定向重放通过。用量/成本见reports/live_smoke.json/md，不能继续把“当前未付费测试”当作事实；历史首轮离线说明保持其日期范围。A6/A7长期语义仍pending。

config/live.local.toml只有开关/模型/预算，不含key，Git/backup/sdist/wheel均排除。发行包config使用逐文件allowlist，通用敏感路径排除大小写变体；12项真实构建/备份fake sentinel回归通过。所有活动仍不包括联系人投递或部署。
