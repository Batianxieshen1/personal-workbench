"""新闻模块测试：aihot API 解析、RSS 解析、缓存、降级。"""
import datetime as dt
import time

from app import news, storage

AIHOT_SAMPLE = {
    "items": [
        {
            "id": "abc",
            "title": "OpenAI 发布新模型",
            "summary": "中文摘要内容",
            "source": {"name": "OpenAI 官网"},
            "links": {"aihot": "https://aihot.virxact.com/items/abc", "original": "https://openai.com/x"},
            "publishedAt": "2026-08-07T10:00:00Z",
        }
    ]
}

RSS_SAMPLE = """<?xml version="1.0"?>
<rss version="2.0"><channel>
  <title>IT之家</title>
  <item>
    <title>某科技新闻标题</title>
    <link>https://www.ithome.com/0/xxx.htm</link>
    <pubDate>Fri, 07 Aug 2026 10:00:00 GMT</pubDate>
    <description>简介文字</description>
  </item>
</channel></rss>
"""

HN_SAMPLE = {
    "hits": [
        {
            "title": "HN 热门标题",
            "url": "https://example.com/1",
            "created_at": "2026-08-07T10:00:00Z",
        }
    ]
}


def test_parse_aihot(monkeypatch, tmp_path):
    monkeypatch.setattr(storage, "DATA_DIR", str(tmp_path))
    monkeypatch.setattr(news.requests, "get",
                        lambda url, timeout=10, headers=None: _FakeResp(AIHOT_SAMPLE))
    items = news.fetch_aihot()
    assert len(items) == 1
    assert items[0]["title"] == "OpenAI 发布新模型"
    assert items[0]["source"] == "OpenAI 官网"
    assert items[0]["url"].startswith("https://openai.com")


def test_parse_rss(monkeypatch, tmp_path):
    monkeypatch.setattr(storage, "DATA_DIR", str(tmp_path))
    monkeypatch.setattr(news.requests, "get",
                        lambda url, timeout=10, headers=None: _FakeResp(RSS_SAMPLE))
    items = news.fetch_rss("https://fake/rss", source_name="IT之家")
    assert len(items) == 1
    assert items[0]["title"] == "某科技新闻标题"
    assert items[0]["source"] == "IT之家"
    assert items[0]["url"].startswith("https://www.ithome.com")


def test_parse_hn(monkeypatch, tmp_path):
    monkeypatch.setattr(storage, "DATA_DIR", str(tmp_path))
    monkeypatch.setattr(news.requests, "get",
                        lambda url, timeout=10, headers=None: _FakeResp(HN_SAMPLE))
    items = news.fetch_hn()
    assert len(items) == 1
    assert items[0]["title"] == "HN 热门标题"


def test_cache_hits_within_ttl(monkeypatch, tmp_path):
    """1 小时内重复请求走缓存，不重复拉外部。"""
    monkeypatch.setattr(storage, "DATA_DIR", str(tmp_path))
    calls = {"n": 0}

    def fake_get(url, timeout=10, headers=None):
        calls["n"] += 1
        return _FakeResp(AIHOT_SAMPLE)

    monkeypatch.setattr(news.requests, "get", fake_get)
    news.get_news("ai")
    news.get_news("ai")  # 命中缓存
    assert calls["n"] == 1


def test_failure_degrades(monkeypatch, tmp_path):
    """外部源失败返回空列表 + error 标记，不抛异常。"""
    monkeypatch.setattr(storage, "DATA_DIR", str(tmp_path))

    def boom(url, timeout=10, headers=None):
        raise RuntimeError("网络错误")

    monkeypatch.setattr(news.requests, "get", boom)
    result = news.get_news("global")
    assert result["error"] is True
    assert result["items"] == []


class _FakeResp:
    def __init__(self, payload):
        self._p = payload

    def json(self):
        return self._p

    @property
    def text(self):
        return self._p if isinstance(self._p, str) else ""

    def raise_for_status(self):
        pass
