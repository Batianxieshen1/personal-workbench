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
from . import ielts as ielts_mod
from . import plan as plan_mod
from . import progress as progress_mod
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


# ── 学习进度 ──────────────────────────────────────────────
@app.get("/api/progress")
def api_progress():
    return progress_mod.load_progress()


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
def api_review_vocab(word_id: str):
    try:
        return vocab_mod.review(word_id)
    except KeyError:
        raise HTTPException(404, f"生词不存在：{word_id}")


@app.delete("/api/vocab/{word_id}")
def api_delete_vocab(word_id: str):
    try:
        vocab_mod.delete_word(word_id)
        return {"ok": True}
    except KeyError:
        raise HTTPException(404, f"生词不存在：{word_id}")


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
        "ideas_today": [],               # 今日灵感（M3）
        "review_due": len(vocab_mod.due_words()),
    }


# ── 静态前端（必须最后挂载）───────────────────────────────
app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")
