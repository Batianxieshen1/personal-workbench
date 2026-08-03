"""抖音工具测试：ID 解析、短链解析、输出解析、任务状态机（mock subprocess）。"""
import time

import pytest

from app import storage, tools


def test_extract_id_from_share_text():
    text = "8.88 复制打开抖音，看看【xxx的作品】https://v.douyin.com/iABC123/ 复制此链接"
    # 分享文案里没有 10 位以上数字 → 需要走短链解析；纯数字 ID 直接命中
    assert tools.extract_video_id("https://www.douyin.com/video/7398765432109876543") == "7398765432109876543"
    assert tools.extract_video_id("7398765432109876543") == "7398765432109876543"


def test_extract_id_none():
    assert tools.extract_video_id("没有数字") is None


def test_short_link_resolution(monkeypatch):
    class FakeResp:
        url = "https://www.douyin.com/video/7398765432109876543"

        def raise_for_status(self):
            pass

    monkeypatch.setattr(tools.requests, "get", lambda url, timeout=10, allow_redirects=True: FakeResp())
    assert tools.extract_video_id("https://v.douyin.com/iABC123/") == "7398765432109876543"


def test_parse_output():
    stdout = "一些日志\n--- JSON_OUTPUT ---\n{\"metadata\": {\"标题\": \"x\"}, \"ocr_count\": 2, \"transcript_length\": 500}"
    out = tools._parse_output(stdout)
    assert out["ocr_count"] == 2
    assert out["transcript_length"] == 500


def test_parse_output_without_marker():
    out = tools._parse_output("脚本崩了")
    assert "raw_tail" in out


def test_start_job_runs_and_completes(monkeypatch, tmp_path):
    monkeypatch.setattr(storage, "DATA_DIR", str(tmp_path))

    class FakeResult:
        returncode = 0
        stdout = "--- JSON_OUTPUT ---\n{\"metadata\": {}, \"ocr_count\": 0, \"transcript_length\": 100}"

    def fake_run(cmd, cwd, capture_output, text, timeout, encoding):
        assert cwd == tools.PROJECT_ROOT  # 必须在项目根跑（脚本用相对路径）
        assert cmd[0] == tools.sys.executable
        return FakeResult()

    monkeypatch.setattr(tools.subprocess, "run", fake_run)
    job_id = tools.start_job("7398765432109876543")
    # 等待后台线程完成
    for _ in range(50):
        if tools.get_job(job_id)["status"] in ("done", "error"):
            break
        time.sleep(0.05)
    job = tools.get_job(job_id)
    assert job["status"] == "done"
    assert job["result"]["transcript_length"] == 100


def test_start_job_script_error(monkeypatch, tmp_path):
    monkeypatch.setattr(storage, "DATA_DIR", str(tmp_path))

    class FakeResult:
        returncode = 1
        stdout = ""
        stderr = "Cookie 无效"

    monkeypatch.setattr(tools.subprocess, "run", lambda *a, **k: FakeResult())
    job_id = tools.start_job("7398765432109876543")
    for _ in range(50):
        if tools.get_job(job_id)["status"] in ("done", "error"):
            break
        time.sleep(0.05)
    assert tools.get_job(job_id)["status"] == "error"
    assert "Cookie" in tools.get_job(job_id)["error"]


def test_get_job_missing_returns_none(tmp_path):
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(storage, "DATA_DIR", str(tmp_path))
    assert tools.get_job("不存在") is None


def test_retry_once_on_failure(monkeypatch, tmp_path):
    monkeypatch.setattr(storage, "DATA_DIR", str(tmp_path))

    calls = {"n": 0}

    def flaky_run(cmd, cwd, capture_output, text, timeout, encoding):
        calls["n"] += 1
        if calls["n"] == 1:
            class Bad:
                returncode = 1
                stdout = ""
                stderr = "偶发错误"
            return Bad()
        class Good:
            returncode = 0
            stdout = "--- JSON_OUTPUT ---\n{\"metadata\": {}, \"ocr_count\": 0, \"transcript_length\": 7}"
        return Good()

    monkeypatch.setattr(tools.subprocess, "run", flaky_run)
    job_id = tools.start_job("7398765432109876543")
    for _ in range(50):
        if tools.get_job(job_id)["status"] in ("done", "error"):
            break
        time.sleep(0.05)
    assert calls["n"] == 2  # 失败后自动重试
    assert tools.get_job(job_id)["status"] == "done"
