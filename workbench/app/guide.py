"""今日行动指南：根据各模块状态自动生成行动清单（按优先级排序）。

规则（priority 越小越靠前）：
1. 今日计划为空 → 先定计划；有计划但未开始 → 开始执行
2. 生词到期 → 复习
3. 今日 AI 灵感全部未处理 → 留/丢
4. 学习进度未完成 → 继续学习
5. 今日总结未写 → 睡前写总结

每条行动：{id, priority, text, page, target}，前端可一键跳转并聚焦 target。
"""
import datetime as dt

from . import ideas
from . import plan
from . import progress
from . import reviews
from . import vocab


def build_guide(today: str | None = None) -> list:
    d = today or dt.date.today().isoformat()
    actions = []

    # 1. 今日计划
    p = plan.get_plan(d)
    if not p["items"]:
        actions.append({
            "id": "plan", "priority": 1,
            "text": "先给今天定几件最重要的事",
            "page": "home", "target": "plan-input",
        })
    elif not any(i["done"] for i in p["items"]):
        actions.append({
            "id": "plan-start", "priority": 1,
            "text": f"开始执行今日计划（{len(p['items'])} 项待完成）",
            "page": "home", "target": "plan-list",
        })

    # 2. 生词到期
    due = vocab.due_words(d)
    if due:
        actions.append({
            "id": "vocab", "priority": 2,
            "text": f"复习 {len(due)} 个到期生词（艾宾浩斯不等人）",
            "page": "ielts", "target": "vocab-due-list",
        })

    # 3. 今日 AI 灵感未处理（全部 kept 视为没看过）
    today_ai = [i for i in ideas.get_today(d) if i["source"] == "ai"]
    if today_ai and all(i["status"] == "kept" for i in today_ai):
        actions.append({
            "id": "ideas", "priority": 3,
            "text": "处理今日灵感：留下 / 丢弃 / 采用",
            "page": "ideas", "target": "ideas-today-list",
        })

    # 4. 学习进度
    pr = progress.load_progress()
    if not pr.get("missing") and pr["done_count"] < pr["total_count"]:
        actions.append({
            "id": "study", "priority": 4,
            "text": f"继续学习：完成下一个阶段（{pr['done_count']}/{pr['total_count']}）",
            "page": "study", "target": "study-stages",
        })

    # 5. 今日总结
    r = reviews.get_review(d)
    if not r["summary"]:
        actions.append({
            "id": "review", "priority": 5,
            "text": "睡前写今日总结",
            "page": "review", "target": "review-summary",
        })

    return sorted(actions, key=lambda a: a["priority"])
