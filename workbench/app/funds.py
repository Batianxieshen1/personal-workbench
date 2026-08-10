"""基金涨跌：天天基金公开接口（与支付宝同源数据）。

- pingzhongdata/{code}.js：历史净值 Data_netWorthTrend（每日净值 + 涨跌幅，盘后更新）
- 列表按涨跌幅排序展示（红涨绿跌由前端处理）
- 数据 10 分钟缓存；关注列表存 data/funds.json

默认列表：用户持仓 6 只 + 热门 4 只（沪深300/白酒/医疗/新能源）。
"""
import datetime as dt
import json
import re
import threading
import time

import requests

from . import storage

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
PINGZHONG_URL = "https://fund.eastmoney.com/pingzhongdata/{code}.js"

CACHE_TTL = 600  # 10 分钟
FUNDS_FILE = "funds.json"

# 默认关注列表：用户持仓 + 每类热门
DEFAULT_FUNDS = [
    {"code": "017641"},  # 摩根标普500（美股）
    {"code": "270042"},  # 广发纳指100（美股）
    {"code": "021277"},  # 广发全球精选（全球）
    {"code": "023896"},  # 天弘科创板增强（科技）
    {"code": "110011"},  # 易方达优质精选（混合）
    {"code": "014662"},  # 天弘黄金联接（黄金）
    {"code": "000961"},  # 天弘沪深300（指数）
    {"code": "161725"},  # 招商中证白酒（消费）
    {"code": "003096"},  # 中欧医疗健康（医疗）
    {"code": "001156"},  # 申万菱信新能源汽车（新能源）
]

_cache: dict[str, dict] = {}
_lock = threading.Lock()


def _data() -> dict:
    return storage.load(FUNDS_FILE, {"funds": list(DEFAULT_FUNDS)})


def _save(data: dict) -> None:
    storage.save(FUNDS_FILE, data)


def list_codes() -> list:
    return [f["code"] for f in _data()["funds"]]


def add_fund(code: str) -> dict:
    """添加关注（重复忽略）；返回基金信息。"""
    code = code.strip()
    data = _data()
    if any(f["code"] == code for f in data["funds"]):
        return {"code": code, "duplicate": True}
    info = _fetch_fund(code)
    if not info:
        raise ValueError(f"基金代码不存在或无法获取：{code}")
    data["funds"].append({"code": code})
    _save(data)
    return {"code": code, "name": info["name"]}


def remove_fund(code: str) -> None:
    data = _data()
    data["funds"] = [f for f in data["funds"] if f["code"] != code]
    _save(data)


def parse_pingzhong(text: str) -> dict:
    """解析 pingzhongdata JS：名称 + 历史净值（含每日涨跌幅）。"""
    name_m = re.search(r"var fS_name = \"(.*?)\";", text)
    code_m = re.search(r"var fund_info = \{\"code\": \"(.*?)\"\};", text)
    trend_m = re.search(r"var Data_netWorthTrend = (\[.*?\]);", text, re.S)
    history = []
    if trend_m:
        for pt in json.loads(trend_m.group(1)):
            history.append({
                "date": dt.datetime.fromtimestamp(pt["x"] / 1000).strftime("%m-%d"),
                "value": pt["y"],
                "change": pt.get("equityReturn", 0),
            })
    latest = history[-1] if history else {"value": 0, "change": 0}
    return {
        "name": name_m.group(1) if name_m else code_m.group(1) if code_m else "",
        "code": code_m.group(1) if code_m else "",
        "latest": latest["value"],
        "change_pct": latest.get("change", 0),
        "history": history,
    }


def _fetch_fund(code: str) -> dict | None:
    try:
        r = requests.get(PINGZHONG_URL.format(code=code), timeout=10, headers=UA)
        r.raise_for_status()
        data = parse_pingzhong(r.text)
        if not data["name"]:
            return None
        return data
    except Exception:
        return None


def get_funds() -> dict:
    """全部关注基金的涨跌排行（按涨跌幅排序）。"""
    codes = list_codes()
    now = time.time()
    with _lock:
        cached = _cache.get("list")
        if cached and now - cached["ts"] < CACHE_TTL:
            return cached["data"]
    funds_list = []
    for code in codes:
        info = _fetch_fund(code)
        if info:
            funds_list.append({
                "code": code,
                "name": info["name"],
                "latest": info["latest"],
                "change_pct": info["change_pct"],
            })
    funds_list.sort(key=lambda f: f["change_pct"], reverse=True)  # 涨在前
    data = {"funds": funds_list, "ts": dt.datetime.now().strftime("%m-%d %H:%M")}
    with _lock:
        _cache["list"] = {"ts": now, "data": data}
    return data


def get_history(code: str, days: int = 30) -> dict:
    """单只基金近 N 天净值曲线（5 分钟缓存，反复点击不重复请求）。"""
    now = time.time()
    key = f"hist:{code}"
    with _lock:
        cached = _cache.get(key)
        if cached and now - cached["ts"] < CACHE_TTL:
            return cached["data"]
    info = _fetch_fund(code)
    if not info:
        raise ValueError(f"基金不存在：{code}")
    points = [{"date": p["date"], "value": p["value"]} for p in info["history"][-days:]]
    data = {"code": code, "name": info["name"], "points": points}
    with _lock:
        _cache[key] = {"ts": now, "data": data}
    return data
