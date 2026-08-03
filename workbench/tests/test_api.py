"""API 层测试：TestClient 模拟 HTTP 请求，验证路由、状态码、降级路径。"""
import datetime as dt

from fastapi.testclient import TestClient

from app import main, storage


def _client() -> TestClient:
    return TestClient(main.app)


def test_get_plan_empty(monkeypatch, tmp_path):
    monkeypatch.setattr(storage, "DATA_DIR", str(tmp_path))
    r = _client().get("/api/plan")
    assert r.status_code == 200
    body = r.json()
    assert body["date"] == dt.date.today().isoformat()
    assert body["items"] == []


def test_plan_full_flow(monkeypatch, tmp_path):
    monkeypatch.setattr(storage, "DATA_DIR", str(tmp_path))
    c = _client()
    r = c.post("/api/plan/items", json={"text": " 背单词 "})
    assert r.status_code == 200
    items = r.json()["items"]
    assert items[0]["text"] == "背单词"  # 服务端去空格
    iid = items[0]["id"]

    r = c.patch(f"/api/plan/items/{iid}", json={"done": True})
    assert r.json()["items"][0]["done"] is True

    r = c.delete(f"/api/plan/items/{iid}")
    assert r.json()["items"] == []


def test_plan_patch_missing_404(monkeypatch, tmp_path):
    monkeypatch.setattr(storage, "DATA_DIR", str(tmp_path))
    r = _client().patch("/api/plan/items/no-such-id", json={"done": True})
    assert r.status_code == 404


def test_weather_ok(monkeypatch, tmp_path):
    monkeypatch.setattr(storage, "DATA_DIR", str(tmp_path))
    monkeypatch.setattr(main.weather_mod, "fetch_weather",
                        lambda lat, lon, timeout=5.0: {"temp": 25, "humidity": 60, "desc": "晴", "icon": "☀️"})
    r = _client().get("/api/weather")
    assert r.status_code == 200
    assert r.json()["desc"] == "晴"


def test_weather_failure_degrades(monkeypatch, tmp_path):
    monkeypatch.setattr(storage, "DATA_DIR", str(tmp_path))

    def boom(lat, lon, timeout=5.0):
        raise RuntimeError("网络挂了")

    monkeypatch.setattr(main.weather_mod, "fetch_weather", boom)
    r = _client().get("/api/weather")
    assert r.status_code == 200          # 不报 500
    assert r.json()["error"] is True
    assert r.json()["desc"] == "—"       # 前端显示占位


def test_config_roundtrip(monkeypatch, tmp_path):
    monkeypatch.setattr(storage, "DATA_DIR", str(tmp_path))
    c = _client()
    r = c.patch("/api/config/nickname", json={"nickname": "小暴龙"})
    assert r.json()["nickname"] == "小暴龙"
    r = c.get("/api/config")
    assert r.json()["nickname"] == "小暴龙"


def test_set_city_bad_400(monkeypatch, tmp_path):
    monkeypatch.setattr(storage, "DATA_DIR", str(tmp_path))
    monkeypatch.setattr(main.weather_mod, "geocode_city", lambda name, timeout=5.0: None)
    r = _client().patch("/api/config/city", json={"city": "火星"})
    assert r.status_code == 400


def test_overview_aggregates(monkeypatch, tmp_path):
    monkeypatch.setattr(storage, "DATA_DIR", str(tmp_path))
    monkeypatch.setattr(main.weather_mod, "fetch_weather",
                        lambda lat, lon, timeout=5.0: {"temp": 25, "humidity": 60, "desc": "晴", "icon": "☀️"})
    c = _client()
    c.post("/api/plan/items", json={"text": "写代码"})
    body = c.get("/api/overview").json()
    assert body["date"] == dt.date.today().isoformat()
    assert body["weather"]["desc"] == "晴"
    assert body["plan"]["items"][0]["text"] == "写代码"
    assert body["nickname"] == "同学"


# ── M2：学习进度 / 雅思 / 生词本 ─────────────────────────────

def test_progress_returns_structure(monkeypatch, tmp_path):
    monkeypatch.setattr(storage, "DATA_DIR", str(tmp_path))
    monkeypatch.setattr(main.progress_mod, "load_progress",
                        lambda: {"subject": "认识大模型", "stages": [], "chapters": [],
                                 "done_count": 0, "total_count": 0, "missing": False})
    r = _client().get("/api/progress")
    assert r.status_code == 200
    assert r.json()["subject"] == "认识大模型"


def test_ielts_get_and_patch(monkeypatch, tmp_path):
    monkeypatch.setattr(storage, "DATA_DIR", str(tmp_path))
    c = _client()
    r = c.get("/api/ielts")
    assert r.json()["target_score"] == 6.5
    r = c.patch("/api/ielts", json={"target_score": 7.0, "skills": {"听力": "6.0"}})
    assert r.json()["target_score"] == 7.0
    assert r.json()["skills"]["听力"] == "6.0"
    assert r.json()["skills"]["阅读"] == ""


def test_vocab_full_flow(monkeypatch, tmp_path):
    monkeypatch.setattr(storage, "DATA_DIR", str(tmp_path))
    c = _client()
    r = c.post("/api/vocab", json={"word": "abandon", "meaning": "v. 放弃"})
    assert r.status_code == 200
    wid = r.json()["id"]
    assert c.get("/api/vocab").json()[0]["word"] == "abandon"

    r = c.post(f"/api/vocab/{wid}/review")
    assert r.json()["stage"] == 1

    r = c.delete(f"/api/vocab/{wid}")
    assert r.status_code == 200
    assert c.get("/api/vocab").json() == []


def test_vocab_due_queue(monkeypatch, tmp_path):
    monkeypatch.setattr(storage, "DATA_DIR", str(tmp_path))
    c = _client()
    c.post("/api/vocab", json={"word": "due", "meaning": "到期"})
    due = c.get("/api/vocab/due").json()
    assert isinstance(due, list)


def test_vocab_missing_404(monkeypatch, tmp_path):
    monkeypatch.setattr(storage, "DATA_DIR", str(tmp_path))
    r = _client().post("/api/vocab/no-such-id/review")
    assert r.status_code == 404


def test_overview_includes_m2(monkeypatch, tmp_path):
    monkeypatch.setattr(storage, "DATA_DIR", str(tmp_path))
    monkeypatch.setattr(main.weather_mod, "fetch_weather",
                        lambda lat, lon, timeout=5.0: {"temp": 25, "humidity": 60, "desc": "晴", "icon": "☀️"})
    monkeypatch.setattr(main.progress_mod, "load_progress",
                        lambda: {"subject": "认识大模型", "stages": [], "chapters": [],
                                 "done_count": 0, "total_count": 0, "missing": False})
    body = _client().get("/api/overview").json()
    assert body["progress"]["subject"] == "认识大模型"
    assert body["ielts"]["target_score"] == 6.5
    assert isinstance(body["review_due"], int)
