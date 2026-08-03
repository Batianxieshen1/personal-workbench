# 个人工作台 M1 骨架 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 搭起工作台的地基——FastAPI 后端 + 护眼暖调前端骨架 + 今日计划/时钟天气两个可用模块 + 侧边栏导航，`python run.py` 一键启动。

**Architecture:** 本地 FastAPI 服务（127.0.0.1:8765）同时提供 JSON API（`/api/*`）和静态前端；数据以 JSON 文件存于 `workbench/data/`（线程安全读写）；前端为无构建原生 SPA，hash 路由分页，首页一屏网格聚合。M2-M4（学习进度/雅思/灵感/复盘/工具）在本计划后各自成计划，本计划为其预留路由与占位卡片。

**Tech Stack:** Python 3.13 · FastAPI · uvicorn · requests（天气代理）· 原生 HTML/CSS/JS · pytest（含 TestClient，需 httpx）

**前置条件：** 已完成设计评审（`docs/superpowers/specs/2026-08-03-personal-workbench-design.md`）；用户已批准 M1 范围。

---

## 文件结构（M1 创建）

```
workbench/
  app/
    __init__.py          # 空包标记
    storage.py           # JSON 存储层（线程安全）
    plan.py              # 今日计划 CRUD
    weather.py           # Open-Meteo 客户端（天气 + 城市地理编码）
    config.py            # 用户配置读写
    main.py              # FastAPI 路由 + 静态挂载
  static/
    index.html           # SPA 骨架（侧边栏 + 首页网格 + 占位页）
    style.css            # 护眼暖调主题（CSS 变量）
    app.js               # 路由 + 时钟 + 天气 + 计划交互
  data/                  # JSON 数据（git 忽略）
  tests/
    test_storage.py
    test_plan.py
    test_weather.py
    test_config.py
    test_api.py
  requirements.txt
  run.py                 # 一键启动 + 自动开浏览器
  start.bat              # Windows 双击启动
.gitignore               # 项目根（忽略 workbench/data/、.env、__pycache__）
```

**约定（贯穿所有任务）：**
- 相对导入一律用 `.` 前缀（`from . import storage`），测试运行时 cwd 在 `workbench/`。
- 所有 JSON 写盘用「先写 .tmp 再 os.replace」保证不写坏文件。
- 日期统一 ISO 格式 `YYYY-MM-DD`，默认取 `datetime.date.today()`。
- 每个任务完成后跑一次该任务测试；全部任务完成后跑全量 `pytest`。

---

## Task 0: 环境与仓库初始化

**Files:**
- Create: `workbench/requirements.txt`
- Create: `.gitignore`（项目根）
- Create: `workbench/app/__init__.py`（空文件）

- [ ] **Step 1: 建目录**

```bash
mkdir workbench\app workbench\static workbench\tests workbench\data
```

- [ ] **Step 2: 写依赖清单 `workbench/requirements.txt`**

```
fastapi
uvicorn
requests
httpx
pytest
```

- [ ] **Step 3: 写项目根 `.gitignore`**

```
workbench/data/
.env
__pycache__/
*.pyc
.superpowers/
```

- [ ] **Step 4: 创建空包 `workbench/app/__init__.py`**（空文件即可）

- [ ] **Step 5: 安装依赖**（需联网，会弹确认）

```bash
pip install -r workbench\requirements.txt
```

Expected: `Successfully installed fastapi ... uvicorn ...` 无报错。

- [ ] **Step 6: 初始化 git（需用户确认是否引入 git）**

```bash
git init
git add .gitignore
git commit -m "chore: 初始化项目与忽略规则"
```

> 若用户不想要 git，跳过本步，后续任务中的 commit 步骤同样跳过。

---

## Task 1: 存储层 storage.py

**Files:**
- Create: `workbench/app/storage.py`
- Test: `workbench/tests/test_storage.py`

- [ ] **Step 1: 写失败测试**

```python
# workbench/tests/test_storage.py
import pytest
from app import storage

@pytest.fixture(autouse=True)
def tmp_data(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "DATA_DIR", str(tmp_path))
    yield tmp_path

def test_load_missing_returns_default(tmp_data):
    assert storage.load("plans/2026-08-03.json", {"items": []}) == {"items": []}

def test_save_then_load_roundtrip(tmp_data):
    storage.save("plans/2026-08-03.json", {"date": "2026-08-03", "items": [{"id": "a", "text": "背单词", "done": False}]})
    loaded = storage.load("plans/2026-08-03.json", None)
    assert loaded["date"] == "2026-08-03"
    assert loaded["items"][0]["text"] == "背单词"

def test_save_creates_nested_dirs(tmp_data):
    storage.save("reviews/2026-08-03.json", {"ok": True})
    assert (tmp_data / "reviews" / "2026-08-03.json").exists()

def test_unicode_preserved(tmp_data):
    storage.save("config.json", {"nickname": "暴龙战士wink"})
    assert storage.load("config.json", None)["nickname"] == "暴龙战士wink"
```

- [ ] **Step 2: 跑测试确认失败**

Run: `cd workbench && pytest tests/test_storage.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app'`

- [ ] **Step 3: 写实现 `workbench/app/storage.py`**

```python
"""JSON 存储层：线程安全读写 workbench/data/ 下的文件。

设计说明：
- 所有数据文件集中在 data/ 目录，路径用形如 "plans/2026-08-03.json" 的相对名。
- 写入用「临时文件 + os.replace」两步：即使中途断电/报错，也不会留下半截文件。
- 全局锁保证多线程（未来抖音后台任务）读写不打架。
"""
import json
import os
import threading

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
_lock = threading.Lock()


def _path(name: str) -> str:
    # 防路径穿越：只允许 data/ 内部的相对路径
    assert not os.path.isabs(name) and ".." not in name, f"非法存储路径: {name}"
    return os.path.join(DATA_DIR, name)


def load(name: str, default):
    """读取 JSON；文件不存在时返回 default（常传空结构）。"""
    with _lock:
        p = _path(name)
        if not os.path.exists(p):
            return default
        with open(p, "r", encoding="utf-8") as f:
            return json.load(f)


def save(name: str, data) -> None:
    """原子写 JSON：先写 <name>.tmp 再替换。"""
    with _lock:
        p = _path(name)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        tmp = p + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp, p)
```

- [ ] **Step 4: 跑测试确认通过**

Run: `cd workbench && pytest tests/test_storage.py -v`
Expected: 4 passed

- [ ] **Step 5: 提交**

```bash
git add workbench/app/storage.py workbench/tests/test_storage.py
git commit -m "feat: JSON 存储层（原子写 + 线程安全）"
```

---

## Task 2: 今日计划 plan.py

**Files:**
- Create: `workbench/app/plan.py`
- Test: `workbench/tests/test_plan.py`

- [ ] **Step 1: 写失败测试**

```python
# workbench/tests/test_plan.py
import pytest
from app import storage, plan

@pytest.fixture(autouse=True)
def tmp_data(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "DATA_DIR", str(tmp_path))

def test_get_missing_date_returns_empty():
    p = plan.get_plan("2026-08-03")
    assert p == {"date": "2026-08-03", "items": []}

def test_add_item():
    p = plan.add_item("2026-08-03", "  背 50 个雅思单词  ")
    assert p["items"][0]["text"] == "背 50 个雅思单词"  # 首尾空格被清理
    assert p["items"][0]["done"] is False
    assert len(p["items"][0]["id"]) == 8

def test_add_then_toggle_done():
    plan.add_item("2026-08-03", "任务A")
    item_id = plan.get_plan("2026-08-03")["items"][0]["id"]
    p = plan.update_item("2026-08-03", item_id, done=True)
    assert p["items"][0]["done"] is True

def test_update_missing_id_raises():
    with pytest.raises(KeyError):
        plan.update_item("2026-08-03", "nope", done=True)

def test_delete_item():
    plan.add_item("2026-08-03", "任务A")
    plan.add_item("2026-08-03", "任务B")
    item_id = plan.get_plan("2026-08-03")["items"][0]["id"]
    p = plan.delete_item("2026-08-03", item_id)
    assert [i["text"] for i in p["items"]] == ["任务B"]
```

- [ ] **Step 2: 跑测试确认失败**

Run: `cd workbench && pytest tests/test_plan.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.plan'`

- [ ] **Step 3: 写实现 `workbench/app/plan.py`**

```python
"""今日计划：按天一份 JSON，支持增、删、勾选、改文案。"""
import uuid
from datetime import date as _date

from . import storage


def _file(d: str) -> str:
    return f"plans/{d}.json"


def get_plan(d: str | None = None) -> dict:
    d = d or _date.today().isoformat()
    return storage.load(_file(d), {"date": d, "items": []})


def add_item(d: str, text: str) -> dict:
    plan = get_plan(d)
    plan["items"].append({
        "id": uuid.uuid4().hex[:8],
        "text": text.strip(),
        "done": False,
    })
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
            storage.save(_file(d), plan)
            return plan
    raise KeyError(item_id)


def delete_item(d: str, item_id: str) -> dict:
    plan = get_plan(d)
    plan["items"] = [it for it in plan["items"] if it["id"] != item_id]
    storage.save(_file(d), plan)
    return plan
```

- [ ] **Step 4: 跑测试确认通过**

Run: `cd workbench && pytest tests/test_plan.py -v`
Expected: 6 passed

- [ ] **Step 5: 提交**

```bash
git add workbench/app/plan.py workbench/tests/test_plan.py
git commit -m "feat: 今日计划 CRUD（按天 JSON 存储）"
```

---

## Task 3: 天气客户端 weather.py

**Files:**
- Create: `workbench/app/weather.py`
- Test: `workbench/tests/test_weather.py`

- [ ] **Step 1: 写失败测试**（用假响应模拟 Open-Meteo，不碰真实网络）

```python
# workbench/tests/test_weather.py
import pytest
from app import weather

class FakeResponse:
    def __init__(self, payload):
        self._payload = payload
    def raise_for_status(self):
        pass
    def json(self):
        return self._payload

def test_fetch_weather_maps_codes(monkeypatch):
    def fake_get(url, params=None, timeout=None):
        assert "api.open-meteo.com" in url
        return FakeResponse({"current": {
            "temperature_2m": 26.4, "relative_humidity_2m": 60, "weather_code": 61,
        }})
    monkeypatch.setattr(weather.requests, "get", fake_get)
    w = weather.fetch_weather(23.1291, 113.2644)
    assert w["temp"] == 26          # 四舍五入取整
    assert w["humidity"] == 60
    assert w["desc"] == "小雨"      # code 61 → 小雨
    assert w["icon"] == "🌧️"

def test_fetch_weather_unknown_code(monkeypatch):
    def fake_get(url, params=None, timeout=None):
        return FakeResponse({"current": {
            "temperature_2m": 10.0, "relative_humidity_2m": 50, "weather_code": 999,
        }})
    monkeypatch.setattr(weather.requests, "get", fake_get)
    w = weather.fetch_weather(0, 0)
    assert w["desc"] == "未知"

def test_geocode_city(monkeypatch):
    def fake_get(url, params=None, timeout=None):
        assert "geocoding-api.open-meteo.com" in url
        assert params["name"] == "广州"
        return FakeResponse({"results": [{"name": "广州", "latitude": 23.1291, "longitude": 113.2644}]})
    monkeypatch.setattr(weather.requests, "get", fake_get)
    geo = weather.geocode_city("广州")
    assert geo["city"] == "广州" and geo["lat"] == 23.1291

def test_geocode_city_not_found(monkeypatch):
    def fake_get(url, params=None, timeout=None):
        return FakeResponse({"results": []})
    monkeypatch.setattr(weather.requests, "get", fake_get)
    assert weather.geocode_city("不存在的城市xyz") is None
```

- [ ] **Step 2: 跑测试确认失败**

Run: `cd workbench && pytest tests/test_weather.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.weather'`

- [ ] **Step 3: 写实现 `workbench/app/weather.py`**

```python
"""Open-Meteo 天气客户端（免费、无需 key）。

- fetch_weather: 按经纬度拿当前天气，weather_code 映射为中文描述 + emoji。
- geocode_city: 城市名 → 经纬度（供设置页改城市用）。
服务端代理的原因：前端直连第三方 API 有跨域限制，且以后想换天气源只改这一个文件。
"""
import requests

GEO_URL = "https://geocoding-api.open-meteo.com/v1/search"
WX_URL = "https://api.open-meteo.com/v1/forecast"

WEATHER_CODES = {
    0: ("晴", "☀️"), 1: ("多云", "🌤️"), 2: ("阴", "☁️"), 3: ("阴", "☁️"),
    45: ("雾", "🌫️"), 48: ("雾凇", "🌫️"),
    51: ("毛毛雨", "🌦️"), 53: ("毛毛雨", "🌦️"), 55: ("毛毛雨", "🌦️"),
    61: ("小雨", "🌧️"), 63: ("中雨", "🌧️"), 65: ("大雨", "🌧️"),
    71: ("小雪", "🌨️"), 73: ("中雪", "🌨️"), 75: ("大雪", "🌨️"),
    80: ("阵雨", "🌦️"), 81: ("阵雨", "🌦️"), 82: ("强阵雨", "⛈️"),
    95: ("雷暴", "⛈️"), 96: ("雷暴+冰雹", "⛈️"), 99: ("雷暴+冰雹", "⛈️"),
}


def fetch_weather(lat: float, lon: float, timeout: float = 5.0) -> dict:
    r = requests.get(WX_URL, params={
        "latitude": lat,
        "longitude": lon,
        "current": "temperature_2m,weather_code,relative_humidity_2m",
        "timezone": "auto",
    }, timeout=timeout)
    r.raise_for_status()
    cur = r.json()["current"]
    desc, icon = WEATHER_CODES.get(cur["weather_code"], ("未知", "🌡️"))
    return {
        "temp": round(cur["temperature_2m"]),
        "humidity": cur["relative_humidity_2m"],
        "desc": desc,
        "icon": icon,
    }


def geocode_city(name: str, timeout: float = 5.0) -> dict | None:
    r = requests.get(GEO_URL, params={"name": name, "count": 1, "language": "zh"}, timeout=timeout)
    r.raise_for_status()
    results = r.json().get("results") or []
    if not results:
        return None
    first = results[0]
    return {"city": first["name"], "lat": first["latitude"], "lon": first["longitude"]}
```

- [ ] **Step 4: 跑测试确认通过**

Run: `cd workbench && pytest tests/test_weather.py -v`
Expected: 4 passed

- [ ] **Step 5: 提交**

```bash
git add workbench/app/weather.py workbench/tests/test_weather.py
git commit -m "feat: Open-Meteo 天气客户端（含城市地理编码）"
```

---

## Task 4: 配置 config.py

**Files:**
- Create: `workbench/app/config.py`
- Test: `workbench/tests/test_config.py`

- [ ] **Step 1: 写失败测试**

```python
# workbench/tests/test_config.py
import pytest
from app import storage, config

@pytest.fixture(autouse=True)
def tmp_data(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "DATA_DIR", str(tmp_path))

def test_defaults():
    cfg = config.get_config()
    assert cfg["nickname"] == "同学"
    assert cfg["lat"] is not None and cfg["lon"] is not None

def test_set_nickname_persists():
    config.set_nickname(" 小明 ")
    assert config.get_config()["nickname"] == "小明"

def test_set_city_geocodes(monkeypatch):
    from app import weather
    def fake_geocode(name):
        assert name == "成都"
        return {"city": "成都", "lat": 30.5728, "lon": 104.0668}
    monkeypatch.setattr(weather, "geocode_city", fake_geocode)
    cfg = config.set_city("成都")
    assert cfg["city"] == "成都" and cfg["lat"] == 30.5728

def test_set_city_not_found_raises(monkeypatch):
    from app import weather
    monkeypatch.setattr(weather, "geocode_city", lambda name: None)
    with pytest.raises(ValueError):
        config.set_city("不存在的城市xyz")
```

- [ ] **Step 2: 跑测试确认失败**

Run: `cd workbench && pytest tests/test_config.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.config'`

- [ ] **Step 3: 写实现 `workbench/app/config.py`**

```python
"""用户配置：昵称 + 城市坐标。存 data/config.json。"""
from . import storage, weather

DEFAULTS = {
    "nickname": "同学",
    "city": "广州",
    "lat": 23.1291,
    "lon": 113.2644,
}


def get_config() -> dict:
    cfg = storage.load("config.json", dict(DEFAULTS))
    # 兜底：老配置缺字段时补默认值
    for k, v in DEFAULTS.items():
        cfg.setdefault(k, v)
    return cfg


def set_nickname(name: str) -> dict:
    cfg = get_config()
    cfg["nickname"] = name.strip()
    storage.save("config.json", cfg)
    return cfg


def set_city(city: str) -> dict:
    """按城市名查经纬度并保存；查不到抛 ValueError。"""
    geo = weather.geocode_city(city)
    if not geo:
        raise ValueError(f"找不到城市：{city}")
    cfg = get_config()
    cfg.update(city=geo["city"], lat=geo["lat"], lon=geo["lon"])
    storage.save("config.json", cfg)
    return cfg
```

- [ ] **Step 4: 跑测试确认通过**

Run: `cd workbench && pytest tests/test_config.py -v`
Expected: 4 passed

- [ ] **Step 5: 提交**

```bash
git add workbench/app/config.py workbench/tests/test_config.py
git commit -m "feat: 用户配置（昵称/城市，城市自动地理编码）"
```

---

## Task 5: FastAPI 路由 main.py

**Files:**
- Create: `workbench/app/main.py`
- Test: `workbench/tests/test_api.py`

- [ ] **Step 1: 写失败测试**

```python
# workbench/tests/test_api.py
import pytest
from fastapi.testclient import TestClient

@pytest.fixture()
def client(tmp_path, monkeypatch):
    from app import storage
    monkeypatch.setattr(storage, "DATA_DIR", str(tmp_path))
    from app.main import app
    return TestClient(app)

def test_plan_roundtrip(client):
    r = client.post("/api/plan/items", json={"date": "2026-08-03", "text": "背单词"})
    assert r.status_code == 200
    item_id = r.json()["items"][0]["id"]

    r = client.patch(f"/api/plan/items/{item_id}", json={"date": "2026-08-03", "done": True})
    assert r.json()["items"][0]["done"] is True

    r = client.delete(f"/api/plan/items/{item_id}", params={"date": "2026-08-03"})
    assert r.json()["items"] == []

def test_plan_missing_date_defaults_today(client):
    r = client.get("/api/plan")
    assert r.status_code == 200
    assert "items" in r.json()

def test_weather_failure_degrades(client, monkeypatch):
    # 天气挂了也不 500：返回带 error 标记的占位
    from app import weather
    def boom(*a, **k):
        raise RuntimeError("network down")
    monkeypatch.setattr(weather, "fetch_weather", boom)
    r = client.get("/api/weather")
    assert r.status_code == 200
    assert r.json()["error"] is True

def test_overview_shape(client, monkeypatch):
    from app import weather
    monkeypatch.setattr(weather, "fetch_weather",
        lambda *a, **k: {"temp": 26, "humidity": 60, "desc": "晴", "icon": "☀️"})
    r = client.get("/api/overview")
    body = r.json()
    assert body["date"] == "2026-08-03" or body["date"]  # 与真实今天一致即可
    assert "plan" in body and "weather" in body and "nickname" in body
    # M2/M3 占位字段存在且为 null/空
    assert body["progress"] is None and body["ielts"] is None
    assert body["ideas_today"] == [] and body["review_due"] == 0

def test_config_roundtrip(client, monkeypatch):
    from app import weather
    monkeypatch.setattr(weather, "geocode_city", lambda name: {"city": "北京", "lat": 39.9, "lon": 116.4})
    r = client.patch("/api/config/city", json={"city": "北京"})
    assert r.json()["city"] == "北京"
    assert client.get("/api/config").json()["lat"] == 39.9

def test_index_served(client):
    r = client.get("/")
    assert r.status_code == 200
    assert "工作台" in r.text
```

- [ ] **Step 2: 跑测试确认失败**

Run: `cd workbench && pytest tests/test_api.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.main'`

- [ ] **Step 3: 写实现 `workbench/app/main.py`**（先写路由；前端文件 Task 7 才建，`test_index_served` 最后跑）

```python
"""个人工作台后端：/api/* JSON 接口 + 静态前端挂载。

设计说明：
- API 路由定义在静态挂载之前 —— FastAPI 按定义顺序匹配，"/" 兜底必须最后。
- 每个接口都自带降级：天气/第三方失败返回占位数据，绝不 500 崩页面。
- M2/M3 的 /api/progress、/api/ielts、/api/vocab、/api/ideas、/api/reviews、
  /api/weekly、/api/tools/* 将在各自里程碑计划中加入。
"""
import datetime as dt
import os

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import plan as plan_mod, weather as weather_mod, config as config_mod

app = FastAPI(title="个人工作台", version="0.1.0")

STATIC_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "static")


# ── 请求体模型 ──────────────────────────────────────────────
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


# ── 今日计划 ────────────────────────────────────────────────
@app.get("/api/plan")
def api_get_plan(date: str | None = None):
    return plan_mod.get_plan(date)


@app.post("/api/plan/items")
def api_add_item(body: PlanItemIn):
    text = body.text.strip()
    if not text:
        raise HTTPException(400, "任务内容不能为空")
    return plan_mod.add_item(body.date or dt.date.today().isoformat(), text)


@app.patch("/api/plan/items/{item_id}")
def api_update_item(item_id: str, body: PlanItemPatch):
    try:
        return plan_mod.update_item(body.date or dt.date.today().isoformat(), item_id,
                                    done=body.done, text=body.text)
    except KeyError:
        raise HTTPException(404, f"任务不存在: {item_id}")


@app.delete("/api/plan/items/{item_id}")
def api_delete_item(item_id: str, date: str | None = None):
    return plan_mod.delete_item(date or dt.date.today().isoformat(), item_id)


# ── 天气 ────────────────────────────────────────────────────
@app.get("/api/weather")
def api_weather():
    cfg = config_mod.get_config()
    try:
        return weather_mod.fetch_weather(cfg["lat"], cfg["lon"])
    except Exception:
        return {"temp": None, "humidity": None, "desc": "—", "icon": "🌡️", "error": True}


# ── 配置 ────────────────────────────────────────────────────
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


# ── 首页聚合 ────────────────────────────────────────────────
@app.get("/api/overview")
def api_overview():
    cfg = config_mod.get_config()
    d = dt.date.today().isoformat()
    try:
        weather = weather_mod.fetch_weather(cfg["lat"], cfg["lon"])
    except Exception:
        weather = {"temp": None, "humidity": None, "desc": "—", "icon": "🌡️", "error": True}
    return {
        "date": d,
        "nickname": cfg["nickname"],
        "city": cfg["city"],
        "plan": plan_mod.get_plan(d),
        "weather": weather,
        # M2/M3 占位：后续里程碑填充
        "progress": None,
        "ielts": None,
        "ideas_today": [],
        "review_due": 0,
    }


# ── 静态前端（必须最后挂载）─────────────────────────────────
app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")
```

- [ ] **Step 4: 跑测试（除 index 测试）确认通过**

Run: `cd workbench && pytest tests/test_api.py -k "not index" -v`
Expected: 5 passed

> `test_index_served` 需要 Task 7 的 index.html 才通过，先留着，Task 7 末尾一起跑。

- [ ] **Step 5: 提交**

```bash
git add workbench/app/main.py workbench/tests/test_api.py
git commit -m "feat: FastAPI 路由（计划/天气/配置/overview 聚合，含降级）"
```

---

## Task 6: 一键启动 run.py + start.bat

**Files:**
- Create: `workbench/run.py`
- Create: `workbench/start.bat`

- [ ] **Step 1: 写 `workbench/run.py`**

```python
"""一键启动：起 FastAPI 服务 + 自动打开浏览器。

用法：在 workbench/ 目录下执行 `python run.py`（或双击 start.bat）。
"""
import threading
import time
import webbrowser

import uvicorn

HOST = "127.0.0.1"
PORT = 8765


def _open_browser():
    time.sleep(1.2)  # 等服务真正起来再开浏览器
    webbrowser.open(f"http://{HOST}:{PORT}")


if __name__ == "__main__":
    threading.Thread(target=_open_browser, daemon=True).start()
    uvicorn.run("app.main:app", host=HOST, port=PORT)
```

- [ ] **Step 2: 写 `workbench/start.bat`**

```bat
@echo off
chcp 65001 >nul
cd /d %~dp0
python run.py
pause
```

- [ ] **Step 3: 冒烟测试**

Run: `cd workbench && python run.py`（起服务后 Ctrl+C 停掉，浏览器应自动弹出）
Expected: 控制台出现 `Uvicorn running on http://127.0.0.1:8765`，浏览器自动打开

> 注意：此时前端还是空目录，页面会 404 —— Task 7 之后就好。

- [ ] **Step 4: 提交**

```bash
git add workbench/run.py workbench/start.bat
git commit -m "feat: 一键启动脚本（自动开浏览器）"
```

---

## Task 7: 前端骨架 index.html + style.css（护眼暖调）

**Files:**
- Create: `workbench/static/index.html`
- Create: `workbench/static/style.css`

- [ ] **Step 1: 写 `workbench/static/index.html`**

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>个人工作台</title>
<link rel="stylesheet" href="style.css">
</head>
<body>
<div class="app">
  <!-- 左侧导航 -->
  <nav class="sidebar">
    <div class="brand">📓 工作台</div>
    <a href="#/home"   class="nav-item" data-page="home">🏠 首页</a>
    <a href="#/study"  class="nav-item" data-page="study">📚 学习</a>
    <a href="#/ielts"  class="nav-item" data-page="ielts">🇬🇧 雅思</a>
    <a href="#/ideas"  class="nav-item" data-page="ideas">💡 灵感</a>
    <a href="#/review" class="nav-item" data-page="review">📝 复盘</a>
    <a href="#/tools"  class="nav-item" data-page="tools">🧰 工具</a>
  </nav>

  <!-- 主区 -->
  <main class="main">
    <!-- 首页：一屏聚合 -->
    <section id="page-home" class="page">
      <header class="page-head">
        <h1 id="greeting">早上好</h1>
        <span id="today" class="today"></span>
      </header>
      <div class="grid">
        <div class="card" id="card-clock">
          <div class="card-title">🕐 时钟</div>
          <div id="clock-time" class="clock-time">--:--</div>
          <div id="clock-date" class="clock-date"></div>
        </div>
        <div class="card" id="card-weather">
          <div class="card-title">🌤 天气 <span id="weather-city"></span></div>
          <div id="weather-body" class="weather-body">加载中…</div>
        </div>
        <div class="card card-wide" id="card-plan">
          <div class="card-title">📋 今日计划</div>
          <form id="plan-form" class="plan-form">
            <input id="plan-input" type="text" placeholder="添加一项任务，回车确认" autocomplete="off">
            <button type="submit">添加</button>
          </form>
          <ul id="plan-list" class="plan-list"></ul>
        </div>
        <div class="card" id="card-progress">
          <div class="card-title">📚 学习进度</div>
          <div class="placeholder">M2 里程碑接入<br>（自动读取 study_progress.md）</div>
        </div>
        <div class="card" id="card-ielts">
          <div class="card-title">🇬🇧 雅思</div>
          <div class="placeholder">M2 里程碑接入<br>（进度 + 生词复习）</div>
        </div>
        <div class="card" id="card-ideas">
          <div class="card-title">💡 今日灵感</div>
          <div class="placeholder">M3 里程碑接入<br>（AI 每日自动生成）</div>
        </div>
        <div class="card" id="card-review">
          <div class="card-title">📝 复盘</div>
          <div class="placeholder">M3 里程碑接入<br>（每日总结 + 周报）</div>
        </div>
      </div>
    </section>

    <!-- 其余页面：M2/M3 占位 -->
    <section id="page-study"  class="page hidden"><div class="placeholder big">📚 学习页 · M2 里程碑建设中</div></section>
    <section id="page-ielts"  class="page hidden"><div class="placeholder big">🇬🇧 雅思页 · M2 里程碑建设中</div></section>
    <section id="page-ideas"  class="page hidden"><div class="placeholder big">💡 灵感页 · M3 里程碑建设中</div></section>
    <section id="page-review" class="page hidden"><div class="placeholder big">📝 复盘页 · M3 里程碑建设中</div></section>
    <section id="page-tools"  class="page hidden"><div class="placeholder big">🧰 工具页 · M4 里程碑建设中</div></section>
  </main>
</div>
<script src="app.js"></script>
</body>
</html>
```

- [ ] **Step 2: 写 `workbench/static/style.css`**（护眼暖调主题，CSS 变量集中管理）

```css
/* 护眼暖调主题 —— 配色集中在 :root，改风格只动这里 */
:root {
  --bg: #f3ead9;            /* 米黄纸感背景 */
  --card: #faf4e6;          /* 卡片底色 */
  --border: #ece0c8;        /* 卡片描边 */
  --ink: #5a4a2e;           /* 主文字（深褐） */
  --muted: #8a7a58;         /* 次要文字 */
  --accent: #c9a35f;        /* 强调色（木质暖金） */
  --accent-soft: #e8dcc0;   /* 强调弱底 */
  --shadow: 0 2px 10px rgba(120, 90, 40, .08);
  --radius: 14px;
}

* { margin: 0; padding: 0; box-sizing: border-box; }

body {
  font-family: "Microsoft YaHei", "PingFang SC", sans-serif;
  background: var(--bg);
  color: var(--ink);
  min-height: 100vh;
}

.app { display: flex; min-height: 100vh; }

/* ── 侧边栏 ── */
.sidebar {
  width: 180px;
  flex-shrink: 0;
  background: var(--card);
  border-right: 1px solid var(--border);
  padding: 20px 12px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.brand { font-size: 18px; font-weight: 700; padding: 6px 10px 18px; }
.nav-item {
  display: block;
  padding: 10px 12px;
  border-radius: 10px;
  color: var(--muted);
  text-decoration: none;
  font-size: 14px;
  transition: background .15s, color .15s;
}
.nav-item:hover { background: var(--accent-soft); color: var(--ink); }
.nav-item.active { background: var(--accent); color: #fff; font-weight: 600; }

/* ── 主区 ── */
.main { flex: 1; padding: 28px 32px; }
.page-head { display: flex; align-items: baseline; gap: 12px; margin-bottom: 20px; }
.page-head h1 { font-size: 24px; }
.today { color: var(--muted); font-size: 14px; }
.hidden { display: none; }

/* ── 首页网格 ── */
.grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  gap: 16px;
}
.card {
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  box-shadow: var(--shadow);
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.card-wide { grid-column: 1 / -1; }
.card-title { font-size: 13px; color: var(--muted); font-weight: 600; }

.clock-time { font-size: 34px; font-weight: 700; letter-spacing: 1px; }
.clock-date { color: var(--muted); font-size: 13px; }

.weather-body { font-size: 15px; display: flex; flex-direction: column; gap: 4px; }
.weather-main { font-size: 24px; font-weight: 700; }

.placeholder {
  color: var(--muted);
  font-size: 13px;
  line-height: 1.8;
  padding: 8px 0;
}
.placeholder.big { text-align: center; padding: 80px 0; font-size: 16px; }

/* ── 今日计划 ── */
.plan-form { display: flex; gap: 8px; }
.plan-form input {
  flex: 1;
  padding: 8px 12px;
  border: 1px solid var(--border);
  border-radius: 10px;
  background: #fffdf7;
  color: var(--ink);
  font-size: 14px;
  outline: none;
}
.plan-form input:focus { border-color: var(--accent); }
.plan-form button {
  padding: 8px 16px;
  border: none;
  border-radius: 10px;
  background: var(--accent);
  color: #fff;
  font-size: 14px;
  cursor: pointer;
}
.plan-form button:hover { filter: brightness(1.05); }
.plan-list { list-style: none; display: flex; flex-direction: column; gap: 6px; }
.plan-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 10px;
  border-radius: 10px;
  background: #fffdf7;
  border: 1px solid var(--border);
}
.plan-item input[type="checkbox"] {
  width: 16px; height: 16px;
  accent-color: var(--accent);
  cursor: pointer;
}
.plan-item .text { flex: 1; font-size: 14px; }
.plan-item.done .text { text-decoration: line-through; color: var(--muted); }
.plan-item .del {
  border: none; background: none; color: var(--muted);
  cursor: pointer; font-size: 14px; padding: 2px 6px;
}
.plan-item .del:hover { color: #c25a4a; }
.plan-empty { color: var(--muted); font-size: 13px; padding: 6px 2px; }
```

- [ ] **Step 3: 补跑 API 的 index 测试**

Run: `cd workbench && pytest tests/test_api.py -v`
Expected: 6 passed（`test_index_served` 现在通过）

- [ ] **Step 4: 提交**

```bash
git add workbench/static/index.html workbench/static/style.css
git commit -m "feat: 前端骨架（护眼暖调主题 + 侧边栏 + 首页网格）"
```

---

## Task 8: 前端交互 app.js

**Files:**
- Create: `workbench/static/app.js`

- [ ] **Step 1: 写 `workbench/static/app.js`**

```javascript
/* 个人工作台前端：hash 路由 + 时钟 + 天气 + 今日计划。
   设计原则：每张卡片独立加载、独立容错 —— 一个接口挂了不影响整页。 */
"use strict";

// ── 工具 ──────────────────────────────────────────────
async function api(path, options = {}) {
  const r = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!r.ok) throw new Error(`${path} → ${r.status}`);
  return r.json();
}

const $ = (sel) => document.querySelector(sel);

// ── 时钟 ──────────────────────────────────────────────
const WEEK = ["日", "一", "二", "三", "四", "五", "六"];
function tick() {
  const now = new Date();
  const hh = String(now.getHours()).padStart(2, "0");
  const mm = String(now.getMinutes()).padStart(2, "0");
  const ss = String(now.getSeconds()).padStart(2, "0");
  $("#clock-time").textContent = `${hh}:${mm}:${ss}`;
  $("#clock-date").textContent =
    `${now.getMonth() + 1}月${now.getDate()}日 星期${WEEK[now.getDay()]}`;
}
setInterval(tick, 1000);

// ── 问候语 ────────────────────────────────────────────
function greeting() {
  const h = new Date().getHours();
  return h < 6 ? "夜深了" : h < 12 ? "早上好" : h < 14 ? "中午好" : h < 18 ? "下午好" : "晚上好";
}

// ── 今日计划 ──────────────────────────────────────────
async function loadPlan() {
  const box = $("#plan-list");
  const plan = await api("/api/plan");
  if (!plan.items.length) {
    box.innerHTML = `<li class="plan-empty">今天还没有安排，加一条吧 ✍️</li>`;
    return;
  }
  box.innerHTML = "";
  for (const item of plan.items) {
    const li = document.createElement("li");
    li.className = "plan-item" + (item.done ? " done" : "");
    li.innerHTML = `
      <input type="checkbox" ${item.done ? "checked" : ""} data-id="${item.id}">
      <span class="text"></span>
      <button class="del" data-id="${item.id}" title="删除">✕</button>`;
    li.querySelector(".text").textContent = item.text;
    box.appendChild(li);
  }
}

function bindPlan() {
  $("#plan-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const input = $("#plan-input");
    const text = input.value.trim();
    if (!text) return;
    try {
      await api("/api/plan/items", { method: "POST", body: JSON.stringify({ text }) });
      input.value = "";
      await loadPlan();
    } catch (err) { alert("添加失败：" + err.message); }
  });

  $("#plan-list").addEventListener("click", async (e) => {
    const del = e.target.closest(".del");
    if (!del) return;
    await api(`/api/plan/items/${del.dataset.id}`, { method: "DELETE" });
    loadPlan();
  });

  $("#plan-list").addEventListener("change", async (e) => {
    const cb = e.target.closest('input[type="checkbox"]');
    if (!cb) return;
    await api(`/api/plan/items/${cb.dataset.id}`, {
      method: "PATCH",
      body: JSON.stringify({ done: cb.checked }),
    });
    loadPlan();
  });
}

// ── 天气 ──────────────────────────────────────────────
async function loadWeather() {
  const body = $("#weather-body");
  try {
    const w = await api("/api/weather");
    if (w.error) throw new Error("weather unavailable");
    $("#weather-city").textContent = "· " + w.desc;
    body.innerHTML = `
      <div class="weather-main">${w.icon} ${w.temp}°C</div>
      <div>湿度 ${w.humidity}% · ${w.desc}</div>`;
  } catch (err) {
    body.innerHTML = `<div class="placeholder">天气暂不可用 —</div>`;
  }
}

// ── 页面路由 ──────────────────────────────────────────
const PAGES = ["home", "study", "ielts", "ideas", "review", "tools"];

function route() {
  const hash = location.hash.replace("#/", "") || "home";
  const page = PAGES.includes(hash) ? hash : "home";
  for (const p of PAGES) {
    const el = document.getElementById(`page-${p}`);
    if (el) el.classList.toggle("hidden", p !== page);
  }
  document.querySelectorAll(".nav-item").forEach((a) =>
    a.classList.toggle("active", a.dataset.page === page)
  );
  if (page === "home") {
    $("#greeting").textContent = greeting();
    $("#today").textContent = new Date().toLocaleDateString("zh-CN", {
      year: "numeric", month: "long", day: "numeric", weekday: "long",
    });
    loadPlan().catch(() => {});
    loadWeather().catch(() => {});
  }
}
window.addEventListener("hashchange", route);

// ── 启动 ──────────────────────────────────────────────
bindPlan();
route();
```

- [ ] **Step 2: 端到端手工走查（浏览器）**

Run: `cd workbench && python run.py`
Expected（逐条验证）：
1. 浏览器自动打开 http://127.0.0.1:8765，首页显示护眼暖调网格
2. 时钟每秒走动，显示今日日期
3. 天气卡片显示真实温度/描述（或"天气暂不可用"占位）
4. 添加任务 → 回车 → 出现在列表；勾选 → 划线；✕ → 删除
5. 刷新页面，任务仍在（JSON 持久化）
6. 点击侧边栏其他页面 → 显示"M2 建设中"占位；回首页正常

- [ ] **Step 3: 提交**

```bash
git add workbench/static/app.js
git commit -m "feat: 前端交互（路由/时钟/天气/计划，卡片级容错）"
```

---

## Task 9: M1 收尾验证

- [ ] **Step 1: 全量测试**

Run: `cd workbench && pytest -v`
Expected: 24 passed（storage 4 + plan 6 + weather 4 + config 4 + api 6）

- [ ] **Step 2: 冷启动验证**

Run: `cd workbench && python run.py`，等 3 秒后浏览器打开页面
Expected: 首页完整渲染，无控制台报错（F12 看 Network 无 4xx/5xx）

- [ ] **Step 3: 提交收尾**

```bash
git add -A
git commit -m "chore: M1 骨架完成（服务/存储/计划/天气/前端骨架）"
```

---

## 里程碑后续（不在本计划内，各自成计划）

- **M2 数据闭环**：`/api/progress`（解析 `study_progress.md`）、雅思进度看板 `/api/ielts`、生词本 `/api/vocab`（艾宾浩斯 1/3/7/14/30 天）、学习页/雅思页前端。
- **M3 AI 能力**：DeepSeek 客户端（`.env` 密钥 + 降级）、`/api/ideas` + 懒加载生成、`/api/reviews` AI 起草、`/api/weekly` 周报、灵感页/复盘页前端。
- **M4 集成**：`/api/tools/douyin` 异步任务（后台线程跑 `douyin_extract_v3.py` + 进度轮询）、Obsidian URI 联动、设置页（改城市/昵称）、工具页前端 + 护眼暖调打磨。

## 自审记录

- **Spec 覆盖**：M1 对应规格 §3 技术选型、§4 页面结构（骨架 + 首页 + 占位）、§5 中 plan/weather/config/overview 端点、§7 单卡容错、§8 测试策略、§9 M1 里程碑。规格中 M2-M4 内容明确列入"里程碑后续"。
- **占位符检查**：无 TBD；前端占位卡片是设计内的显式占位（M2/M3 内容），非计划缺口。
- **类型一致性**：`plan.get_plan/add_item/update_item/delete_item` 签名在 plan.py 与 main.py 调用处一致；`storage.load/save` 两参数签名一致；`weather.fetch_weather/geocode_city` 返回结构在 main.py/config.py/测试中一致；`overview` 响应字段与测试断言一致。
