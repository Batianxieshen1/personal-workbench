"""存储层测试：文件读写、缺省值、目录自动创建、Unicode 保真。"""
from app import storage


def test_load_missing_returns_default(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "DATA_DIR", str(tmp_path))
    assert storage.load("plans/2026-08-03.json", {"items": []}) == {"items": []}


def test_save_then_load_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "DATA_DIR", str(tmp_path))
    data = {"date": "2026-08-03", "items": [{"id": "abc123", "text": "学习", "done": False}]}
    storage.save("plans/2026-08-03.json", data)
    assert storage.load("plans/2026-08-03.json", None) == data


def test_save_creates_nested_dirs(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "DATA_DIR", str(tmp_path))
    storage.save("a/b/c.json", {"ok": 1})
    assert (tmp_path / "a" / "b" / "c.json").exists()


def test_save_root_file(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "DATA_DIR", str(tmp_path))
    storage.save("config.json", {"nickname": "x"})
    assert (tmp_path / "config.json").exists()


def test_unicode_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "DATA_DIR", str(tmp_path))
    storage.save("plans/2026-08-03.json", {"items": [{"text": "背雅思单词🧠"}]})
    assert storage.load("plans/2026-08-03.json", None)["items"][0]["text"] == "背雅思单词🧠"
