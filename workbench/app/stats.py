"""统计：从 data/ 聚合使用数据（连续天数/完成率/词汇/灵感）。"""
import datetime as dt
import os

from . import ideas
from . import storage
from . import vocab


def _plan_days() -> list:
    """所有有计划的日期列表 [(date_str, plan_dict)]，按日期升序。"""
    plans_dir = os.path.join(storage.DATA_DIR, "plans")
    if not os.path.isdir(plans_dir):
        return []
    days = []
    for name in sorted(os.listdir(plans_dir)):
        if name.endswith(".json"):
            d = name[:-5]
            days.append((d, storage.load(f"plans/{name}", {"date": d, "items": []})))
    return days


def streak_days(today: str | None = None) -> int:
    """连续完成计划的学习天数（含今天；今天未完成则从昨天往回数）。"""
    done_days = {d for d, p in _plan_days() if any(i["done"] for i in p["items"])}
    t = dt.date.fromisoformat(today) if today else dt.date.today()
    streak = 0
    cur = t
    while cur.isoformat() in done_days:
        streak += 1
        cur -= dt.timedelta(days=1)
    return streak


def week_completion(week_start: str) -> dict:
    """周完成率：week_start 为该周周一日期。"""
    start = dt.date.fromisoformat(week_start)
    total = done = 0
    for i in range(7):
        d = (start + dt.timedelta(days=i)).isoformat()
        for dd, p in _plan_days():
            if dd != d:
                continue
            for it in p["items"]:
                total += 1
                if it["done"]:
                    done += 1
    return {"total": total, "done": done, "rate": round(done / total, 2) if total else 0}


def vocab_stats(today: str | None = None) -> dict:
    words = vocab.list_words()
    t = today or dt.date.today().isoformat()
    return {
        "total": len(words),
        "active": sum(1 for w in words if w["stage"] < 5),
        "graduated": sum(1 for w in words if w["stage"] >= 5),
        "added_today": sum(1 for w in words if w["added"] == t),
    }


def idea_stats() -> dict:
    items = ideas.list_all()
    done = sum(1 for i in items if i["status"] == "done")
    return {
        "total": len(items),
        "kept": sum(1 for i in items if i["status"] == "kept"),
        "done": done,
        "discarded": sum(1 for i in items if i["status"] == "discarded"),
        "adopt_rate": round(done / len(items), 2) if items else 0,
    }


def build_stats(today: str | None = None) -> dict:
    t = today or dt.date.today().isoformat()
    # 本周周一
    d = dt.date.fromisoformat(t)
    monday = d - dt.timedelta(days=d.weekday())
    return {
        "streak_days": streak_days(t),
        "week": week_completion(monday.isoformat()),
        "vocab": vocab_stats(t),
        "ideas": idea_stats(),
    }
