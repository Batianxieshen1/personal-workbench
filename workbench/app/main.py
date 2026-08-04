"""个人工作台后端：FastAPI 路由 + 静态前端挂载。

路由顺序约定：/api/* 全部定义在前，最后 app.mount("/", ...) 挂静态文件——
FastAPI 按注册顺序匹配，这样静态挂载不会抢走 API 请求。
"""
import datetime as dt
import os

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import config as config_mod
from . import deepseek
from . import guide as guide_mod
from . import ideas as ideas_mod
from . import ielts as ielts_mod
from . import links as links_mod
from . import obsidian as obsidian_mod
from . import plan as plan_mod
from . import progress as progress_mod
from . import reviews as reviews_mod
from . import stats as stats_mod
from . import tools as tools_mod
from . import vocab as vocab_mod
from . import weather as weather_mod

app = FastAPI(title="个人工作台", version="0.1.0")

STATIC_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "static")


# ── 请求体模型 ─────────────────────────────────────────────
class PlanItemIn(BaseModel):
    date: str | None = None
    text: str


class PlanItemPatch(BaseModel):
    date: str | None = None
    done: bool | None = None
    text: str | None = None
    important: bool | None = None


class CityIn(BaseModel):
    city: str


class NicknameIn(BaseModel):
    nickname: str


class IeltsPatch(BaseModel):
    target_score: float | None = None
    current_band: str | None = None
    stage: str | None = None
    exam_date: str | None = None
    skills: dict | None = None


class VocabIn(BaseModel):
    word: str
    meaning: str


class VocabPatch(BaseModel):
    meaning: str


class IdeaIn(BaseModel):
    text: str


class IdeaPatch(BaseModel):
    status: str | None = None
    note: str | None = None
    outcome: str | None = None


class ReviewIn(BaseModel):
    date: str
    summary: str = ""


class WeekIn(BaseModel):
    week: str
    summary: str = ""


class DouyinIn(BaseModel):
    text: str
    ocr: bool = False


class CoordsIn(BaseModel):
    city: str
    lat: float
    lon: float


class LinkIn(BaseModel):
    title: str
    url: str
    note: str = ""


class LinkPatch(BaseModel):
    title: str | None = None
    url: str | None = None
    note: str | None = None


# ── 今日计划 ───────────────────────────────────────────────
@app.get("/api/plan")
def api_get_plan(date: str | None = None):
    return plan_mod.get_plan(date)


@app.post("/api/plan/items")
def api_add_item(body: PlanItemIn):
    d = body.date or dt.date.today().isoformat()
    return plan_mod.add_item(d, body.text)


@app.patch("/api/plan/items/{item_id}")
def api_update_item(item_id: str, body: PlanItemPatch):
    d = body.date or dt.date.today().isoformat()
    try:
        return plan_mod.update_item(d, item_id, done=body.done, text=body.text)
    except KeyError:
        raise HTTPException(404, f"任务不存在：{item_id}")


@app.delete("/api/plan/items/{item_id}")
def api_delete_item(item_id: str, date: str | None = None):
    d = date or dt.date.today().isoformat()
    try:
        return plan_mod.delete_item(d, item_id)
    except KeyError:
        raise HTTPException(404, f"任务不存在：{item_id}")


# ── 天气 ───────────────────────────────────────────────────
@app.get("/api/weather")
def api_weather():
    cfg = config_mod.get_config()
    try:
        return weather_mod.fetch_weather(cfg["lat"], cfg["lon"])
    except Exception:
        # 降级：天气挂了不阻塞页面，前端显示占位
        return {"temp": None, "humidity": None, "desc": "—", "icon": "🌡️", "error": True}


# ── 配置 ───────────────────────────────────────────────────
@app.get("/api/config")
def api_get_config():
    return config_mod.get_config()


@app.patch("/api/config/city")
def api_set_city(body: CityIn):
    try:
        return config_mod.set_city(body.city)
    except ValueError as e:
        raise HTTPException(400, str(e))


@app.patch("/api/config/nickname")
def api_set_nickname(body: NicknameIn):
    return config_mod.set_nickname(body.nickname)


@app.patch("/api/config/coords")
def api_set_coords(body: CoordsIn):
    return config_mod.set_coords(body.city, body.lat, body.lon)


# ── 学习进度 ──────────────────────────────────────────────
@app.get("/api/progress")
def api_progress():
    return progress_mod.load_progress()


@app.get("/api/plan-info")
def api_plan_info():
    return progress_mod.load_plan()


class StagePatch(BaseModel):
    done: bool


@app.patch("/api/progress/stages/{index}")
def api_toggle_stage(index: int, body: StagePatch):
    try:
        return progress_mod.toggle_stage(progress_mod.PROGRESS_FILE, index, body.done)
    except IndexError:
        raise HTTPException(404, f"阶段不存在：{index}")


# ── 雅思 ───────────────────────────────────────────────────
@app.get("/api/ielts")
def api_get_ielts():
    return ielts_mod.get_ielts()


@app.patch("/api/ielts")
def api_patch_ielts(body: IeltsPatch):
    return ielts_mod.update_ielts(body.model_dump(exclude_none=True))


# ── 生词本 ─────────────────────────────────────────────────
# 注意：/api/vocab/due 必须注册在 /api/vocab/{word_id} 之前，
# 否则 FastAPI 会把 "due" 当成 word_id 匹配
@app.get("/api/vocab")
def api_list_vocab():
    return vocab_mod.list_words()


@app.get("/api/vocab/due")
def api_due_vocab():
    return vocab_mod.due_words()


@app.post("/api/vocab")
def api_add_vocab(body: VocabIn):
    return vocab_mod.add_word(body.word, body.meaning)


@app.patch("/api/vocab/{word_id}")
def api_update_vocab(word_id: str, body: VocabPatch):
    try:
        return vocab_mod.update_meaning(word_id, body.meaning)
    except KeyError:
        raise HTTPException(404, f"生词不存在：{word_id}")


@app.post("/api/vocab/{word_id}/review")
def api_review_vocab(word_id: str, body: dict | None = None):
    known = True
    if body and isinstance(body.get("known"), bool):
        known = body["known"]
    try:
        return vocab_mod.review(word_id, known=known)
    except KeyError:
        raise HTTPException(404, f"生词不存在：{word_id}")


@app.delete("/api/vocab/{word_id}")
def api_delete_vocab(word_id: str):
    try:
        vocab_mod.delete_word(word_id)
        return {"ok": True}
    except KeyError:
        raise HTTPException(404, f"生词不存在：{word_id}")


# ── 灵感 ───────────────────────────────────────────────────
@app.get("/api/ideas")
def api_list_ideas():
    return ideas_mod.list_all()


@app.post("/api/ideas/generate")
def api_generate_ideas():
    """生成今日批次（幂等）；AI 失败返回 503 + 原因，前端降级提示。"""
    try:
        return ideas_mod.generate_today()
    except deepseek.AIError as e:
        raise HTTPException(503, {"reason": e.reason, "message": str(e)})


@app.post("/api/ideas")
def api_add_idea(body: IdeaIn):
    return ideas_mod.add_manual(body.text)


@app.patch("/api/ideas/{idea_id}")
def api_set_idea_status(idea_id: str, body: IdeaPatch):
    try:
        if body.status is not None:
            return ideas_mod.set_status(idea_id, body.status)
        if body.outcome is not None:
            return ideas_mod.set_outcome(idea_id, body.outcome)
        return ideas_mod.set_note(idea_id, body.note or "")
    except KeyError:
        raise HTTPException(404, f"灵感不存在：{idea_id}")


# ── 复盘 ───────────────────────────────────────────────────
@app.get("/api/reviews")
def api_get_review(date: str | None = None):
    return reviews_mod.get_review(date)


@app.post("/api/reviews")
def api_save_review(body: ReviewIn):
    return reviews_mod.save_review(body.date, body.summary)


@app.post("/api/reviews/ai-draft")
def api_review_ai_draft(body: ReviewIn):
    try:
        return {"draft": reviews_mod.ai_draft(body.date)}
    except deepseek.AIError as e:
        raise HTTPException(503, {"reason": e.reason, "message": str(e)})


@app.get("/api/reviews/content")
def api_content_review():
    return reviews_mod.content_review()


@app.post("/api/reviews/sync-obsidian")
def api_sync_obsidian(body: ReviewIn):
    """把今日总结追加到 Obsidian 日记。"""
    try:
        path = obsidian_mod.sync_daily_review(body.date, body.summary)
        return {"ok": True, "path": path}
    except ValueError as e:
        raise HTTPException(400, str(e))


@app.get("/api/weekly")
def api_get_weekly(week: str):
    return reviews_mod.get_weekly(week)


@app.post("/api/weekly/ai-draft")
def api_weekly_ai_draft(body: WeekIn):
    try:
        return {"draft": reviews_mod.weekly_draft(body.week)}
    except deepseek.AIError as e:
        raise HTTPException(503, {"reason": e.reason, "message": str(e)})


@app.post("/api/weekly")
def api_save_weekly(body: WeekIn):
    return reviews_mod.save_weekly(body.week, body.summary)


# ── 快捷工具 ──────────────────────────────────────────────
@app.post("/api/tools/douyin")
def api_douyin_start(body: DouyinIn):
    try:
        return {"job_id": tools_mod.start_job(body.text, ocr=body.ocr)}
    except ValueError as e:
        raise HTTPException(400, str(e))


# 注意：/history 必须注册在 /{job_id} 之前
@app.get("/api/tools/douyin/history")
def api_douyin_history():
    return tools_mod.list_jobs()


@app.get("/api/tools/douyin/{job_id}")
def api_douyin_status(job_id: str):
    job = tools_mod.get_job(job_id)
    if not job:
        raise HTTPException(404, f"任务不存在：{job_id}")
    return job


# ── Obsidian 联动 ──────────────────────────────────────────
@app.get("/api/obsidian/daily")
def api_obsidian_daily(date: str | None = None):
    d = date or dt.date.today().isoformat()
    return {"uri": obsidian_mod.daily_uri(d)}


@app.get("/api/obsidian/vault")
def api_obsidian_vault():
    return {"uri": obsidian_mod.vault_uri()}


@app.get("/api/obsidian/study-note")
def api_obsidian_study_note():
    return {"uri": obsidian_mod.study_note_uri()}


# ── 资源收藏 ───────────────────────────────────────────────
@app.get("/api/links")
def api_list_links():
    return links_mod.list_all()


@app.post("/api/links")
def api_add_link(body: LinkIn):
    try:
        return links_mod.add(body.title, body.url, body.note)
    except ValueError as e:
        raise HTTPException(400, str(e))


@app.patch("/api/links/{link_id}")
def api_update_link(link_id: str, body: LinkPatch):
    try:
        return links_mod.update(link_id, title=body.title, url=body.url, note=body.note)
    except KeyError:
        raise HTTPException(404, f"收藏不存在：{link_id}")
    except ValueError as e:
        raise HTTPException(400, str(e))


@app.delete("/api/links/{link_id}")
def api_delete_link(link_id: str):
    try:
        links_mod.delete(link_id)
        return {"ok": True}
    except KeyError:
        raise HTTPException(404, f"收藏不存在：{link_id}")


# ── 数据导出 ───────────────────────────────────────────────
@app.get("/api/export")
def api_export():
    """打包 data/ 全部 JSON 为 zip 下载。"""
    import io
    import os
    import zipfile

    buf = io.BytesIO()
    data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        if os.path.isdir(data_dir):
            for root, _dirs, files in os.walk(data_dir):
                for name in files:
                    full = os.path.join(root, name)
                    zf.write(full, os.path.relpath(full, data_dir))
    buf.seek(0)
    from fastapi.responses import StreamingResponse
    return StreamingResponse(
        buf,
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename=workbench-data-{dt.date.today().isoformat()}.zip"},
    )


# ── 统计 ───────────────────────────────────────────────────
@app.get("/api/stats")
def api_stats():
    return stats_mod.build_stats()


# ── 今日行动指南 ──────────────────────────────────────────
@app.get("/api/guide")
def api_guide():
    return guide_mod.build_guide()


@app.get("/api/guide/nav")
def api_guide_nav():
    """AI 晨间导航（当天缓存）。"""
    return guide_mod.morning_nav()


@app.get("/api/ideas/best")
def api_best_idea():
    """AI 挑今日最佳灵感（无灵感/失败返回 null）。"""
    return guide_mod.best_idea_today()


# ── 首页聚合 ───────────────────────────────────────────────
@app.get("/api/overview")
def api_overview():
    cfg = config_mod.get_config()
    d = dt.date.today().isoformat()
    return {
        "date": d,
        "nickname": cfg["nickname"],
        "city": cfg["city"],
        "plan": plan_mod.get_plan(d),
        "weather": api_weather(),
        "progress": progress_mod.load_progress(),
        "ielts": ielts_mod.get_ielts(),
        "ideas_today": [i["text"] for i in ideas_mod.get_today(d) if i["status"] == "kept"],
        "review_due": len(vocab_mod.due_words()),
    }


# ── 静态前端（必须最后挂载）───────────────────────────────
app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")
