"""雅思 AI 练习测试：作文批改、口语模拟。"""
from app import ielts_ai


def test_essay_review(monkeypatch):
    monkeypatch.setattr(ielts_ai.deepseek, "chat",
                        lambda prompt, system="", timeout=60.0: "四项得分均为 6.5，总分 6.5。优点：结构清晰。建议：增加高级词汇。")
    r = ielts_ai.essay_review("Some people think...", topic="教育")
    assert "6.5" in r["review"]


def test_essay_review_empty_rejected():
    try:
        ielts_ai.essay_review("   ")
        assert False, "空作文应当被拒绝"
    except ValueError:
        pass


def test_speaking_questions(monkeypatch):
    monkeypatch.setattr(ielts_ai.deepseek, "chat",
                        lambda prompt, system="", timeout=60.0: "问题1：你住在哪里？\n问题2：你喜欢你的家乡吗？\n问题3：未来你想住在城市还是乡村？")
    r = ielts_ai.speaking_questions("家乡")
    assert len(r["questions"]) == 3
    assert "住在哪里" in r["questions"][0]


def test_speaking_review(monkeypatch):
    monkeypatch.setattr(ielts_ai.deepseek, "chat",
                        lambda prompt, system="", timeout=60.0: "流利度 6，词汇 6，语法 6，发音建议：注意 th 发音。")
    r = ielts_ai.speaking_review("家乡", "我住在广州，我很喜欢这里。")
    assert "发音" in r["review"]


def test_topics_available():
    assert len(ielts_ai.SPEAKING_TOPICS) >= 5
