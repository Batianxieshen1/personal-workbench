"""雅思生词本：艾宾浩斯间隔复习。

复习节奏：添加后第 1 / 3 / 7 / 14 / 30 天各复习一次，全部完成即"毕业"。

词条结构：
{
  "id": "a1b2c3d4",
  "word": "abandon",
  "meaning": "v. 放弃",
  "added": "2026-08-03",   # 添加日期
  "stage": 0,               # 已完成复习次数
  "next": "2026-08-04",     # 下次复习日期；毕业为 null
}

设计要点：
- _next_date 是纯函数（stage + base 日期 → 下次复习日期），日期注入便于测试
- review 打卡以"当天"为基准推进下一阶段：今天复习完，N 天后回来
- 到期判断用字符串比较（ISO 格式 YYYY-MM-DD 字典序 = 时间序），避免时区坑
"""
import datetime as dt
import uuid

from . import storage

REVIEW_INTERVALS = [1, 3, 7, 14, 30]
VOCAB_FILE = "vocab.json"


def _today() -> dt.date:
    return dt.date.today()


def _next_date(stage: int, base: dt.date) -> str | None:
    """第 stage 次复习后，下一次复习日期；stage 超过间隔表长度则毕业。"""
    if stage >= len(REVIEW_INTERVALS):
        return None
    return (base + dt.timedelta(days=REVIEW_INTERVALS[stage])).isoformat()


def _data() -> dict:
    return storage.load(VOCAB_FILE, {"words": []})


def _save(data: dict) -> None:
    storage.save(VOCAB_FILE, data)


def list_words() -> list:
    return _data()["words"]


def add_word(word: str, meaning: str) -> dict:
    w = {
        "id": uuid.uuid4().hex[:8],
        "word": word.strip(),
        "meaning": meaning.strip(),
        "added": _today().isoformat(),
        "stage": 0,
        "next": _next_date(0, _today()),
    }
    data = _data()
    data["words"].append(w)
    _save(data)
    return w


def update_meaning(word_id: str, meaning: str) -> dict:
    data = _data()
    for w in data["words"]:
        if w["id"] == word_id:
            w["meaning"] = meaning.strip()
            _save(data)
            return w
    raise KeyError(word_id)


def review(word_id: str) -> dict:
    """复习打卡：stage +1，按新 stage 排下一次复习。"""
    data = _data()
    for w in data["words"]:
        if w["id"] == word_id:
            w["stage"] += 1
            w["next"] = _next_date(w["stage"], _today())
            _save(data)
            return w
    raise KeyError(word_id)


def delete_word(word_id: str) -> None:
    data = _data()
    before = len(data["words"])
    data["words"] = [w for w in data["words"] if w["id"] != word_id]
    if len(data["words"]) == before:
        raise KeyError(word_id)
    _save(data)


def due_words(today: str | None = None) -> list:
    """到期队列：next <= today 且未毕业（next 非 null）。"""
    t = today or _today().isoformat()
    return [w for w in list_words() if w["next"] is not None and w["next"] <= t]
