"""统计模块测试：连续天数、完成率、词汇/灵感统计。"""
from app import stats, storage


def _seed_plans(tmp_path, monkeypatch, plans: dict):
    """plans: {date_str: [(text, done)]}"""
    monkeypatch.setattr(storage, "DATA_DIR", str(tmp_path))
    for d, items in plans.items():
        storage.save(f"plans/{d}.json", {"date": d, "items": [
            {"id": f"i{i}", "text": t, "done": done, "done_at": f"{d}T10:00:00", "important": False}
            for i, (t, done) in enumerate(items)
        ]})


def test_streak_days(tmp_path, monkeypatch):
    _seed_plans(tmp_path, monkeypatch, {
        "2026-08-01": [("a", True)],
        "2026-08-02": [("a", True)],
        "2026-08-03": [("a", False)],  # 断档
        "2026-08-04": [("a", True)],
    })
    # 今天=8-04：连续 = 1（8-03 没完成）
    assert stats.streak_days("2026-08-04") == 1
    # 今天=8-02：连续 = 2
    assert stats.streak_days("2026-08-02") == 2


def test_week_completion(tmp_path, monkeypatch):
    _seed_plans(tmp_path, monkeypatch, {
        "2026-08-03": [("a", True), ("b", False)],
        "2026-08-04": [("c", True)],
    })
    r = stats.week_completion("2026-08-03")  # 周一
    assert r["total"] == 3
    assert r["done"] == 2
    assert r["rate"] == round(2 / 3, 2)


def test_vocab_and_idea_stats(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "DATA_DIR", str(tmp_path))
    storage.save("vocab.json", {"words": [
        {"id": "a", "word": "w1", "meaning": "", "added": "2026-08-04", "stage": 0, "next": "2026-08-05"},
        {"id": "b", "word": "w2", "meaning": "", "added": "2026-08-03", "stage": 5, "next": None},
    ]})
    storage.save("ideas.json", {"ideas": [
        {"id": "i1", "text": "x", "source": "ai", "date": "2026-08-03", "status": "done", "note": "", "outcome": "", "created_at": "2026-08-03T00:00:00"},
        {"id": "i2", "text": "y", "source": "ai", "date": "2026-08-03", "status": "discarded", "note": "", "outcome": "", "created_at": "2026-08-03T00:00:01"},
    ]})
    v = stats.vocab_stats("2026-08-04")
    assert v["total"] == 2
    assert v["graduated"] == 1
    assert v["added_today"] == 1
    i = stats.idea_stats()
    assert i["total"] == 2
    assert i["adopt_rate"] == 0.5


def test_daily_completion(tmp_path, monkeypatch):
    _seed_plans(tmp_path, monkeypatch, {
        "2026-08-03": [("a", True), ("b", True)],
        "2026-08-04": [("c", True)],
    })
    daily = stats.daily_completion(today="2026-08-04")
    assert len(daily) == 7  # 近 7 天
    assert daily[-1]["date"] == "08-04"
    assert daily[-1]["done"] == 1
    assert daily[-2]["done"] == 2  # 08-03
    assert daily[0]["done"] == 0   # 更早的日期无记录
