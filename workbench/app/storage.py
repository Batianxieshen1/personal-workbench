"""JSON 存储层：线程安全读写 workbench/data/ 下的 JSON 文件。

设计要点：
- 加锁：FastAPI 多线程下多个请求同时写文件不会互相踩踏
- 先写 .tmp 再 os.replace：写入中途断电/崩溃不会留下半个文件
- 文件名即路径：如 "plans/2026-08-03.json"，子目录自动创建
"""
import json
import os
import threading

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
_lock = threading.Lock()


def _path(name: str) -> str:
    return os.path.join(DATA_DIR, name)


def load(name: str, default):
    """读取 JSON 文件；不存在时返回 default。"""
    with _lock:
        p = _path(name)
        if not os.path.exists(p):
            return default
        with open(p, "r", encoding="utf-8") as f:
            return json.load(f)


def save(name: str, data) -> None:
    """写入 JSON 文件（原子写：先写临时文件再替换）。"""
    with _lock:
        p = _path(name)
        d = os.path.dirname(p) or DATA_DIR  # 根目录文件 dirname 是空串，兜底
        os.makedirs(d, exist_ok=True)
        tmp = p + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp, p)
