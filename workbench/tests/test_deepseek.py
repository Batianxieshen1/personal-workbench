"""DeepSeek 客户端测试：mock 网络请求，验证解析、key 读取、失败降级。"""
import pytest

from app import deepseek


class FakeResp:
    def __init__(self, payload, ok=True):
        self._payload = payload
        self.ok = ok

    def json(self):
        return self._payload

    def raise_for_status(self):
        if not self.ok:
            raise RuntimeError("HTTP 错误")


def test_get_api_key_from_env(monkeypatch, tmp_path):
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    (tmp_path / ".env").write_text("DEEPSEEK_API_KEY=sk-test123\n", encoding="utf-8")
    monkeypatch.setattr(deepseek, "ENV_PATH", str(tmp_path / ".env"))
    assert deepseek.get_api_key() == "sk-test123"


def test_get_api_key_missing_returns_empty(monkeypatch, tmp_path):
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    monkeypatch.setattr(deepseek, "ENV_PATH", str(tmp_path / "不存在.env"))
    assert deepseek.get_api_key() == ""


def test_chat_parses_content(monkeypatch):
    fake = FakeResp({"choices": [{"message": {"content": "  你好，我是 DeepSeek  "}}]})
    monkeypatch.setattr(deepseek.requests, "post", lambda *a, **k: fake)
    monkeypatch.setattr(deepseek, "get_api_key", lambda: "sk-test")
    assert deepseek.chat("hi") == "你好，我是 DeepSeek"


def test_chat_no_key_raises(monkeypatch):
    monkeypatch.setattr(deepseek, "get_api_key", lambda: "")
    with pytest.raises(deepseek.AIError):
        deepseek.chat("hi")


def test_chat_network_failure_raises(monkeypatch):
    def boom(*a, **k):
        raise RuntimeError("连接超时")

    monkeypatch.setattr(deepseek.requests, "post", boom)
    monkeypatch.setattr(deepseek, "get_api_key", lambda: "sk-test")
    with pytest.raises(deepseek.AIError):
        deepseek.chat("hi")


def test_chat_empty_content_raises(monkeypatch):
    fake = FakeResp({"choices": [{"message": {"content": "  "}}]})
    monkeypatch.setattr(deepseek.requests, "post", lambda *a, **k: fake)
    monkeypatch.setattr(deepseek, "get_api_key", lambda: "sk-test")
    with pytest.raises(deepseek.AIError):
        deepseek.chat("hi")
