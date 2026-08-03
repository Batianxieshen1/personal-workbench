"""快捷工具：抖音视频提取（异步后台任务）。

流程：贴链接/ID → 解析出 video_id → 后台线程跑 douyin_extract_v3.py
→ 前端轮询 job 状态（pending/running/done/error）→ 完成后展示摘要。

设计要点：
- job 存内存 dict：个人工具，重启丢失可接受，不引入数据库
- subprocess 的 cwd 必须是项目根（douyin_extract_v3.py 用相对路径 douyin_output/）
- 超时 600 秒（Whisper 转写很慢），超时标 error
- 脚本成功时 stdout 末尾打印 --- JSON_OUTPUT --- + 摘要 JSON，解析它作为结果
"""
import json
import os
import re
import subprocess
import sys
import threading
import uuid

import requests

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SCRIPT = "douyin_extract_v3.py"
TIMEOUT_SEC = 600

_jobs: dict[str, dict] = {}
_jobs_lock = threading.Lock()


def extract_video_id(text: str) -> str | None:
    """从链接/文本中提取视频 ID。

    规则：
    1. 找 10 位以上连续数字（douyin.com/video/xxx、modal_id=xxx 都是纯数字）
    2. 没有数字且是 http(s) 链接 → 跟随短链重定向（v.douyin.com/xxxx）再找
    """
    m = re.search(r"\d{10,}", text)
    if m:
        return m.group(0)
    if text.strip().startswith(("http://", "https://")):
        try:
            resolved = requests.get(text.strip(), timeout=10, allow_redirects=True).url
            m = re.search(r"\d{10,}", resolved)
            if m:
                return m.group(0)
        except Exception:
            return None
    return None


def _parse_output(stdout: str) -> dict:
    marker = "--- JSON_OUTPUT ---"
    if marker in stdout:
        payload = stdout.split(marker, 1)[1].strip()
        try:
            return json.loads(payload)
        except json.JSONDecodeError:
            return {"raw_tail": stdout[-300:]}
    return {"raw_tail": stdout[-300:]}


def start_job(text: str, ocr: bool = False) -> str:
    """启动提取任务，返回 job_id。"""
    video_id = extract_video_id(text)
    if not video_id:
        raise ValueError("无法从输入中解析出视频 ID")
    job_id = uuid.uuid4().hex[:8]
    with _jobs_lock:
        _jobs[job_id] = {"status": "pending"}
    threading.Thread(target=_run, args=(job_id, video_id, ocr), daemon=True).start()
    return job_id


def _run(job_id: str, video_id: str, ocr: bool) -> None:
    with _jobs_lock:
        _jobs[job_id]["status"] = "running"
    cmd = [sys.executable, SCRIPT, video_id] + (["--ocr"] if ocr else [])
    try:
        r = subprocess.run(
            cmd,
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=TIMEOUT_SEC,
            encoding="utf-8",
        )
        if r.returncode != 0:
            with _jobs_lock:
                _jobs[job_id] = {"status": "error", "error": (r.stderr or r.stdout)[-500:]}
            return
        with _jobs_lock:
            _jobs[job_id] = {"status": "done", "result": _parse_output(r.stdout)}
    except subprocess.TimeoutExpired:
        with _jobs_lock:
            _jobs[job_id] = {"status": "error", "error": f"任务超时（>{TIMEOUT_SEC} 秒）"}
    except Exception as e:
        with _jobs_lock:
            _jobs[job_id] = {"status": "error", "error": str(e)}


def get_job(job_id: str) -> dict | None:
    with _jobs_lock:
        job = _jobs.get(job_id)
        return dict(job) if job else None
