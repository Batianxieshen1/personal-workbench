"""Obsidian 联动：生成 obsidian:// URI，一键打开日记/知识库。

注意：vault 名是「我的知识库」，文件名是 Obsidian 相对 vault 的路径，
中文和空格需要 URL 编码，否则 Obsidian 无法识别。
"""
from urllib.parse import quote

VAULT = "我的知识库"
DAILY_DIR = "01-日记"
STUDY_NOTE = "03-AI产品/大模型工程师课程/01-认识大模型.md"


def _uri(file_path: str) -> str:
    return f"obsidian://open?vault={quote(VAULT)}&file={quote(file_path)}"


def daily_uri(date: str) -> str:
    """今日日记（不存在时 Obsidian 会提示新建）。"""
    return _uri(f"{DAILY_DIR}/{date}")


def vault_uri() -> str:
    return f"obsidian://open?vault={quote(VAULT)}"


def study_note_uri() -> str:
    return _uri(STUDY_NOTE)
