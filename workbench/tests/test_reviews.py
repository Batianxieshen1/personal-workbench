"""复盘模块测试：每日总结存取、AI 起草（聚合数据）、周报聚合与起草。"""
import json
import pytest

from app import reviews, storage


def test_get_review_default(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "DATA_DIR", str(tmp_path))
    r = reviews.get_review("2026-08-03")
    assert r["date"] == "2026-08-03"
    assert r["summary"] == ""


def test_save_review(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "DATA_DIR", str(tmp_path))
    reviews.save_review("2026-08-03", "今天完成了 M2 全部任务")
    assert reviews.get_review("2026-08-03")["summary"] == "今天完成了 M2 全部任务"


def test_ai_draft_aggregates_context(monkeypatch, tmp_path):
    monkeypatch.setattr(storage, "DATA_DIR", str(tmp_path))
    # 今日计划：2 项，1 项完成
    storage.save("plans/2026-08-03.json", {"date": "2026-08-03", "items": [
        {"id": "a", "text": "背单词", "done": True},
        {"id": "b", "text": "写代码", "done": False},
    ]})
    # 今日灵感 1 条
    storage.save("ideas.json", {"ideas": [
        {"id": "i1", "text": "AI 点子", "source": "ai", "date": "2026-08-03", "status": "kept", "created_at": "2026-08-03T00:00:00"},
    ]})
    captured = {}

    def fake_chat(prompt, system="", timeout=60.0):
        captured["prompt"] = prompt
        return "这是 AI 起草的总结"

    monkeypatch.setattr(reviews.deepseek, "chat", fake_chat)
    draft = reviews.ai_draft("2026-08-03")
    assert draft == "这是 AI 起草的总结"
    # 上下文必须包含计划完成情况和灵感
    assert "背单词" in captured["prompt"]
    assert "1/2" in captured["prompt"]
    assert "AI 点子" in captured["prompt"]


def test_week_number():
    assert reviews.week_of("2026-08-03") == "2026-W32"


def test_weekly_draft_aggregates_week(monkeypatch, tmp_path):
    monkeypatch.setattr(storage, "DATA_DIR", str(tmp_path))
    storage.save("plans/2026-08-03.json", {"date": "2026-08-03", "items": [
        {"id": "a", "text": "周计划一", "done": True},
    ]})
    storage.save("reviews/2026-08-03.json", {"date": "2026-08-03", "summary": "周一总结"})
    captured = {}

    def fake_chat(prompt, system="", timeout=60.0):
        captured["prompt"] = prompt
        return "周报草稿"

    monkeypatch.setattr(reviews.deepseek, "chat", fake_chat)
    draft = reviews.weekly_draft("2026-W32")
    assert draft == "周报草稿"
    assert "周计划一" in captured["prompt"]
    assert "周一总结" in captured["prompt"]


def test_ai_draft_failure_propagates(monkeypatch, tmp_path):
    monkeypatch.setattr(storage, "DATA_DIR", str(tmp_path))
    monkeypatch.setattr(reviews.deepseek, "chat",
                        lambda prompt, system="", timeout=60.0: (_ for _ in ()).throw(reviews.deepseek.AIError("挂", reason="network")))
    with pytest.raises(reviews.deepseek.AIError):
        reviews.ai_draft("2026-08-03")
