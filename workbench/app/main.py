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
from . import plan as plan_mod
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
        # ── M2/M3 填充 ──
        "progress": None,     # 学习进度（M2）
        "ielts": None,        # 雅思速览（M2）
        "ideas_today": [],    # 今日灵感（M3）
        "review_due": 0,      # 生词到期数（M2）
    }


# ── 静态前端（必须最后挂载）───────────────────────────────
app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")
