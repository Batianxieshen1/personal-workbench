"""生词本测试：艾宾浩斯间隔计算、打卡推进、到期队列、毕业。"""
import datetime as dt

from app import storage, vocab

D = dt.date


def test_intervals_sequence():
    """添加后第 1/3/7/14/30 天复习，之后毕业。"""
    base = D(2026, 8, 3)
    assert vocab._next_date(0, base) == "2026-08-04"
    assert vocab._next_date(1, base) == "2026-08-06"
    assert vocab._next_date(2, base) == "2026-08-10"
    assert vocab._next_date(3, base) == "2026-08-17"
    assert vocab._next_date(4, base) == "2026-09-02"
    assert vocab._next_date(5, base) is None  # 5 次复习后毕业


def test_add_word(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "DATA_DIR", str(tmp_path))
    w = vocab.add_word(" abandon ", "v. 放弃")
    assert w["word"] == "abandon"
    assert w["meaning"] == "v. 放弃"
    assert w["stage"] == 0
    assert w["next"] == (dt.date.today() + dt.timedelta(days=1)).isoformat()


def test_review_advances_stage(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "DATA_DIR", str(tmp_path))
    w = vocab.add_word("abandon", "v. 放弃")
    w2 = vocab.review(w["id"])
    assert w2["stage"] == 1
    assert w2["next"] == (dt.date.today() + dt.timedelta(days=3)).isoformat()
    # 连续打卡到毕业
    for _ in range(4):
        w2 = vocab.review(w["id"])
    assert w2["stage"] == 5
    assert w2["next"] is None


def test_due_words_filter(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "DATA_DIR", str(tmp_path))
    # 直接构造数据：两个词 next 不同，一个已到期一个未到期
    storage.save("vocab.json", {"words": [
        {"id": "due1", "word": "到期词", "meaning": "a", "added": "2026-08-01", "stage": 0, "next": "2026-08-02"},
        {"id": "later", "word": "未到期词", "meaning": "b", "added": "2026-08-01", "stage": 0, "next": "2026-08-10"},
    ]})
    due = vocab.due_words("2026-08-05")
    assert [w["id"] for w in due] == ["due1"]


def test_due_words_excludes_graduated(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "DATA_DIR", str(tmp_path))
    w = vocab.add_word("毕业词", "x")
    for _ in range(5):
        vocab.review(w["id"])
    assert vocab.due_words() == []


def test_delete_and_update(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "DATA_DIR", str(tmp_path))
    w = vocab.add_word("temp", "临时")
    vocab.update_meaning(w["id"], "改后释义")
    assert vocab.list_words()[0]["meaning"] == "改后释义"
    vocab.delete_word(w["id"])
    assert vocab.list_words() == []


def test_missing_word_raises(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "DATA_DIR", str(tmp_path))
    try:
        vocab.review("no-such-id")
        assert False, "应当抛出 KeyError"
    except KeyError:
        pass
