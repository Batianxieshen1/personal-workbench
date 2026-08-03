"""选题灵感池：AI 每天生成 5 条新奇点子 + 手动添加，支持收藏/丢弃。

数据：data/ideas.json
{"ideas": [
  {"id": "hex8", "text": "...", "source": "ai"|"manual",
   "date": "2026-08-03", "status": "kept"|"discarded", "created_at": "..."}
]}

设计要点：
- generate_today 幂等：当天已生成过就返回现有批次，不重复调用 AI（不重复花钱）
- AI 输出约定为每行一个点子（"- "开头），解析失败则整批丢弃
- AI 失败时抛 AIError，由上层提示"AI 不可用"，不残留半批数据
"""
import datetime as dt
import uuid

from . import deepseek
from . import storage

IDEAS_FILE = "ideas.json"
BATCH_SIZE = 5

SYSTEM_PROMPT = (
    "你是创意点子生成器。为一位学习 AI 产品、备考雅思、做内容创作的学生，"
    "生成新奇有趣的选题/灵感点子。要求：贴近日常可执行、有反差感、不落俗套。"
)
USER_PROMPT = (
    f"请生成 {BATCH_SIZE} 个灵感点子。"
    "输出格式严格遵循：每行一个点子，以 \"- \" 开头，不要编号，不要任何多余文字。"
)


def _data() -> dict:
    return storage.load(IDEAS_FILE, {"ideas": []})


def _save(data: dict) -> None:
    storage.save(IDEAS_FILE, data)


def _make_item(text: str, source: str, date: str) -> dict:
    return {
        "id": uuid.uuid4().hex[:8],
        "text": text,
        "source": source,
        "date": date,
        "status": "kept",
        "note": "",
        "outcome": "",
        "created_at": dt.datetime.now().isoformat(),
    }


def get_today(date: str | None = None) -> list:
    d = date or dt.date.today().isoformat()
    return [i for i in _data()["ideas"] if i["date"] == d]


def list_all() -> list:
    items = _data()["ideas"]
    return sorted(items, key=lambda i: i["created_at"], reverse=True)


def generate_today(date: str | None = None) -> list:
    """生成今日批次（幂等：已有则返回现有）。"""
    d = date or dt.date.today().isoformat()
    today_items = get_today(d)
    if today_items:
        return today_items
    raw = deepseek.chat(USER_PROMPT, system=SYSTEM_PROMPT)
    lines = [ln.strip().lstrip("- ").strip() for ln in raw.splitlines() if ln.strip().startswith("-")]
    if not lines:
        raise deepseek.AIError("AI 返回格式无法解析", reason="bad_format")
    data = _data()
    for text in lines[:BATCH_SIZE]:
        data["ideas"].append(_make_item(text, "ai", d))
    _save(data)
    return get_today(d)


def add_manual(text: str, date: str | None = None) -> dict:
    d = date or dt.date.today().isoformat()
    item = _make_item(text.strip(), "manual", d)
    data = _data()
    data["ideas"].append(item)
    _save(data)
    return item


def set_status(idea_id: str, status: str) -> dict:
    data = _data()
    for i in data["ideas"]:
        if i["id"] == idea_id:
            i["status"] = status
            _save(data)
            return i
    raise KeyError(idea_id)


def set_note(idea_id: str, note: str) -> dict:
    """更新灵感备注/细化思路。"""
    data = _data()
    for i in data["ideas"]:
        if i["id"] == idea_id:
            i["note"] = note.strip()
            _save(data)
            return i
    raise KeyError(idea_id)


def set_outcome(idea_id: str, outcome: str) -> dict:
    """记录已采用灵感的产出：链接 + 效果（自由文本）。"""
    data = _data()
    for i in data["ideas"]:
        if i["id"] == idea_id:
            i["outcome"] = outcome.strip()
            _save(data)
            return i
    raise KeyError(idea_id)
