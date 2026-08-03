"""资源收藏测试：CRUD、校验、排序。"""
from app import links, storage


def test_add_and_list(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "DATA_DIR", str(tmp_path))
    links.add("OpenAI 文档", "https://platform.openai.com", "常用 API 文档")
    items = links.list_all()
    assert len(items) == 1
    assert items[0]["title"] == "OpenAI 文档"
    assert items[0]["url"].startswith("https://")


def test_add_requires_url(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "DATA_DIR", str(tmp_path))
    try:
        links.add("没有链接", "不是url")
        assert False, "应当抛出 ValueError"
    except ValueError:
        pass


def test_update_and_delete(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "DATA_DIR", str(tmp_path))
    links.add("旧标题", "https://a.com", "")
    lid = links.list_all()[0]["id"]
    links.update(lid, title="新标题")
    assert links.list_all()[0]["title"] == "新标题"
    links.delete(lid)
    assert links.list_all() == []


def test_update_missing_raises(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "DATA_DIR", str(tmp_path))
    try:
        links.update("nope", title="x")
        assert False, "应当抛出 KeyError"
    except KeyError:
        pass
