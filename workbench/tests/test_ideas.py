"""灵感池测试：生成幂等、解析、手动添加、状态流转、降级。"""
import pytest

from app import ideas, storage

IDEA_TEXT = """- 把背单词变成打怪升级游戏，用雅思词库做关卡
- 给每天的学习进度生成一张赛博卡片，适合发朋友圈
- 用 AI 把错题本变成脱口秀段子，记忆更牢
- 做一个"五分钟出门"清单生成器
- 把 Obsidian 日记用 AI 画出每周时间线图谱
"""


def test_generate_creates_batch(monkeypatch, tmp_path):
    monkeypatch.setattr(storage, "DATA_DIR", str(tmp_path))
    monkeypatch.setattr(ideas.deepseek, "chat", lambda prompt, system="", timeout=60.0: IDEA_TEXT)
    items = ideas.generate_today("2026-08-03")
    assert len(items) == 5
    assert items[0]["source"] == "ai"
    assert items[0]["status"] == "kept"
    assert items[0]["date"] == "2026-08-03"


def test_generate_idempotent(monkeypatch, tmp_path):
    monkeypatch.setattr(storage, "DATA_DIR", str(tmp_path))
    monkeypatch.setattr(ideas.deepseek, "chat", lambda prompt, system="", timeout=60.0: IDEA_TEXT)
    first = ideas.generate_today("2026-08-03")
    second = ideas.generate_today("2026-08-03")  # 当天第二次调用不重复生成
    assert [i["id"] for i in first] == [i["id"] for i in second]


def test_generate_ai_failure_degrades(monkeypatch, tmp_path):
    monkeypatch.setattr(storage, "DATA_DIR", str(tmp_path))
    monkeypatch.setattr(ideas.deepseek, "chat",
                        lambda prompt, system="", timeout=60.0: (_ for _ in ()).throw(ideas.deepseek.AIError("无 key", reason="no_key")))
    with pytest.raises(ideas.deepseek.AIError):
        ideas.generate_today("2026-08-03")
    # 失败后不残留半批数据
    assert ideas.get_today("2026-08-03") == []


def test_manual_add_and_status(monkeypatch, tmp_path):
    monkeypatch.setattr(storage, "DATA_DIR", str(tmp_path))
    ideas.add_manual("随手记的点子", "2026-08-03")  # 显式日期，避免依赖真实时钟跨天
    items = ideas.get_today("2026-08-03")
    assert len(items) == 1
    assert items[0]["source"] == "manual"
    assert items[0]["status"] == "kept"
    assert items[0]["note"] == ""
    ideas.set_status(items[0]["id"], "discarded")
    assert ideas.get_today("2026-08-03")[0]["status"] == "discarded"


def test_list_all_ordered(monkeypatch, tmp_path):
    monkeypatch.setattr(storage, "DATA_DIR", str(tmp_path))
    monkeypatch.setattr(ideas.deepseek, "chat", lambda prompt, system="", timeout=60.0: IDEA_TEXT)
    ideas.generate_today("2026-08-02")
    ideas.generate_today("2026-08-03")
    ideas.add_manual("手动点子")
    all_items = ideas.list_all()
    assert len(all_items) == 11  # 5 + 5 + 1
    # 最新在前
    assert all_items[0]["source"] == "manual"
