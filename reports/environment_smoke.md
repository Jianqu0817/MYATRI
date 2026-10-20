# 环境实际验证

2026-10-20。Python3.12.7 Windows，uv创建.venv，实际解析锁定安装。tfidf/igraph/leidenalg均本地运行；可选ONNX/tokenizers已装且BGE真推理成功。具体版本/模型hash/SQLite FTS5兼容性见environment_smoke.json。

运行：`uv sync --frozen --extra neural`；普通无模型下载环境 `uv sync --frozen`。初次科学包下载慢，曾使用清华镜像实际解析（锁文件记录来源），无需安装参考框架。依赖许可按安装metadata记录，GPL组件单列。测试使用.venv解释器，不混用conda未装async插件的临时测试结果。
