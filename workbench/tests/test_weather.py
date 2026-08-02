"""天气客户端测试：用伪造的 requests 响应，不真实联网。

原理：monkeypatch 把 weather.requests.get 换成假函数，
返回我们预设的 JSON —— 测试只验证"我们解析得对不对"，不验证"Open-Meteo 活没活着"。
"""
from app import weather


class FakeResp:
    def __init__(self, payload):
        self._payload = payload
        self.calls = []

    def json(self):
        return self._payload

    def raise_for_status(self):
        pass


def _fake_get(fake):
    def handler(url, params=None, timeout=None):
        fake.calls.append({"url": url, "params": params})
        return fake
    return handler


def test_fetch_weather_parses(monkeypatch):
    fake = FakeResp({
        "current": {"temperature_2m": 23.7, "weather_code": 2, "relative_humidity_2m": 66},
    })
    monkeypatch.setattr(weather.requests, "get", _fake_get(fake))
    result = weather.fetch_weather(23.1, 113.3)
    assert result["temp"] == 24          # 四舍五入
    assert result["humidity"] == 66
    assert result["desc"] == "阴"        # 天气码 2 → 阴
    assert result["icon"] == "☁️"


def test_fetch_weather_unknown_code(monkeypatch):
    fake = FakeResp({"current": {"temperature_2m": 10.0, "weather_code": 999, "relative_humidity_2m": 0}})
    monkeypatch.setattr(weather.requests, "get", _fake_get(fake))
    result = weather.fetch_weather(0, 0)
    assert result["desc"] == "未知"


def test_fetch_weather_sends_coords(monkeypatch):
    fake = FakeResp({"current": {"temperature_2m": 1, "weather_code": 0, "relative_humidity_2m": 1}})
    monkeypatch.setattr(weather.requests, "get", _fake_get(fake))
    weather.fetch_weather(23.1291, 113.2644)
    assert fake.calls[0]["params"]["latitude"] == 23.1291
    assert fake.calls[0]["params"]["longitude"] == 113.2644


def test_geocode_city_found(monkeypatch):
    fake = FakeResp({"results": [{"name": "广州", "latitude": 23.1291, "longitude": 113.2644}]})
    monkeypatch.setattr(weather.requests, "get", _fake_get(fake))
    geo = weather.geocode_city("广州")
    assert geo == {"city": "广州", "lat": 23.1291, "lon": 113.2644}


def test_geocode_city_not_found(monkeypatch):
    fake = FakeResp({"results": []})
    monkeypatch.setattr(weather.requests, "get", _fake_get(fake))
    assert weather.geocode_city("不存在的地方") is None
