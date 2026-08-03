"""内容复盘测试：灵感状态统计、已采用列表。"""
from app import reviews, storage


def _seed(monkeypatch, tmp_path):
    monkeypatch.setattr(storage, "DATA_DIR", str(tmp_path))
    storage.save("ideas.json", {"ideas": [
        {"id": "a", "text": "已采用的点子", "source": "ai", "date": "2026-08-01",
         "status": "done", "created_at": "2026-08-01T10:00:00"},
        {"id": "b", "text": "收藏的点子", "source": "ai", "date": "2026-08-02",
         "status": "kept", "created_at": "2026-08-02T10:00:00"},
        {"id": "c", "text": "丢弃的点子", "source": "manual", "date": "2026-08-02",
         "status": "discarded", "created_at": "2026-08-02T11:00:00"},
    ]})


def test_content_review_stats(monkeypatch, tmp_path):
    _seed(monkeypatch, tmp_path)
    r = reviews.content_review()
    assert r["stats"]["done"] == 1
    assert r["stats"]["kept"] == 1
    assert r["stats"]["discarded"] == 1


def test_content_review_adopted_list(monkeypatch, tmp_path):
    _seed(monkeypatch, tmp_path)
    r = reviews.content_review()
    assert [i["text"] for i in r["adopted"]] == ["已采用的点子"]


def test_content_review_empty(monkeypatch, tmp_path):
    monkeypatch.setattr(storage, "DATA_DIR", str(tmp_path))
    r = reviews.content_review()
    assert r["stats"] == {"kept": 0, "done": 0, "discarded": 0}
    assert r["adopted"] == []
