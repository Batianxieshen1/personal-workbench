"""学习进度增强测试：阶段写回 md、备考计划解析。"""
from app import progress

PLAN_SAMPLE = """# 备考计划：认识大模型

## 阶段安排
1. ✅ 一键大纲解析与本地化
2. ⬜ 按章授课 + 章节测验（ch1 → ch5）
3. ⬜ 错题扫雷
4. ⬜ 生成考前极简速记小抄
"""

PROGRESS_SAMPLE = """# 复习进度

- 科目：认识大模型

## 当前阶段
- [x] ch1 授课 + 测验
- [ ] ch2 授课 + 测验
- [ ] ch3 授课 + 测验
"""


def test_parse_study_plan_stages():
    stages = progress.parse_plan_stages(PLAN_SAMPLE)
    assert len(stages) == 4
    assert stages[0] == {"done": True, "text": "一键大纲解析与本地化"}
    assert stages[1]["done"] is False
    assert stages[3]["text"] == "生成考前极简速记小抄"


def test_parse_plan_empty():
    assert progress.parse_plan_stages("") == []


def test_toggle_stage_writes_back(tmp_path):
    f = tmp_path / "study_progress.md"
    f.write_text(PROGRESS_SAMPLE, encoding="utf-8")
    # 勾选 ch2
    progress.toggle_stage(str(f), 1, True)
    text = f.read_text(encoding="utf-8")
    assert "- [x] ch2 授课 + 测验" in text
    assert "- [ ] ch3 授课 + 测验" in text
    # 取消勾选 ch1
    progress.toggle_stage(str(f), 0, False)
    text = f.read_text(encoding="utf-8")
    assert "- [ ] ch1 授课 + 测验" in text
    # 其余内容不被破坏
    assert "# 复习进度" in text
    assert "## 当前阶段" in text


def test_toggle_stage_bad_index(tmp_path):
    f = tmp_path / "study_progress.md"
    f.write_text(PROGRESS_SAMPLE, encoding="utf-8")
    try:
        progress.toggle_stage(str(f), 99, True)
        assert False, "应当抛出 IndexError"
    except IndexError:
        pass
