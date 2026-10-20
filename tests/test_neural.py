import asyncio
import importlib.util
from pathlib import Path

import pytest

from myatri.app import Application


MODEL_PATH = Path(__file__).resolve().parents[1] / "var/models/bge-small-zh-v1.5"


@pytest.mark.skipif(not (MODEL_PATH / "manifest.json").exists() or importlib.util.find_spec("onnxruntime") is None or importlib.util.find_spec("tokenizers") is None,
                    reason="optional real local BGE model/runtime not installed; never download in tests")
async def test_real_bge_restart_sync_async_recall_and_saved_selection(tmp_path):
    from myatri.providers.local_onnx import LocalOnnxEmbeddingProvider
    provider = LocalOnnxEmbeddingProvider(MODEL_PATH)
    app = Application(tmp_path, embedding_provider=provider)
    await app.conversation.respond("那次电影临时取消，我有点失落。", message_id="neural_message")
    await app.drain()
    app.queue.set_meta("embedding", {"backend": "bge", "path": str(MODEL_PATH)})
    sync = app.index.query("观影约定取消后难过", limit=3)
    async_result = await app.index.aquery("观影约定取消后难过", limit=3)
    assert sync and sync == async_result
    assert app.index.indexes["event"].dimension == 512
    recovered = Application(tmp_path)
    assert recovered.index.provider.space_id == provider.space_id
    bundle = recovered.recall.recall("为什么电影临时取消后失落", budget=6000)
    assert any(r.record_id == "neural_message" for r in bundle.records)
    assert not any("需要异步" in limitation for limitation in bundle.limitations)
    assert all(j["status"] == "succeeded" for j in recovered.queue.list_jobs())
