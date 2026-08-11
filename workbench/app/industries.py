"""行业研究：30 个最有潜力赛道 + 交叉分析（版本化存储）。

数据机制：
- 首次启动：从 app/industry_seed.json（种子，入库）初始化当前版本
- 每次更新（AI 调研后写入）：生成 industry_YYYYMMDD.json 新版本
- 历史回看：保留 7 天内所有版本；超过 7 天自动清理（_prune_old）
- 前端显示更新时间，超 3 天提示"建议更新"
"""
import datetime as dt
import json
import os
import shutil

from . import storage

INDUSTRIES_DIR = "industries"
SEED_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "industry_seed.json")
KEEP_DAYS = 7


def _dir() -> str:
    return os.path.join(storage.DATA_DIR, INDUSTRIES_DIR)


def _version_path(date_str: str) -> str:
    return os.path.join(_dir(), f"industry_{date_str}.json")


def _load(path: str) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _ensure_initialized() -> None:
    """首次使用：把种子数据复制为当前版本。"""
    os.makedirs(_dir(), exist_ok=True)
    if os.listdir(_dir()):
        return
    with open(SEED_PATH, encoding="utf-8") as f:
        seed = json.load(f)
    today = dt.date.today().isoformat()
    seed["updated"] = today
    with open(_version_path(today), "w", encoding="utf-8") as f:
        json.dump(seed, f, ensure_ascii=False, indent=1)


def _prune_old() -> None:
    """删除超过 KEEP_DAYS 天的历史版本。"""
    os.makedirs(_dir(), exist_ok=True)
    cutoff = dt.date.today() - dt.timedelta(days=KEEP_DAYS)
    for name in os.listdir(_dir()):
        if not name.startswith("industry_"):
            continue
        try:
            date = dt.date.fromisoformat(name[len("industry_"):-5])
            if date < cutoff:
                os.remove(os.path.join(_dir(), name))
        except ValueError:
            continue


def current() -> dict:
    """最新版本（全部行业 + 交叉 + 更新时间）。"""
    _ensure_initialized()
    _prune_old()
    files = sorted(f for f in os.listdir(_dir()) if f.startswith("industry_"))
    return _load(os.path.join(_dir(), files[-1]))


def get_industry(industry_id: str) -> dict:
    """单个行业详情。"""
    for ind in current()["industries"]:
        if ind["id"] == industry_id:
            return ind
    raise KeyError(f"行业不存在：{industry_id}")


def history() -> list:
    """历史版本索引（日期倒序）。"""
    _ensure_initialized()
    _prune_old()
    files = sorted((f for f in os.listdir(_dir()) if f.startswith("industry_")), reverse=True)
    out = []
    for name in files:
        try:
            date = name[len("industry_"):-5]
            data = _load(os.path.join(_dir(), name))
            out.append({"date": date, "count": len(data.get("industries", []))})
        except Exception:
            continue
    return out


def get_version(date_str: str) -> dict:
    """回看指定日期的历史版本。"""
    path = _version_path(date_str)
    if not os.path.exists(path):
        raise KeyError(f"没有 {date_str} 的版本")
    return _load(path)
