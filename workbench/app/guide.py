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

from . import deepseek
from . import ideas
from . import plan
from . import progress
from . import reviews
from . import storage
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


# ── AI 晨间导航（当天缓存，不重复调 AI） ────────────────────

_nav_cache: dict[str, dict] = {}
# 最多保留最近 7 天的导航缓存（防止无限增长）
MAX_NAV_CACHE_DAYS = 7

_NAV_SYSTEM = "你是清晨导航员：基于用户的真实数据，用 3 句话告诉他今天最重要的是什么、为什么、怎么开始。语气温暖简洁，不要列清单。"


def _trim_nav_cache() -> None:
    """丢弃 7 天前的缓存条目。"""
    cutoff = (dt.date.today() - dt.timedelta(days=MAX_NAV_CACHE_DAYS)).isoformat()
    for d in [k for k in _nav_cache if k < cutoff]:
        del _nav_cache[d]


def morning_nav(today: str | None = None) -> dict:
    """AI 生成今日导读；当天结果缓存（重启丢失可接受）。失败降级返回 error。"""
    d = today or dt.date.today().isoformat()
    if d in _nav_cache:
        return _nav_cache[d]
    try:
        p = plan.get_plan(d)
        due = vocab.due_words(d)
        today_ideas = ideas.get_today(d)
        r = reviews.get_review(d)
        pr = progress.load_progress()
        plan_lines = "；".join(
            f"{'✅' if i['done'] else '⬜'} {i['text']}" for i in p["items"]
        ) or "（还没定）"
        idea_lines = "；".join(i["text"] for i in today_ideas if i["status"] == "kept") or "（无）"
        context = (
            f"今天是 {d}。\n"
            f"今日计划：{plan_lines}\n"
            f"到期生词：{len(due)} 个\n"
            f"今日灵感：{idea_lines}\n"
            f"学习进度：{pr.get('done_count', 0)}/{pr.get('total_count', 0)}\n"
            f"昨日总结：{r['summary'] or '（未写）'}"
        )
        text = deepseek.chat(
            "请用 3 句话写今天的晨间导航：第一句点出今天最该做的一件事并说明为什么，"
            "第二句给出最小行动建议（今天就能做），第三句鼓励。不要用列表。\n\n" + context,
            system=_NAV_SYSTEM,
        )
        nav = {"date": d, "text": text}
    except deepseek.AIError as e:
        return {"date": d, "error": True, "reason": e.reason}
    _nav_cache[d] = nav
    _trim_nav_cache()
    return nav


# ── AI 挑今日最佳灵感（当天缓存，省 token） ─────────────────

_best_cache: dict[str, dict] = {}

_BEST_SYSTEM = "你是选题策划：从用户今天的灵感里选出最值得先做的一条，一句话说明理由。"


def best_idea_today(today: str | None = None) -> dict | None:
    """今日 kept 灵感中让 AI 选一条最值得做的；无灵感/失败返回 None。

    成功结果按天缓存（当天不重复调 AI）；失败不缓存（下次可重试）。
    """
    d = today or dt.date.today().isoformat()
    if d in _best_cache:
        return _best_cache[d]
    today_ai = [i for i in ideas.get_today(d) if i["status"] == "kept"]
    if not today_ai:
        return None  # 无灵感不耗 AI，无需缓存
    try:
        options = "\n".join(f"{i['id']}: {i['text']}" for i in today_ai)
        reply = deepseek.chat(
            f"从下面今天的灵感中选最值得先做的一条，回复格式严格为：<id> | <一句话理由>。\n{options}",
            system=_BEST_SYSTEM,
        )
        idea_id, _, reason = reply.partition("|")
        idea_id = idea_id.strip()
        # 优先按 id 匹配，其次按文本匹配（AI 可能返回文本），最后取第一条
        target = next((i for i in today_ai if i["id"] == idea_id), None) \
            or next((i for i in today_ai if idea_id in i["text"] or i["text"] in idea_id), None) \
            or today_ai[0]
        result = {"id": target["id"], "text": target["text"], "reason": reason.strip() or "最值得先做"}
    except deepseek.AIError:
        return None  # 失败不缓存，下次重试
    _best_cache[d] = result
    _trim_nav_cache()
    return result
