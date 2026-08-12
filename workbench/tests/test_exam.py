"""考公模块测试：科目进度、考试倒计时、AI 出题与判题。"""
import datetime as dt

from app import exam, storage


def test_exam_info_structure():
    """考情速览数据结构完整。"""
    assert "xingce" in exam.EXAM_INFO
    assert len(exam.EXAM_INFO["xingce"]["modules"]) == 5  # 行测五模块
    assert "shenlun" in exam.EXAM_INFO
    assert "province" in exam.EXAM_INFO
    assert "state" in exam.EXAM_INFO


def test_progress_default_and_set(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "DATA_DIR", str(tmp_path))
    p = exam.get_progress()
    assert p["progress"] == {}
    exam.set_progress("政治理论", True)
    assert exam.get_progress()["progress"]["政治理论"] is True


def test_exam_date_and_countdown(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "DATA_DIR", str(tmp_path))
    exam.set_exam_date("2027-03-13")
    days = exam.days_until_exam()
    assert days is not None and days > 0


def test_exam_date_not_set(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "DATA_DIR", str(tmp_path))
    assert exam.days_until_exam() is None


def test_ai_generate_question(monkeypatch, tmp_path):
    monkeypatch.setattr(storage, "DATA_DIR", str(tmp_path))
    monkeypatch.setattr(exam.deepseek, "chat",
                        lambda prompt, system="", timeout=60.0: "题目：1+1=？\nA. 1\nB. 2\nC. 3\nD. 4\n答案：B\n解析：基础加法")
    q = exam.ai_generate_question("数量关系")
    assert q["module"] == "数量关系"
    assert "1+1" in q["content"]
    # 答案被剥离：content 不含"答案："行，answer 字段单独存
    assert "答案：" not in q["content"]
    assert q["answer"] == "B"
    assert q["explain"] == "基础加法"


def test_ai_generate_without_answer_lines(monkeypatch, tmp_path):
    """AI 未按格式输出时兜底：answer 为空，content 保留原文。"""
    monkeypatch.setattr(storage, "DATA_DIR", str(tmp_path))
    monkeypatch.setattr(exam.deepseek, "chat",
                        lambda prompt, system="", timeout=60.0: "题目：x\nA. 1\nB. 2")
    q = exam.ai_generate_question("数量关系")
    assert q["answer"] == ""
    assert "A. 1" in q["content"]


def test_ai_check_answer(monkeypatch, tmp_path):
    monkeypatch.setattr(storage, "DATA_DIR", str(tmp_path))
    monkeypatch.setattr(exam.deepseek, "chat",
                        lambda prompt, system="", timeout=60.0: "回答正确 ✅ 解析：……")
    r = exam.ai_check_answer("数量关系", "题目内容", "B", answer="B")
    assert "解析" in r["result"] or "正确" in r["result"]


def test_modules_list():
    assert "政治理论" in exam.EXAM_MODULES
    assert "科学推理" in exam.EXAM_MODULES  # 广东特色
