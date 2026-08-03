"""学习进度解析器：读取项目根 study_progress.md，提取结构化进度。

设计要点：
- parse_markdown 是纯函数（输入文本 → 输出结构），不碰文件系统，便于测试
- 文件不存在/读取失败时降级返回空结构 + missing 标记，前端显示占位而非报错
- 解析规则只认两样东西：## 当前阶段 下的 - [x] 复选框，## 测验记录 下的 | 表格行
"""
import os
import re

# workbench/ 的上级目录 = 项目根（study_progress.md 所在处）
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PROGRESS_FILE = os.path.join(PROJECT_ROOT, "study_progress.md")

_EMPTY = {"subject": "", "updated": "", "stages": [], "chapters": [],
          "done_count": 0, "total_count": 0, "missing": False}


def parse_markdown(text: str) -> dict:
    result = {"subject": "", "updated": "", "stages": [], "chapters": [],
              "done_count": 0, "total_count": 0, "missing": False}
    in_stages = False
    in_table = False
    for raw in text.splitlines():
        line = raw.strip()
        if line.startswith("- 科目："):
            result["subject"] = line.split("：", 1)[1].strip()
        elif line.startswith("- 最后更新："):
            # 真实文件可能是 "2026-08-02（导入日）"，只取日期部分
            m = re.search(r"\d{4}-\d{2}-\d{2}", line)
            if m:
                result["updated"] = m.group(0)
        elif line.startswith("## "):
            in_stages = line == "## 当前阶段"
            in_table = line == "## 测验记录"
            continue
        if in_stages and line.startswith("- ["):
            m = re.match(r"- \[([ x])\] (.+)", line)
            if m:
                result["stages"].append({"done": m.group(1) == "x", "text": m.group(2)})
        elif in_table and line.startswith("|"):
            cells = [c.strip() for c in line.strip("|").split("|")]
            if cells and cells[0].startswith("ch"):
                result["chapters"].append({"chapter": cells[0], "status": cells[1], "result": cells[2]})
    result["done_count"] = sum(1 for s in result["stages"] if s["done"])
    result["total_count"] = len(result["stages"])
    return result


def load_progress(path: str | None = None) -> dict:
    p = path or PROGRESS_FILE
    try:
        with open(p, "r", encoding="utf-8") as f:
            return parse_markdown(f.read())
    except FileNotFoundError:
        return dict(_EMPTY, missing=True)
