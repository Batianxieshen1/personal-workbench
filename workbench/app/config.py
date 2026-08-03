"""用户配置：昵称、城市与坐标。存 data/config.json。

设计要点：
- get_config() 永远返回完整配置（缺字段自动补默认值），前端不用判空
- set_city 走地理编码（城市名 → 经纬度），查不到就抛 ValueError，不写盘
- set_city 先把"改名后的完整配置"算出来再整体 save，保证失败不污染旧配置
"""
from . import storage
from . import weather

DEFAULTS = {
    "nickname": "同学",
    "city": "广州",
    "lat": 23.1291,
    "lon": 113.2644,
}

_CONFIG_FILE = "config.json"


def get_config() -> dict:
    cfg = storage.load(_CONFIG_FILE, None) or {}
    merged = dict(DEFAULTS)
    merged.update({k: v for k, v in cfg.items() if v is not None})
    return merged


def set_nickname(name: str) -> dict:
    cfg = get_config()
    cfg["nickname"] = name.strip()
    storage.save(_CONFIG_FILE, cfg)
    return cfg


def set_city(city: str) -> dict:
    geo = weather.geocode_city(city)
    if not geo:
        raise ValueError(f"找不到城市：{city}")
    cfg = get_config()
    cfg.update(city=geo["city"], lat=geo["lat"], lon=geo["lon"])
    storage.save(_CONFIG_FILE, cfg)
    return cfg


def set_coords(city: str, lat: float, lon: float) -> dict:
    """手动指定坐标兜底：Open-Meteo 地理编码查不到县级小地名时用。"""
    cfg = get_config()
    cfg.update(city=city.strip(), lat=lat, lon=lon)
    storage.save(_CONFIG_FILE, cfg)
    return cfg
