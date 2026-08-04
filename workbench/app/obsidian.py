"""Obsidian 联动：生成 obsidian:// URI，一键打开日记/知识库。

注意：vault 名是「我的知识库」，文件名是 Obsidian 相对 vault 的路径，
中文和空格需要 URL 编码，否则 Obsidian 无法识别。
"""
import os
import re
from urllib.parse import quote

VAULT = "我的知识库"
DAILY_DIR = "01-日记"
STUDY_NOTE = "03-AI产品/大模型工程师课程/01-认识大模型.md"

# 我的知识库 位于项目根（workbench 的上级）
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
VAULT_DIR = os.path.join(PROJECT_ROOT, VAULT)


def _uri(file_path: str) -> str:
    return f"obsidian://open?vault={quote(VAULT)}&file={quote(file_path)}"


def daily_uri(date: str) -> str:
    """今日日记（不存在时 Obsidian 会提示新建）。"""
    return _uri(f"{DAILY_DIR}/{date}")


def vault_uri() -> str:
    return f"obsidian://open?vault={quote(VAULT)}"


def study_note_uri() -> str:
    return _uri(STUDY_NOTE)


def sync_daily_review(date: str, summary: str) -> str:
    """把今日总结追加到 Obsidian 日记文件（不存在则创建）。

    日期严格校验 YYYY-MM-DD，防止路径穿越写任意文件。
    """
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", date):
        raise ValueError(f"非法日期：{date}")
    daily_dir = os.path.join(VAULT_DIR, DAILY_DIR)
    os.makedirs(daily_dir, exist_ok=True)
    path = os.path.join(daily_dir, f"{date}.md")
    block = f"\n## 📝 今日总结\n{summary}\n"
    if os.path.exists(path):
        with open(path, "a", encoding="utf-8") as f:
            f.write(block)
    else:
        with open(path, "w", encoding="utf-8") as f:
            f.write(f"# {date}\n{block}")
    return path
