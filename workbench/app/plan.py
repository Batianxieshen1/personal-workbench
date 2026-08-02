"""今日计划：按天存储（data/plans/YYYY-MM-DD.json），支持增删、勾选、改文字。

设计要点：
- 每个任务项有独立 id（uuid 前 8 位），前端勾选/删除靠 id 而不是文字，避免重名任务互相干扰
- 找不到 id 时抛 KeyError，由上层路由转成 404
"""
import datetime as dt
import uuid

from . import storage


def _file(d: str) -> str:
    return f"plans/{d}.json"


def get_plan(d: str | None = None) -> dict:
    d = d or dt.date.today().isoformat()
    return storage.load(_file(d), {"date": d, "items": []})


def add_item(d: str, text: str) -> dict:
    plan = get_plan(d)
    item = {
        "id": uuid.uuid4().hex[:8],
        "text": text.strip(),
        "done": False,
    }
    plan["items"].append(item)
    storage.save(_file(d), plan)
    return plan


def update_item(d: str, item_id: str, done: bool | None = None, text: str | None = None) -> dict:
    plan = get_plan(d)
    for it in plan["items"]:
        if it["id"] == item_id:
            if done is not None:
                it["done"] = done
            if text is not None:
                it["text"] = text.strip()
            break
    else:
        raise KeyError(item_id)
    storage.save(_file(d), plan)
    return plan


def delete_item(d: str, item_id: str) -> dict:
    plan = get_plan(d)
    before = len(plan["items"])
    plan["items"] = [it for it in plan["items"] if it["id"] != item_id]
    if len(plan["items"]) == before:
        raise KeyError(item_id)
    storage.save(_file(d), plan)
    return plan
