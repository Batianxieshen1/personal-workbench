"""资源收藏：常用网站/参考资料卡片墙。存 data/links.json。

校验：URL 必须 http(s) 开头（防注入 javascript: 伪协议）。
"""
import datetime as dt
import uuid

from . import storage

LINKS_FILE = "links.json"


def _data() -> dict:
    return storage.load(LINKS_FILE, {"links": []})


def _save(data: dict) -> None:
    storage.save(LINKS_FILE, data)


def list_all() -> list:
    return _data()["links"]


def add(title: str, url: str, note: str = "") -> dict:
    url = url.strip()
    if not url.startswith(("http://", "https://")):
        raise ValueError("链接必须以 http:// 或 https:// 开头")
    link = {
        "id": uuid.uuid4().hex[:8],
        "title": title.strip(),
        "url": url,
        "note": note.strip(),
        "created": dt.date.today().isoformat(),
    }
    data = _data()
    data["links"].append(link)
    _save(data)
    return link


def update(link_id: str, title: str | None = None, url: str | None = None, note: str | None = None) -> dict:
    data = _data()
    for lk in data["links"]:
        if lk["id"] == link_id:
            if title is not None:
                lk["title"] = title.strip()
            if url is not None:
                url = url.strip()
                if not url.startswith(("http://", "https://")):
                    raise ValueError("链接必须以 http:// 或 https:// 开头")
                lk["url"] = url
            if note is not None:
                lk["note"] = note.strip()
            _save(data)
            return lk
    raise KeyError(link_id)


def delete(link_id: str) -> None:
    data = _data()
    before = len(data["links"])
    data["links"] = [l for l in data["links"] if l["id"] != link_id]
    if len(data["links"]) == before:
        raise KeyError(link_id)
    _save(data)
