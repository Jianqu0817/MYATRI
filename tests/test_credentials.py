import ctypes

import httpx
import pytest

from myatri import credentials
from myatri.contracts import ModelRequest
from myatri.providers import DeepSeekProvider, ProviderError


def test_windows_credential_store_roundtrip_with_fake_os_api(monkeypatch, tmp_path):
    fake = "sk-" + "synthetic-not-real-secret" * 2
    kept = {}
    buffers = []
    class API:
        def CredWriteW(self, pointer, flags):
            record = ctypes.cast(pointer, ctypes.POINTER(credentials.CREDENTIALW)).contents
            kept.update(target=record.TargetName, value=ctypes.string_at(record.CredentialBlob, record.CredentialBlobSize), persist=record.Persist)
            return True
        def CredReadW(self, target, type_, flags, output):
            blob = (credentials.wintypes.BYTE * len(kept["value"])).from_buffer_copy(kept["value"])
            record = credentials.CREDENTIALW(CredentialBlobSize=len(kept["value"]), CredentialBlob=blob)
            pointer = ctypes.pointer(record)
            buffers.extend([blob, record, pointer])
            ctypes.cast(output, ctypes.POINTER(ctypes.POINTER(credentials.CREDENTIALW)))[0] = pointer
            return True
        def CredFree(self, pointer):
            kept["freed"] = True
    monkeypatch.setattr(credentials, "_wincred", lambda: API())
    credentials.save_deepseek_key(fake)
    assert credentials.read_deepseek_key() == fake
    assert kept["target"] == credentials.DEEPSEEK_TARGET and kept["persist"] == 2 and kept["freed"]
    assert not list(tmp_path.iterdir())


async def test_saved_key_lazy_loading_and_official_host_only(monkeypatch):
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    reads = []
    monkeypatch.setattr(credentials, "read_deepseek_key", lambda: reads.append(True) or "fake-stored-key")
    captured = []
    def handle(request):
        captured.append(request)
        return httpx.Response(200, json={"model": "deepseek-flash", "choices": [{"message": {"content": "ok"}, "finish_reason": "stop"}]})
    async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
        provider = DeepSeekProvider(model="deepseek-flash", allow_paid=True, client=client)
        assert not reads
        assert (await provider.generate(ModelRequest(messages=[]))).content == "ok"
        assert captured[0].headers["Authorization"] == "Bearer fake-stored-key"
        with pytest.raises(ProviderError, match="official"):
            await DeepSeekProvider(model="deepseek-flash", endpoint="https://api.deepseek.com.evil.invalid", allow_paid=True, client=client).generate(ModelRequest(messages=[]))
        assert len(captured) == 1 and len(reads) == 1


def test_invalid_secret_format_rejected_without_os_write(monkeypatch):
    monkeypatch.setattr(credentials, "_wincred", lambda: pytest.fail("must not access OS"))
    with pytest.raises(credentials.CredentialError):
        credentials.save_deepseek_key("invalid")


async def test_schema_sent_but_authorization_not_serialized(monkeypatch):
    captured = []
    def handle(request):
        captured.append(request)
        return httpx.Response(200, json={"choices": [{"message": {"content": '{"ok":true}'}, "finish_reason": "stop"}]})
    async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
        provider = DeepSeekProvider(model="deepseek-flash", api_key="fake-header-only", allow_paid=True, client=client)
        response = await provider.generate(ModelRequest(messages=[{"role": "user", "content": "test"}], output_schema={"type": "object"}))
    assert "fake-header-only" not in captured[0].content.decode()
    assert "fake-header-only" not in response.model_dump_json()
    assert "JSON Schema" in captured[0].content.decode()
