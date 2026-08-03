"""雅思进度测试：默认值、字段更新、skills 合并。"""
from app import ielts, storage


def test_default_ielts(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "DATA_DIR", str(tmp_path))
    data = ielts.get_ielts()
    assert data["target_score"] == 6.5
    assert set(data["skills"].keys()) == {"听力", "阅读", "写作", "口语"}


def test_update_fields(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "DATA_DIR", str(tmp_path))
    ielts.update_ielts({"target_score": 7.0, "exam_date": "2026-12-01"})
    data = ielts.get_ielts()
    assert data["target_score"] == 7.0
    assert data["exam_date"] == "2026-12-01"
    assert data["stage"] == "基础强化"  # 未改的字段保持默认


def test_update_skills_merges(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "DATA_DIR", str(tmp_path))
    ielts.update_ielts({"skills": {"听力": "6.0"}})
    data = ielts.get_ielts()
    assert data["skills"]["听力"] == "6.0"
    assert data["skills"]["阅读"] == ""  # 其他科保持默认


def test_ignore_unknown_keys(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "DATA_DIR", str(tmp_path))
    ielts.update_ielts({"不存在的字段": 123})
    assert "不存在的字段" not in ielts.get_ielts()
