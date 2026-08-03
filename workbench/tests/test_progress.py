"""学习进度解析器测试：真实结构样例 + 边界情况。"""
from app import progress

SAMPLE = """# 复习进度（断点锁定）

- 科目：认识大模型（大模型工程师课程·第1章）
- 最后更新：2026-08-02（导入日）

## 当前阶段
- [x] ch1 授课 + 测验（3/3 通过）
- [x] ch2 授课 + 测验（4/4 通过）
- [ ] ch3 授课 + 测验（4/4 通过）
- [x] 错题扫雷（错题本为空，跳过）

## 已完成
- 2026-08-02：知识库导入完成

## 测验记录
| 章节 | 状态 | 结果 |
| --- | --- | --- |
| ch1 | 已通过 | 3/3 全对 |
| ch2 | 已通过 | 4/4 |
"""


def test_parse_subject_and_updated():
    p = progress.parse_markdown(SAMPLE)
    assert p["subject"] == "认识大模型（大模型工程师课程·第1章）"
    assert p["updated"] == "2026-08-02"


def test_parse_stages_checkboxes():
    p = progress.parse_markdown(SAMPLE)
    assert len(p["stages"]) == 4
    assert p["stages"][0] == {"done": True, "text": "ch1 授课 + 测验（3/3 通过）"}
    assert p["stages"][2]["done"] is False
    assert p["done_count"] == 3
    assert p["total_count"] == 4


def test_parse_chapters_table():
    p = progress.parse_markdown(SAMPLE)
    assert len(p["chapters"]) == 2
    assert p["chapters"][0] == {"chapter": "ch1", "status": "已通过", "result": "3/3 全对"}
    assert p["chapters"][1]["result"] == "4/4"


def test_parse_empty_text():
    p = progress.parse_markdown("")
    assert p["stages"] == []
    assert p["chapters"] == []
    assert p["done_count"] == 0


def test_load_progress_from_file(tmp_path):
    f = tmp_path / "study_progress.md"
    f.write_text(SAMPLE, encoding="utf-8")
    p = progress.load_progress(str(f))
    assert p["subject"].startswith("认识大模型")
    assert p["done_count"] == 3


def test_load_progress_missing_file_degrades(tmp_path):
    p = progress.load_progress(str(tmp_path / "不存在.md"))
    assert p["missing"] is True
    assert p["stages"] == []
    assert p["chapters"] == []
