# 个人工作台 M4 集成 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 打通工作台与外部系统：抖音提取脚本异步集成、Obsidian 一键跳转、设置页（昵称/城市/坐标兜底），完成最后一个里程碑。

**Architecture:** 抖音提取走"后台线程 + 任务 ID 轮询"（脚本是几分钟的长任务，不能阻塞 API）；Obsidian 用 obsidian:// URI 调起本地客户端；设置页复用已有 config 接口 + 新增坐标兜底。工具页聚合三块 UI。

**Tech Stack:** Python 3.13 · FastAPI · subprocess（抖音脚本）· obsidian:// URI · 原生前端

**前置条件：** 设计评审已通过（spec 2026-08-03）；M1-M3 已完成，73 测全绿。

---

## 文件结构（M4 创建/修改）

```
workbench/app/
  tools.py          # 新增：抖音提取异步任务（ID 解析 + job 状态机）
  obsidian.py       # 新增：Obsidian URI 构造
  config.py         # 修改：+ set_coords（手动坐标兜底）
  main.py           # 修改：+ tools / obsidian / coords 路由
workbench/tests/
  test_tools.py     # 新增
  test_obsidian.py  # 新增
  test_config.py    # 修改：+ 坐标兜底测试
  test_api.py       # 修改：+ 新路由测试
workbench/static/
  index.html        # 修改：工具页三卡片
  app.js            # 修改：工具页逻辑
  style.css         # 修改：任务进度条等小样式
```

**约定：** 与 M1-M3 一致（`.` 相对导入、原子写、ISO 日期、TDD 红绿灯、每任务 commit）。

---

## Task 0: 抖音任务模块 tools.py（TDD）

**Files:**
- Create: `workbench/app/tools.py`
- Test: `workbench/tests/test_tools.py`

- [ ] **Step 1: 写失败测试**

```python
# workbench/tests/test_tools.py
"""抖音任务模块测试：ID 解析、任务状态机（subprocess 被 mock）。"""
import pytest

from app import storage, tools


def test_extract_video_id_plain():
    assert tools.extract_video_id("7366893723456789012") == "7366893723456789012"


def test_extract_video_id_from_url():
    assert tools.extract_video_id("https://www.douyin.com/video/7366893723456789012") == "7366893723456789012"
    assert tools.extract_video_id("https://v.douyin.com/abc123/?modal_id=7366893723456789012") == "7366893723456789012"


def test_extract_video_id_none():
    assert tools.extract_video_id("https://example.com/not-a-video") is None
    assert tools.extract_video_id("") is None


def test_start_job_runs_subprocess(monkeypatch, tmp_path):
    monkeypatch.setattr(tools.storage, "DATA_DIR", str(tmp_path))
    calls = {}

    def fake_run(cmd, cwd=None, capture_output=True, text=True, timeout=300):
        calls["cmd"] = cmd
        calls["cwd"] = cwd

        class R:
            returncode = 0
            stdout = '报告已保存: douyin_output/x.txt\n--- JSON_OUTPUT ---\n{"metadata": {"标题": "测试"}, "ocr_count": 0, "transcript_length": 100}'
            stderr = ""
        return R()

    monkeypatch.setattr(tools.subprocess, "run", fake_run)
    tools.start_job("7366893723456789012", ocr=False)
    # 任务在后台线程跑，等它完成
    import time
    for _ in range(50):
        if tools.get_job("7366893723456789012")["status"] == "done":
            break
        time.sleep(0.05)
    job = tools.get_job("7366893723456789012")
    assert job["status"] == "done"
    assert "测试" in job["result"]["metadata_text"]
    assert calls["cmd"][-1] == "7366893723456789012"


def test_start_job_failure_records_error(monkeypatch, tmp_path):
    monkeypatch.setattr(tools.storage, "DATA_DIR", str(tmp_path))

    def fake_run(cmd, cwd=None, capture_output=True, text=True, timeout=300):
        class R:
            returncode = 1
            stdout = ""
            stderr = "Cookie 无效"
        return R()

    monkeypatch.setattr(tools.subprocess, "run", fake_run)
    tools.start_job("7366893723456789012", ocr=False)
    import time
    for _ in range(50):
        if tools.get_job("7366893723456789012")["status"] in ("done", "error"):
            break
        time.sleep(0.05)
    job = tools.get_job("7366893723456789012")
    assert job["status"] == "error"
    assert "Cookie" in job["error"]
```

- [ ] **Step 2: 跑测试确认失败**

Run: `python -m pytest workbench\tests\test_tools.py -v`
Expected: `ModuleNotFoundError: No module named 'app.tools'`

- [ ] **Step 3: 写实现**

```python
# workbench/app/tools.py
"""抖音提取异步任务：后台线程跑 douyin_extract_v3.py，任务 ID 轮询查状态。

设计要点：
- 长任务（视频下载+Whisper 转写，几分钟）不能阻塞 API 请求 → 线程 + 内存 job 表
- 脚本在项目根运行（它用相对路径 douyin_output/）
- 脚本 stdout 末尾带 --- JSON_OUTPUT --- 标记 + JSON，解析它提取摘要
- 内存 job 表重启即失，个人工具可接受
"""
import os
import re
import subprocess
import threading
import time

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SCRIPT = "douyin_extract_v3.py"
TIMEOUT = 600  # 10 分钟，转写很慢

_JOBS = {}
_JOBS_LOCK = threading.Lock()


def extract_video_id(text: str) -> str | None:
    """从分享文本/链接里提取抖音视频 ID：优先 /video/{id} 与 modal_id=，
    否则取文本里最长的纯数字串。"""
    m = re.search(r"/video/(\d+)", text)
    if m:
        return m.group(1)
    m = re.search(r"modal_id=(\d+)", text)
    if m:
        return m.group(1)
    digits = re.findall(r"\d+", text)
    if digits:
        return max(digits, key=len)
    return None


def start_job(video_id: str, ocr: bool = False) -> dict:
    with _JOBS_LOCK:
        _JOBS[video_id] = {"id": video_id, "status": "pending", "created_at": time.time(),
                           "result": None, "error": None}
    threading.Thread(target=_run, args=(video_id, ocr), daemon=True).start()
    return _JOBS[video_id]


def _run(video_id: str, ocr: bool) -> None:
    with _JOBS_LOCK:
        _JOBS[video_id]["status"] = "running"
    cmd = ["python", SCRIPT, video_id] + (["--ocr"] if ocr else [])
    try:
        r = subprocess.run(cmd, cwd=PROJECT_ROOT, capture_output=True, text=True, timeout=TIMEOUT)
        if r.returncode != 0:
            raise RuntimeError(r.stderr.strip() or "脚本退出码非 0")
        result = _parse_output(r.stdout)
        with _JOBS_LOCK:
            _JOBS[video_id].update(status="done", result=result)
    except Exception as e:
        with _JOBS_LOCK:
            _JOBS[video_id].update(status="error", error=str(e))


def _parse_output(stdout: str) -> dict:
    """截取 --- JSON_OUTPUT --- 之后的 JSON，并附带报告路径提示。"""
    marker = "--- JSON_OUTPUT ---"
    if marker in stdout:
        payload = stdout.split(marker, 1)[1].strip()
        import json as _json
        try:
            return {"json": _json.loads(payload), "tail": stdout[-600:]}
        except Exception:
            pass
    return {"json": None, "tail": stdout[-600:]}


def get_job(video_id: str) -> dict | None:
    with _JOBS_LOCK:
        job = _JOBS.get(video_id)
        return dict(job) if job else None
```

- [ ] **Step 4: 跑测试确认通过**

Run: `python -m pytest workbench\tests\test_tools.py -v`
Expected: 5 passed

- [ ] **Step 5: Commit**

```bash
git add workbench/app/tools.py workbench/tests/test_tools.py
git commit -m "feat: 抖音提取异步任务 tools.py（ID 解析 + 线程任务 + JSON 摘要）"
```

---

## Task 1: Obsidian URI + 坐标兜底（TDD）

**Files:**
- Create: `workbench/app/obsidian.py`
- Test: `workbench/tests/test_obsidian.py`
- Modify: `workbench/app/config.py`（+set_coords）、`workbench/tests/test_config.py`

- [ ] **Step 1: 写失败测试**

```python
# workbench/tests/test_obsidian.py
"""Obsidian URI 构造测试。"""
from app import obsidian


def test_daily_uri():
    uri = obsidian.daily_uri("2026-08-03")
    assert uri.startswith("obsidian://open?vault=")
    assert "01-日记%2F2026-08-03" in uri or "01-日记/2026-08-03" in uri


def test_vault_uri():
    uri = obsidian.vault_uri()
    assert uri.startswith("obsidian://open?vault=我的知识库")


def test_note_uri():
    uri = obsidian.note_uri("03-AI产品/大模型工程师课程/01-认识大模型")
    assert "03-AI产品" in uri
```

```python
# workbench/tests/test_config.py 追加
def test_set_coords_manual(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "DATA_DIR", str(tmp_path))
    config.set_coords("梅州五华", 23.92961, 115.76499)
    cfg = config.get_config()
    assert cfg["city"] == "梅州五华"
    assert cfg["lat"] == 23.92961
    assert cfg["lon"] == 115.76499
```

- [ ] **Step 2: 跑测试确认失败**

Expected: ImportError app.obsidian / AttributeError set_coords

- [ ] **Step 3: 写实现**

```python
# workbench/app/obsidian.py
"""Obsidian URI 构造：调起本地 Obsidian 客户端打开指定笔记。

URI 格式：obsidian://open?vault=<vault>&file=<path>
中文需 URL 编码（urllib.parse.quote）。
"""
import urllib.parse

VAULT = "我的知识库"


def _uri(file_path: str | None) -> str:
    params = {"vault": VAULT}
    if file_path:
        params["file"] = urllib.parse.quote(file_path)
    return "obsidian://open?" + urllib.parse.urlencode(params)


def vault_uri() -> str:
    return _uri(None)


def daily_uri(date: str) -> str:
    return _uri(f"01-日记/{date}")


def note_uri(path: str) -> str:
    return _uri(path)
```

config.py 追加（`set_city` 之后）：

```python
def set_coords(city: str, lat: float, lon: float) -> dict:
    """手动坐标兜底：中文地名 geocode 不到时用（如五华县）。"""
    cfg = get_config()
    cfg.update(city=city.strip(), lat=float(lat), lon=float(lon))
    storage.save(_CONFIG_FILE, cfg)
    return cfg
```

- [ ] **Step 4: 跑测试确认通过**

Expected: obsidian 3 passed + config 5 passed

- [ ] **Step 5: Commit**

---

## Task 2: 路由层（TDD）

**Files:**
- Modify: `workbench/app/main.py`、`workbench/tests/test_api.py`

- [ ] **Step 1: 追加测试**

```python
# test_api.py 追加
def test_tools_douyin_start_and_poll(monkeypatch, tmp_path):
    monkeypatch.setattr(storage, "DATA_DIR", str(tmp_path))
    monkeypatch.setattr(main.tools_mod.subprocess, "run", lambda *a, **k: type("R", (), {
        "returncode": 0,
        "stdout": '--- JSON_OUTPUT ---\n{"metadata": {"标题": "T"}, "ocr_count": 0, "transcript_length": 5}',
        "stderr": "",
    })())
    c = _client()
    r = c.post("/api/tools/douyin", json={"text": "https://www.douyin.com/video/7366893723456789012"})
    assert r.status_code == 200
    jid = r.json()["id"]
    assert jid == "7366893723456789012"
    import time
    for _ in range(50):
        if c.get(f"/api/tools/douyin/{jid}").json()["status"] == "done":
            break
        time.sleep(0.05)
    job = c.get(f"/api/tools/douyin/{jid}").json()
    assert job["status"] == "done"
    assert job["result"]["json"]["metadata"]["标题"] == "T"


def test_tools_douyin_bad_input_400(monkeypatch, tmp_path):
    monkeypatch.setattr(storage, "DATA_DIR", str(tmp_path))
    r = _client().post("/api/tools/douyin", json={"text": "https://example.com/nope"})
    assert r.status_code == 400


def test_obsidian_uris(monkeypatch, tmp_path):
    monkeypatch.setattr(storage, "DATA_DIR", str(tmp_path))
    body = _client().get("/api/obsidian/daily", params={"date": "2026-08-03"}).json()
    assert body["uri"].startswith("obsidian://open")
    body = _client().get("/api/obsidian/vault").json()
    assert "我的知识库" in body["uri"]


def test_config_coords(monkeypatch, tmp_path):
    monkeypatch.setattr(storage, "DATA_DIR", str(tmp_path))
    r = _client().patch("/api/config/coords", json={"city": "梅州五华", "lat": 23.92961, "lon": 115.76499})
    assert r.status_code == 200
    assert r.json()["lat"] == 23.92961
```

- [ ] **Step 2: 跑测试确认失败**

- [ ] **Step 3: main.py 加路由**

```python
# 路由区追加（模型类追加 ToolsIn / CoordsIn）
class ToolsIn(BaseModel):
    text: str
    ocr: bool = False


class CoordsIn(BaseModel):
    city: str
    lat: float
    lon: float


# 路由
@app.post("/api/tools/douyin")
def api_tools_douyin(body: ToolsIn):
    vid = tools_mod.extract_video_id(body.text)
    if not vid:
        raise HTTPException(400, "无法从输入中识别抖音视频 ID")
    return tools_mod.start_job(vid, ocr=body.ocr)


@app.get("/api/tools/douyin/{job_id}")
def api_tools_douyin_status(job_id: str):
    job = tools_mod.get_job(job_id)
    if not job:
        raise HTTPException(404, f"任务不存在：{job_id}")
    return job


@app.get("/api/obsidian/daily")
def api_obsidian_daily(date: str | None = None):
    d = date or dt.date.today().isoformat()
    return {"uri": obsidian_mod.daily_uri(d)}


@app.get("/api/obsidian/vault")
def api_obsidian_vault():
    return {"uri": obsidian_mod.vault_uri()}


@app.patch("/api/config/coords")
def api_set_coords(body: CoordsIn):
    return config_mod.set_coords(body.city, body.lat, body.lon)
```

imports 追加：`from . import obsidian as obsidian_mod`、`from . import tools as tools_mod`

- [ ] **Step 4: 跑测试确认通过**（全量）

- [ ] **Step 5: Commit**

---

## Task 3: 工具页前端

**Files:**
- Modify: `workbench/static/index.html`、`app.js`、`style.css`

- [ ] **Step 1: index.html 工具页替换占位为三卡片**

```html
<section class="page" id="page-tools">
  <div class="page-head"><h1>🛠 工具</h1></div>
  <div class="grid">
    <!-- 抖音提取 -->
    <div class="card card-wide">
      <div class="card-title">🎬 抖音视频深度解析</div>
      <div class="sub-hint">粘贴分享链接或视频 ID，后台解析出元数据 + 字幕（长任务，可关页面等通知）</div>
      <form class="plan-form" id="douyin-form">
        <input class="plan-input" id="douyin-input" type="text" placeholder="https://v.douyin.com/xxxx 或视频 ID" autocomplete="off">
        <button class="btn-small" type="submit">开始解析</button>
      </form>
      <div class="muted-line" id="douyin-status" style="margin-bottom:8px"></div>
      <pre class="tool-output" id="douyin-output" style="display:none"></pre>
    </div>
    <!-- Obsidian -->
    <div class="card">
      <div class="card-title">📓 Obsidian 联动</div>
      <div style="display:flex;flex-direction:column;gap:8px">
        <a class="btn-small" href="#" id="obsidian-daily" target="_blank">📔 打开今日日记</a>
        <a class="btn-small ghost" href="#" id="obsidian-vault" target="_blank">🗂 打开知识库</a>
      </div>
    </div>
    <!-- 设置 -->
    <div class="card">
      <div class="card-title">⚙️ 设置</div>
      <div class="muted-line" style="margin-bottom:8px">昵称</div>
      <form class="plan-form" id="nickname-form">
        <input class="plan-input" id="nickname-input" type="text" placeholder="你的昵称" autocomplete="off">
        <button class="btn-small" type="submit">保存</button>
      </form>
      <div class="muted-line" style="margin:10px 0 8px">城市天气（改城市自动查坐标）</div>
      <form class="plan-form" id="city-form">
        <input class="plan-input" id="city-input" type="text" placeholder="城市名" autocomplete="off">
        <button class="btn-small" type="submit">保存</button>
      </form>
      <div class="muted-line" style="margin:10px 0 8px">或手动坐标（小地名 geocode 不到时用）</div>
      <form class="plan-form" id="coords-form">
        <input class="plan-input" id="coords-city" type="text" placeholder="地名" style="max-width:100px" autocomplete="off">
        <input class="plan-input" id="coords-lat" type="text" placeholder="纬度" style="max-width:80px" autocomplete="off">
        <input class="plan-input" id="coords-lon" type="text" placeholder="经度" style="max-width:80px" autocomplete="off">
        <button class="btn-small" type="submit">保存</button>
      </form>
      <div class="muted-line" id="settings-status" style="margin-top:8px"></div>
    </div>
  </div>
</section>
```

- [ ] **Step 2: app.js 逻辑**

```js
// ── 工具页 ──
async function loadToolsPage() {
  // Obsidian 链接
  try {
    const d = await api(`/api/obsidian/daily`);
    document.getElementById("obsidian-daily").href = d.uri;
    const v = await api("/api/obsidian/vault");
    document.getElementById("obsidian-vault").href = v.uri;
  } catch { /* 忽略 */ }
  // 设置表单预填
  try {
    const cfg = await api("/api/config");
    document.getElementById("nickname-input").value = cfg.nickname;
    document.getElementById("city-input").value = cfg.city;
  } catch { /* 忽略 */ }
}

document.getElementById("douyin-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const input = document.getElementById("douyin-input");
  const text = input.value.trim();
  if (!text) return;
  const status = document.getElementById("douyin-status");
  const output = document.getElementById("douyin-output");
  status.textContent = "已提交，解析任务 ID 中…";
  output.style.display = "none";
  try {
    const job = await api("/api/tools/douyin", { method: "POST", body: JSON.stringify({ text }) });
    status.textContent = `任务 ${job.id} 运行中…（长任务约 1-5 分钟，可刷新页面）`;
    pollDouyin(job.id, 0);
  } catch (err) {
    status.textContent = "提交失败：" + err.message;
  }
});

async function pollDouyin(jobId, attempt) {
  const status = document.getElementById("douyin-status");
  const output = document.getElementById("douyin-output");
  try {
    const job = await api(`/api/tools/douyin/${jobId}`);
    if (job.status === "done") {
      status.textContent = "✅ 解析完成（报告已存入 douyin_output/）";
      const j = job.result?.json;
      if (j) {
        const md = j.metadata || {};
        output.style.display = "block";
        output.textContent = `标题：${md["标题"] || "—"}\nOCR 片段：${j.ocr_count || 0} 段\n字幕长度：${j.transcript_length || 0} 字`;
      } else {
        output.style.display = "block";
        output.textContent = job.result?.tail || "";
      }
      return;
    }
    if (job.status === "error") {
      status.textContent = "❌ 解析失败：" + (job.error || "未知错误");
      return;
    }
    if (attempt > 120) {  // 120 × 3s = 6 分钟上限
      status.textContent = "⏳ 任务仍在后台运行，可稍后刷新页面查看（任务表在内存中，服务重启会丢失）";
      return;
    }
    setTimeout(() => pollDouyin(jobId, attempt + 1), 3000);
  } catch {
    status.textContent = "查询任务状态失败，请刷新页面";
  }
}

document.getElementById("nickname-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const input = document.getElementById("nickname-input");
  try {
    await api("/api/config/nickname", { method: "PATCH", body: JSON.stringify({ nickname: input.value }) });
    setSettingsStatus("昵称已保存 ✅");
    loadHomeCards();
  } catch { setSettingsStatus("保存失败"); }
});

document.getElementById("city-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const input = document.getElementById("city-input");
  try {
    await api("/api/config/city", { method: "PATCH", body: JSON.stringify({ city: input.value }) });
    setSettingsStatus("城市已更新 ✅");
    loadHomeCards();
  } catch { setSettingsStatus("找不到这个城市，试试手动坐标"); }
});

document.getElementById("coords-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const city = document.getElementById("coords-city").value.trim();
  const lat = parseFloat(document.getElementById("coords-lat").value);
  const lon = parseFloat(document.getElementById("coords-lon").value);
  if (!city || Number.isNaN(lat) || Number.isNaN(lon)) { setSettingsStatus("请填写完整的地名/纬度/经度"); return; }
  try {
    await api("/api/config/coords", { method: "PATCH", body: JSON.stringify({ city, lat, lon }) });
    setSettingsStatus("坐标已保存 ✅");
    loadHomeCards();
  } catch { setSettingsStatus("保存失败"); }
});

function setSettingsStatus(text) {
  const el = document.getElementById("settings-status");
  el.textContent = text;
  setTimeout(() => { el.textContent = ""; }, 3000);
}
```

navigate() 追加 `if (page === "tools") loadToolsPage();`

- [ ] **Step 3: style.css 追加**

```css
/* 工具页 */
.tool-output {
  background: var(--bg); border: 1px solid var(--card-border); border-radius: 9px;
  padding: 10px 12px; font-size: 13px; line-height: 1.6;
  white-space: pre-wrap; word-break: break-all; max-height: 260px; overflow: auto;
  font-family: Consolas, "Microsoft YaHei", monospace;
}
```

- [ ] **Step 4: 手工走查**（启动服务，工具页三卡片渲染、Obsidian 链接生成、昵称/城市/坐标保存、抖音表单错误提示）

- [ ] **Step 5: Commit**

---

## Task 4: 端到端走查 + 收尾

- [ ] **Step 1: 全量测试**

Run: `python -m pytest workbench\tests`  → 全绿

- [ ] **Step 2: 浏览器走查**
- 工具页三卡片渲染正常
- 抖音：先测"无效链接"（400 提示），再测真实 ID（如果网络允许，真实跑一次 douyin 脚本；脚本需要 Cookie，可能失败——失败也要验证错误展示）
- Obsidian：点击"打开今日日记"→ 浏览器调起 Obsidian（或提示协议未关联）
- 设置：改昵称 → 首页问候语联动；改城市"北京" → 天气变北京；手动坐标 → 梅州五华
- 全页面回归：首页/学习/雅思/灵感/复盘

- [ ] **Step 3: README 里程碑更新 + commit**

- [ ] **Step 4: 更新项目记忆（workbench-status）**

---

## 风险与说明

- 抖音脚本需要 `.douyin_cookie` 有效 Cookie，可能失败——失败路径也要验证
- 真实跑脚本耗时长（Whisper），走查时优先验证任务状态机（提交→轮询→done/error），不强制跑完
- obsidian:// 需要本机装了 Obsidian 且关联协议；点击后浏览器可能弹"打开 Obsidian？"
- 任务表在内存，服务重启即失——README 注明
