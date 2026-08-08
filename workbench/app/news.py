"""新闻简讯：AI 最新 / 国内 / 国外 三板块，多源聚合。

数据源（全部免费公开，已实测）：
- AI 最新：aihot REST API v1（匿名免 Key，中文摘要）
- 国内：IT之家 RSS + B站热门 API
- 国外：Hacker News Algolia API + BBC 中文 RSS + TechCrunch AI RSS

设计要点：
- 统一输出 [{title, source, url, time}]，前端按板块取
- 1 小时内存缓存（各自独立），外部源失败时降级返回 error 标记，不阻塞
- 所有拉取带 UA，超时 10 秒
"""
import datetime as dt
import re
import threading
import time

import requests

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

AIHOT_URL = "https://aihot.virxact.com/api/v1/items?mode=selected&window=24h&limit=20"
IT_HOME_RSS = "https://www.ithome.com/rss/"
BILI_HOT = "https://api.bilibili.com/x/web-interface/ranking/v2?rid=0"
KR36_RSS = "https://36kr.com/feed"
BAIDU_HOT = "https://top.baidu.com/api/board?platform=wise&tab=realtime"
HN_API = "https://hn.algolia.com/api/v1/search?tags=front_page&hitsPerPage=15"
BBC_RSS = "https://feeds.bbci.co.uk/zhongwen/simp/rss.xml"
TECHCRUNCH_RSS = "https://techcrunch.com/category/artificial-intelligence/feed/"

CACHE_TTL = 3600  # 1 小时

_cache: dict[str, dict] = {}
_lock = threading.Lock()


def _get(url: str, timeout: float = 10.0) -> requests.Response:
    return requests.get(url, timeout=timeout, headers=UA)


def _ts_to_str(ts) -> str:
    """时间戳/ISO 字符串 → 'MM-DD HH:MM'。"""
    try:
        if isinstance(ts, (int, float)) and ts > 1e12:
            ts /= 1000
        t = dt.datetime.fromtimestamp(ts)
    except (TypeError, OSError, ValueError):
        return ""
    return t.strftime("%m-%d %H:%M")


def fetch_aihot() -> list:
    data = _get(AIHOT_URL).json()
    items = []
    for it in (data.get("items") or []):
        items.append({
            "title": it.get("title", ""),
            "source": (it.get("source") or {}).get("name", "AI HOT"),
            "url": (it.get("links") or {}).get("original") or (it.get("links") or {}).get("aihot", ""),
            "time": _ts_to_str(it.get("publishedAt")),
        })
    return items


def fetch_rss(url: str, source_name: str) -> list:
    text = _get(url).text
    items = []
    # 简易 RSS 解析：item 块内取 title/link/pubDate/description
    for m in re.finditer(r"<item>(.*?)</item>", text, re.S):
        block = m.group(1)
        title = re.search(r"<title>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</title>", block, re.S)
        link = re.search(r"<link>(.*?)</link>", block, re.S)
        pub = re.search(r"<pubDate>(.*?)</pubDate>", block, re.S)
        if not title:
            continue
        items.append({
            "title": title.group(1).strip(),
            "source": source_name,
            "url": link.group(1).strip() if link else "",
            "time": pub.group(1)[5:16] if pub else "",
        })
    return items[:15]


def fetch_hn() -> list:
    data = _get(HN_API).json()
    items = []
    for hit in (data.get("hits") or []):
        items.append({
            "title": hit.get("title", ""),
            "source": "Hacker News",
            "url": hit.get("url") or f"https://news.ycombinator.com/item?id={hit.get('objectID', '')}",
            "time": _ts_to_str(hit.get("created_at_i")),
        })
    return items


def fetch_bili() -> list:
    data = _get(BILI_HOT).json()
    items = []
    for v in (data.get("data", {}).get("list") or []):
        items.append({
            "title": v.get("title", ""),
            "source": "B站热门",
            "url": v.get("short_link_v2") or v.get("bvid", ""),
            "time": v.get("pubdate") and _ts_to_str(v["pubdate"]) or "",
        })
    return items[:15]


def _sources(tab: str) -> list:
    """每个板块的数据源列表。"""
    if tab == "ai":
        return [("aihot", fetch_aihot)]
    if tab == "domestic":
        return [("百度热搜", fetch_baidu),
                ("IT之家", lambda: fetch_rss(IT_HOME_RSS, "IT之家")),
                ("B站", fetch_bili)]
    return [("BBC中文", lambda: fetch_rss(BBC_RSS, "BBC中文")),
            ("Hacker News", fetch_hn),
            ("TechCrunch", lambda: fetch_rss(TECHCRUNCH_RSS, "TechCrunch"))]


def fetch_baidu() -> list:
    """百度实时热搜（综合：政治/民生/社会/娱乐等）。"""
    data = _get(BAIDU_HOT).json()
    items = []
    seen = set()

    def walk(node):
        if isinstance(node, dict):
            word = node.get("word") or node.get("query")
            if word and word not in seen:
                seen.add(word)
                items.append({"title": word, "source": "百度热搜", "url": node.get("url", ""), "time": ""})
            for v in node.values():
                walk(v)
        elif isinstance(node, list):
            for v in node:
                walk(v)

    walk(data)
    return items[:15]


def get_news(tab: str = "ai", refresh: bool = False) -> dict:
    """拉取板块新闻（带 1 小时缓存，单源失败不影响其他源）。

    refresh=True 时绕过缓存强制重拉（手动刷新用）。
    """
    tab = tab if tab in ("ai", "domestic", "global") else "ai"
    now = time.time()
    if not refresh:
        with _lock:
            cached = _cache.get(tab)
            if cached and now - cached["ts"] < CACHE_TTL:
                return cached["data"]
    items = []
    errors = 0
    sources = _sources(tab)
    for name, fetcher in sources:
        try:
            if len(sources) == 1:
                items.extend(fetcher())          # AI 板块：单源拿满
            else:
                items.extend(fetcher()[:6])      # 多源板块：每源最多 6 条防挤占
        except Exception:
            errors += 1
    data = {
        "tab": tab,
        "items": items[:20],
        "error": errors == len(sources),
        "fetched_at": dt.datetime.now().strftime("%m-%d %H:%M"),
    }
    with _lock:
        _cache[tab] = {"ts": now, "data": data}
    return data
