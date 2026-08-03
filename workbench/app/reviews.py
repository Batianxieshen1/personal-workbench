"""复盘：每日总结 + 周报（AI 起草，失败降级由上层处理）。

数据：
- data/reviews/YYYY-MM-DD.json  {"date", "summary"}
- data/weekly/YYYY-Www.json     {"week", "summary"}

设计要点：
- ai_draft 把"今日计划完成情况 + 今日灵感"拼进 prompt，让 AI 基于真实数据写总结
- weekly_draft 把本周所有计划与已写总结聚合进 prompt
- 周编号用 ISO 周（week_of），周报按周存文件
"""
import datetime as dt
import os

from . import deepseek
from . import ideas
from . import plan
from . import storage

REVIEW_DIR = "reviews"
WEEKLY_DIR = "weekly"

_SYSTEM = "你是复盘助手：基于用户提供的真实数据，写简洁、具体、有行动建议的复盘。"


def _review_file(d: str) -> str:
    return f"{REVIEW_DIR}/{d}.json"


def _weekly_file(week: str) -> str:
    return f"{WEEKLY_DIR}/{week}.json"


def week_of(date_str: str) -> str:
    y, w, _ = dt.date.fromisoformat(date_str).isocalendar()
    return f"{y}-W{w:02d}"


def get_review(date_str: str | None = None) -> dict:
    d = date_str or dt.date.today().isoformat()
    return storage.load(_review_file(d), {"date": d, "summary": ""})


def save_review(date_str: str, summary: str) -> dict:
    data = {"date": date_str, "summary": summary.strip()}
    storage.save(_review_file(date_str), data)
    return data


def _plan_summary(d: str) -> str:
    p = plan.get_plan(d)
    items = p["items"]
    if not items:
        return "（无计划）"
    done = sum(1 for it in items if it["done"])
    lines = [f"完成 {done}/{len(items)} 项"]
    for it in items:
        mark = "✅" if it["done"] else "⬜"
        lines.append(f"{mark} {it['text']}")
    return "\n".join(lines)


def ai_draft(date_str: str | None = None) -> str:
    """AI 起草每日总结：聚合当日计划完成情况 + 今日灵感。"""
    d = date_str or dt.date.today().isoformat()
    prompt = (
        f"今天是 {d}。今日计划完成情况：\n{_plan_summary(d)}\n\n"
        f"今日灵感：\n" + "\n".join(f"- {i['text']}" for i in ideas.get_today(d)) + "\n\n"
        "请写一份 150 字以内的每日总结：今天完成了什么、有什么收获、明天做什么。"
    )
    return deepseek.chat(prompt, system=_SYSTEM)


def weekly_draft(week: str) -> str:
    """AI 起草周报：聚合本周（ISO 周）所有计划与已写总结。"""
    start = dt.date.fromisocalendar(int(week.split("-W")[0]), int(week.split("W")[1]), 1)
    days = [start + dt.timedelta(days=i) for i in range(7)]
    sections = []
    for day in days:
        d = day.isoformat()
        p = plan.get_plan(d)
        r = get_review(d)
        if not p["items"] and not r["summary"]:
            continue
        lines = [f"【{d}】"]
        lines.append("计划：" + _plan_summary(d).replace("\n", "；"))
        if r["summary"]:
            lines.append(f"总结：{r['summary']}")
        sections.append("\n".join(lines))
    if not sections:
        raise deepseek.AIError("本周还没有任何记录", reason="empty")
    prompt = (
        f"本周（{week}）记录：\n\n" + "\n\n".join(sections) + "\n\n"
        "请写一份 200 字以内的周报：本周概览、亮点、问题、下周重点。"
    )
    return deepseek.chat(prompt, system=_SYSTEM)


def get_weekly(week: str) -> dict:
    return storage.load(_weekly_file(week), {"week": week, "summary": ""})


def save_weekly(week: str, summary: str) -> dict:
    data = {"week": week, "summary": summary.strip()}
    storage.save(_weekly_file(week), data)
    return data
