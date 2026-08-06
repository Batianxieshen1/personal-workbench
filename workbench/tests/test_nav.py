"""AI 晨间导航测试：聚合上下文、当天缓存、降级。"""
import datetime as dt

import pytest

from app import guide, storage


@pytest.fixture(autouse=True)
def _clear_cache():
    """缓存是模块级共享的，每个测试前清空防止相互污染。"""
    guide._nav_cache.clear()
    guide._best_cache.clear()


def test_morning_nav_generates_and_caches(monkeypatch, tmp_path):
    monkeypatch.setattr(storage, "DATA_DIR", str(tmp_path))
    monkeypatch.setattr(guide.plan, "get_plan", lambda d: {"date": d, "items": [
        {"id": "a", "text": "背单词", "done": False},
    ]})
    monkeypatch.setattr(guide.vocab, "due_words", lambda today=None: [{"id": "w1"}])
    monkeypatch.setattr(guide.ideas, "get_today", lambda d: [{"id": "i1", "text": "AI 点子", "status": "kept"}])
    monkeypatch.setattr(guide.progress, "load_progress",
                        lambda: {"missing": False, "done_count": 3, "total_count": 8})
    monkeypatch.setattr(guide.reviews, "get_review", lambda d: {"summary": ""})
    calls = {"n": 0}

    def fake_chat(prompt, system="", timeout=60.0):
        calls["n"] += 1
        return "今天最重要的是背单词，因为明天到期。加油！"

    monkeypatch.setattr(guide.deepseek, "chat", fake_chat)
    nav = guide.morning_nav("2026-08-04")
    assert "背单词" in nav["text"]
    # 缓存：当天第二次调用不再调 AI
    guide.morning_nav("2026-08-04")
    assert calls["n"] == 1
    # 第二天重新生成
    guide.morning_nav("2026-08-05")
    assert calls["n"] == 2


def test_morning_nav_ai_failure_degrades(monkeypatch, tmp_path):
    monkeypatch.setattr(storage, "DATA_DIR", str(tmp_path))
    monkeypatch.setattr(guide.plan, "get_plan", lambda d: {"date": d, "items": []})
    monkeypatch.setattr(guide.vocab, "due_words", lambda today=None: [])
    monkeypatch.setattr(guide.ideas, "get_today", lambda d: [])
    monkeypatch.setattr(guide.progress, "load_progress",
                        lambda: {"missing": True, "done_count": 0, "total_count": 0})
    monkeypatch.setattr(guide.reviews, "get_review", lambda d: {"summary": ""})

    def boom(prompt, system="", timeout=60.0):
        raise guide.deepseek.AIError("无 key", reason="no_key")

    monkeypatch.setattr(guide.deepseek, "chat", boom)
    nav = guide.morning_nav("2026-08-04")
    assert nav["error"] is True
    # 失败不缓存，下次还能重试
    assert guide._nav_cache.get("2026-08-04") is None


def test_best_idea_today(monkeypatch, tmp_path):
    monkeypatch.setattr(storage, "DATA_DIR", str(tmp_path))
    monkeypatch.setattr(guide.ideas, "get_today", lambda d: [
        {"id": "a", "text": "点子一", "status": "kept"},
        {"id": "b", "text": "点子二", "status": "kept"},
    ])
    monkeypatch.setattr(guide.deepseek, "chat",
                        lambda prompt, system="", timeout=60.0: "点子二 | 因为它最贴近雅思备考")
    best = guide.best_idea_today("2026-08-04")
    assert best["text"] == "点子二"
    assert "雅思" in best["reason"]


def test_best_idea_no_ideas(monkeypatch, tmp_path):
    monkeypatch.setattr(storage, "DATA_DIR", str(tmp_path))
    monkeypatch.setattr(guide.ideas, "get_today", lambda d: [])
    assert guide.best_idea_today("2026-08-04") is None


def test_best_idea_cached_per_day(monkeypatch, tmp_path):
    """当天第二次调用不重复调 AI（省 token）。"""
    monkeypatch.setattr(storage, "DATA_DIR", str(tmp_path))
    monkeypatch.setattr(guide.ideas, "get_today", lambda d: [
        {"id": "a", "text": "点子一", "status": "kept"},
    ])
    calls = {"n": 0}

    def fake_chat(prompt, system="", timeout=60.0):
        calls["n"] += 1
        return "a | 理由"

    monkeypatch.setattr(guide.deepseek, "chat", fake_chat)
    guide.best_idea_today("2026-08-04")
    guide.best_idea_today("2026-08-04")  # 命中缓存
    assert calls["n"] == 1
    # 第二天重新调用
    guide.best_idea_today("2026-08-05")
    assert calls["n"] == 2


def test_best_idea_failure_not_cached(monkeypatch, tmp_path):
    """失败不缓存：下次调用还能重试。"""
    monkeypatch.setattr(storage, "DATA_DIR", str(tmp_path))
    monkeypatch.setattr(guide.ideas, "get_today", lambda d: [
        {"id": "a", "text": "点子一", "status": "kept"},
    ])
    calls = {"n": 0}

    def flaky_chat(prompt, system="", timeout=60.0):
        calls["n"] += 1
        if calls["n"] == 1:
            raise guide.deepseek.AIError("挂了", reason="network")
        return "a | 恢复成功"

    monkeypatch.setattr(guide.deepseek, "chat", flaky_chat)
    assert guide.best_idea_today("2026-08-04") is None  # 第一次失败
    best = guide.best_idea_today("2026-08-04")  # 重试成功
    assert best["text"] == "点子一"
    assert calls["n"] == 2
