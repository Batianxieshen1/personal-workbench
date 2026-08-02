"""Open-Meteo 天气客户端：免费、无需 API key，服务端代理解决跨域。

两个接口：
- fetch_weather(lat, lon)：实时天气（温度/湿度/天气码 → 中文描述 + emoji）
- geocode_city(name)：城市名 → 经纬度（Open-Meteo 地理编码）
"""
import requests

WX_URL = "https://api.open-meteo.com/v1/forecast"
GEO_URL = "https://geocoding-api.open-meteo.com/v1/search"

# 天气码映射表（Open-Meteo 官方代码 → (描述, emoji)）
WEATHER_CODES = {
    0: ("晴", "☀️"), 1: ("多云", "🌤️"), 2: ("阴", "☁️"), 3: ("阴", "☁️"),
    45: ("雾", "🌫️"), 48: ("雾凇", "🌫️"),
    51: ("毛毛雨", "🌦️"), 53: ("毛毛雨", "🌦️"), 55: ("毛毛雨", "🌦️"),
    56: ("冻雨", "🌧️"), 57: ("冻雨", "🌧️"),
    61: ("小雨", "🌧️"), 63: ("中雨", "🌧️"), 65: ("大雨", "🌧️"),
    66: ("冻雨", "🌧️"), 67: ("冻雨", "🌧️"),
    71: ("小雪", "🌨️"), 73: ("中雪", "🌨️"), 75: ("大雪", "🌨️"),
    77: ("雪粒", "🌨️"),
    80: ("阵雨", "🌦️"), 81: ("阵雨", "🌦️"), 82: ("强阵雨", "⛈️"),
    85: ("阵雪", "🌨️"), 86: ("强阵雪", "🌨️"),
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
    code = cur["weather_code"]
    desc, icon = WEATHER_CODES.get(code, ("未知", "🌡️"))
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
