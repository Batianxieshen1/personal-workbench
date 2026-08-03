# 个人工作台 M2 数据闭环 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把首页占位卡换成真数据——实时解析 `study_progress.md` 展示学习进度；实现雅思三件套（进度看板 / 生词本艾宾浩斯 1/3/7/14/30 天复习 / 复习队列），并接入 overview 聚合。

**Architecture:** 三个新后端模块（`progress.py` 纯函数解析器、`ielts.py` 配置式进度、`vocab.py` 生词本+间隔复习算法），各自独立可测；`main.py` 挂新路由并把 progress/ielts/review_due 填入 `/api/overview`；前端学习页/雅思页从占位变成真渲染，首页两张卡接真数据。

**Tech Stack:** Python 3.13 · FastAPI · 原生 JS · pytest。存储沿用 JSON 原子写。

**前置条件：** M1 已验收（29 测试全绿）；设计文档 `docs/superpowers/specs/2026-08-03-personal-workbench-design.md` §4/§5。

---

## 文件结构（M2）

```
workbench/app/
  progress.py          # 新增：study_progress.md 解析器
  ielts.py             # 新增：雅思进度 CRUD
  vocab.py             # 新增：生词本 + 艾宾浩斯间隔算法
  main.py              # 修改：新路由 + overview 填充
workbench/tests/
  test_progress.py     # 新增
  test_ielts.py        # 新增
  test_vocab.py        # 新增
  test_api.py          # 修改：新增路由测试
workbench/static/
  index.html           # 修改：学习页/雅思页真结构
  style.css            # 修改：看板/生词样式
  app.js               # 修改：页面渲染 + 生词交互
```

**数据文件（运行期自动生成，git 忽略）：**
- `workbench/data/ielts.json` — 雅思进度
- `workbench/data/vocab.json` — 生词本 `{"words": [...]}`

**词条结构（艾宾浩斯）：**
```json
{"id": "a1b2c3d4", "word": "abandon", "meaning": "v. 放弃",
 "added": "2026-08-03", "stage": 0, "next": "2026-08-04"}
```
- `stage` = 已完成复习次数；`next` = 下次复习日期（`added` 起 1/3/7/14/30 天推进）；毕业（stage≥5）时 `next=null`。

---

## Task 1: 学习进度解析器 progress.py

**Files:**
- Create: `workbench/app/progress.py`
- Test: `workbench/tests/test_progress.py`

- [ ] **Step 1: 写失败测试**

```python
# workbench/tests/test_progress.py
"""进度解析器测试：科目/更新日期/阶段清单/测验表格/缺文件降级。"""
from app import progress

SAMPLE = """# 复习进度（断点锁定）

- 科目：认识大模型（大模型工程师课程·第1章）
- 最后更新：2026-08-02（导入日）

## 当前阶段
- [x] ch1 授课 + 测验（3/3 通过）
- [ ] ch2 授课 + 测验（4/4 通过）
- [x] 错题扫雷（错题本为空，跳过）

## 已完成
- 2026-08-02：ch1 授课完成

## 测验记录
| 章节 | 状态 | 结果 |
| --- | --- | --- |
| ch1 | 已通过 | 3/3 全对 |
| ch2 | 未开始 | — |

## 错题本
（暂无）
"""


def test_parse_extracts_all_fields():
    p = progress.parse_markdown(SAMPLE)
    assert p["subject"] == "认识大模型（大模型工程师课程·第1章）"
    assert p["updated"] == "2026-08-02（导入日）"
    assert len(p["stages"]) == 3
    assert p["stages"][0] == {"done": True, "text": "ch1 授课 + 测验（3/3 通过）"}
    assert p["stages"][1]["done"] is False
    assert p["done_count"] == 2
    assert p["total_count"] == 3


def test_parse_table():
    p = progress.parse_markdown(SAMPLE)
    assert p["chapters"] == [
        {"chapter": "ch1", "status": "已通过", "result": "3/3 全对"},
        {"chapter": "ch2", "status": "未开始", "result": "—"},
    ]


def test_parse_empty_text():
    p = progress.parse_markdown("")
    assert p["subject"] == ""
    assert p["stages"] == []
    assert p["chapters"] == []


def test_load_missing_file_degrades(tmp_path):
    p = progress.load_progress(str(tmp_path / "nope.md"))
    assert p["missing"] is True
    assert p["done_count"] == 0


def test_load_real_file(tmp_path):
    f = tmp_path / "study_progress.md"
    f.write_text(SAMPLE, encoding="utf-8")
    p = progress.load_progress(str(f))
    assert p["missing"] is not True
    assert p["subject"].startswith("认识大模型")
```

- [ ] **Step 2: 跑测试确认失败**

Run: `python -m pytest workbench\tests\test_progress.py -v`
Expected: `ImportError: cannot import name 'progress' from 'app'`

- [ ] **Step 3: 实现**

```python
# workbench/app/progress.py
"""学习进度解析器：读取项目根 study_progress.md，提取结构化进度。

设计要点：
- parse_markdown 是纯函数（输入字符串→输出字典），不碰文件系统，好测
- 文件缺失/解析失败一律降级返回空结构，绝不抛错（前端显示占位）
"""
import os
import re

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PROGRESS_FILE = os.path.join(PROJECT_ROOT, "study_progress.md")


def parse_markdown(text: str) -> dict:
    subject, updated = "", ""
    stages, chapters = [], []
    in_stages = in_table = False
    for raw in text.splitlines():
        line = raw.strip()
        if line.startswith("- 科目："):
            subject = line.split("：", 1)[1].strip()
        elif line.startswith("- 最后更新："):
            updated = line.split("：", 1)[1].strip()
        elif line.startswith("## "):
            in_stages = line == "## 当前阶段"
            in_table = line == "## 测验记录"
            continue
        if in_stages and line.startswith("- ["):
            m = re.match(r"- \[([ x])\] (.+)", line)
            if m:
                stages.append({"done": m.group(1) == "x", "text": m.group(2)})
        elif in_table and line.startswith("|"):
            cells = [c.strip() for c in line.strip("|").split("|")]
            if cells and cells[0].startswith("ch"):
                chapters.append({"chapter": cells[0], "status": cells[1], "result": cells[2]})
    return {
        "subject": subject,
        "updated": updated,
        "stages": stages,
        "chapters": chapters,
        "done_count": sum(1 for s in stages if s["done"]),
        "total_count": len(stages),
    }


def load_progress(path: str | None = None) -> dict:
    p = path or PROGRESS_FILE
    try:
        with open(p, "r", encoding="utf-8") as f:
            result = parse_markdown(f.read())
        result["missing"] = False
        return result
    except FileNotFoundError:
        return {"subject": "", "updated": "", "stages": [], "chapters": [],
                "done_count": 0, "total_count": 0, "missing": True}
```

- [ ] **Step 4: 跑测试确认通过**

Run: `python -m pytest workbench\tests\test_progress.py -v`
Expected: `5 passed`

- [ ] **Step 5: Commit**

```bash
git add workbench && git commit -m "feat: 学习进度解析器 progress.py（md → 结构化数据）"
```

---

## Task 2: 雅思进度 ielts.py

**Files:**
- Create: `workbench/app/ielts.py`
- Test: `workbench/tests/test_ielts.py`

- [ ] **Step 1: 写失败测试**

```python
# workbench/tests/test_ielts.py
"""雅思进度测试：默认值补齐、字段更新、skills 合并。"""
from app import ielts, storage


def test_defaults(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "DATA_DIR", str(tmp_path))
    d = ielts.get_ielts()
    assert d["target_score"] == 6.5
    assert set(d["skills"]) == {"听力", "阅读", "写作", "口语"}


def test_patch_fields(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "DATA_DIR", str(tmp_path))
    d = ielts.update_ielts({"target_score": 7.0, "current_band": "6.0"})
    assert d["target_score"] == 7.0
    assert d["current_band"] == "6.0"


def test_patch_skills_merges(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "DATA_DIR", str(tmp_path))
    d = ielts.update_ielts({"skills": {"听力": "6.5", "阅读": "7.0"}})
    assert d["skills"]["听力"] == "6.5"
    assert d["skills"]["阅读"] == "7.0"
    assert d["skills"]["写作"] == ""  # 未动的键保留默认
```

- [ ] **Step 2: 跑测试确认失败** → `ImportError: cannot import name 'ielts'`

- [ ] **Step 3: 实现**

```python
# workbench/app/ielts.py
"""雅思进度：目标分、当前水平、备考阶段、考试日期、四科水平。存 data/ielts.json。"""
from . import storage

IELTS_FILE = "ielts.json"

DEFAULTS = {
    "target_score": 6.5,
    "current_band": "5.5",
    "stage": "基础强化",
    "exam_date": "",
    "skills": {"听力": "", "阅读": "", "写作": "", "口语": ""},
}


def get_ielts() -> dict:
    data = storage.load(IELTS_FILE, None) or {}
    merged = dict(DEFAULTS)
    merged.update({k: v for k, v in data.items() if v is not None})
    merged["skills"] = {**DEFAULTS["skills"], **(data.get("skills") or {})}
    return merged


def update_ielts(patch: dict) -> dict:
    current = get_ielts()
    for k, v in patch.items():
        if k == "skills":
            current["skills"].update(v or {})
        elif k in current and v is not None:
            current[k] = v
    storage.save(IELTS_FILE, current)
    return current
```

- [ ] **Step 4: 跑测试确认通过** → `3 passed`

- [ ] **Step 5: Commit** → `feat: 雅思进度模块 ielts.py`

---

## Task 3: 生词本 vocab.py（艾宾浩斯核心算法）

**Files:**
- Create: `workbench/app/vocab.py`
- Test: `workbench/tests/test_vocab.py`

- [ ] **Step 1: 写失败测试**

```python
# workbench/tests/test_vocab.py
"""生词本测试：间隔计算、增删、复习推进、到期队列、毕业。"""
import datetime as dt

from app import storage, vocab

TODAY = dt.date(2026, 8, 3)


def test_interval_calculation():
    # 阶段 0（刚添加）→ 1 天后；阶段 1 → 3 天后；毕业（≥5）→ None
    assert vocab._next_date(0, TODAY) == "2026-08-04"
    assert vocab._next_date(1, TODAY) == "2026-08-06"
    assert vocab._next_date(2, TODAY) == "2026-08-10"
    assert vocab._next_date(5, TODAY) is None


def test_add_word(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "DATA_DIR", str(tmp_path))
    w = vocab.add_word("abandon", "v. 放弃")
    assert w["word"] == "abandon"
    assert w["stage"] == 0
    assert w["next"] == (dt.date.today() + dt.timedelta(days=1)).isoformat()


def test_review_progresses(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "DATA_DIR", str(tmp_path))
    w = vocab.add_word("abandon", "v. 放弃")
    w2 = vocab.review(w["id"])
    assert w2["stage"] == 1
    assert w2["next"] == (dt.date.today() + dt.timedelta(days=3)).isoformat()
    w3 = vocab.review(w["id"])
    assert w3["stage"] == 2
    assert w3["next"] == (dt.date.today() + dt.timedelta(days=7)).isoformat()


def test_review_graduate(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "DATA_DIR", str(tmp_path))
    w = vocab.add_word("abandon", "v. 放弃")
    for _ in range(5):
        w = vocab.review(w["id"])
    assert w["stage"] == 5
    assert w["next"] is None


def test_due_words_filter(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "DATA_DIR", str(tmp_path))
    a = vocab.add_word("alpha", "a")
    b = vocab.add_word("beta", "b")
    vocab.review(a["id"])  # a: next = today+3，未到期
    due = vocab.due_words("2026-08-03")  # b: next = today+1 → 到期
    assert [w["word"] for w in due] == ["beta"]


def test_delete_word(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "DATA_DIR", str(tmp_path))
    w = vocab.add_word("alpha", "a")
    vocab.delete_word(w["id"])
    assert vocab.list_words() == []
    try:
        vocab.delete_word("nope")
        assert False, "应当抛 KeyError"
    except KeyError:
        pass
```

- [ ] **Step 2: 跑测试确认失败** → `ImportError: cannot import name 'vocab'`

- [ ] **Step 3: 实现**

```python
# workbench/app/vocab.py
"""雅思生词本：艾宾浩斯间隔复习（1/3/7/14/30 天）。

词条：{"id", "word", "meaning", "added", "stage", "next"}
- stage：已完成复习次数（0 = 刚添加）
- next：下次复习日期；stage ≥ 5 毕业，next = None
"""
import datetime as dt
import uuid

from . import storage

REVIEW_INTERVALS = [1, 3, 7, 14, 30]
VOCAB_FILE = "vocab.json"


def _next_date(stage: int, base: dt.date) -> str | None:
    """阶段 stage 完成后，距 base 再过 REVIEW_INTERVALS[stage] 天复习。"""
    if stage >= len(REVIEW_INTERVALS):
        return None
    return (base + dt.timedelta(days=REVIEW_INTERVALS[stage])).isoformat()


def _data() -> dict:
    return storage.load(VOCAB_FILE, {"words": []})


def _save(data: dict) -> None:
    storage.save(VOCAB_FILE, data)


def list_words() -> list:
    return _data()["words"]


def add_word(word: str, meaning: str) -> dict:
    w = {
        "id": uuid.uuid4().hex[:8],
        "word": word.strip(),
        "meaning": meaning.strip(),
        "added": dt.date.today().isoformat(),
        "stage": 0,
        "next": _next_date(0, dt.date.today()),
    }
    data = _data()
    data["words"].append(w)
    _save(data)
    return w


def update_meaning(word_id: str, meaning: str) -> dict:
    data = _data()
    for w in data["words"]:
        if w["id"] == word_id:
            w["meaning"] = meaning.strip()
            _save(data)
            return w
    raise KeyError(word_id)


def review(word_id: str) -> dict:
    """复习打卡：stage +1，按新阶段重算 next（基准 = 今天）。"""
    data = _data()
    for w in data["words"]:
        if w["id"] == word_id:
            w["stage"] += 1
            w["next"] = _next_date(w["stage"], dt.date.today())
            _save(data)
            return w
    raise KeyError(word_id)


def delete_word(word_id: str) -> None:
    data = _data()
    before = len(data["words"])
    data["words"] = [w for w in data["words"] if w["id"] != word_id]
    if len(data["words"]) == before:
        raise KeyError(word_id)
    _save(data)


def due_words(today: str | None = None) -> list:
    """到期复习队列：next ≤ today 且未毕业（next 非空）。"""
    t = today or dt.date.today().isoformat()
    return [w for w in list_words() if w["next"] is not None and w["next"] <= t]
```

- [ ] **Step 4: 跑测试确认通过** → `6 passed`

- [ ] **Step 5: Commit** → `feat: 生词本 vocab.py（艾宾浩斯 1/3/7/14/30 复习）`

---

## Task 4: 后端路由 + overview 填充

**Files:**
- Modify: `workbench/app/main.py`
- Modify: `workbench/tests/test_api.py`

- [ ] **Step 1: 追加失败测试（test_api.py 末尾）**

```python
# ── M2：进度 / 雅思 / 生词 ──

def test_progress_route(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "DATA_DIR", str(tmp_path))
    monkeypatch.setattr(main.progress_mod, "load_progress",
                        lambda path=None: {"subject": "认识大模型", "chapters": [],
                                           "done_count": 2, "total_count": 3, "missing": False})
    r = _client().get("/api/progress")
    assert r.status_code == 200
    assert r.json()["subject"] == "认识大模型"


def test_ielts_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "DATA_DIR", str(tmp_path))
    c = _client()
    r = c.patch("/api/ielts", json={"target_score": 7.0, "skills": {"听力": "6.5"}})
    assert r.json()["target_score"] == 7.0
    assert c.get("/api/ielts").json()["skills"]["听力"] == "6.5"


def test_vocab_flow(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "DATA_DIR", str(tmp_path))
    c = _client()
    r = c.post("/api/vocab", json={"word": "abandon", "meaning": "v. 放弃"})
    assert r.status_code == 200
    wid = r.json()["id"]
    r = c.post(f"/api/vocab/{wid}/review")
    assert r.json()["stage"] == 1
    assert len(c.get("/api/vocab").json()) == 1
    r = c.delete(f"/api/vocab/{wid}")
    assert r.json()["ok"] is True


def test_vocab_review_missing_404(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "DATA_DIR", str(tmp_path))
    r = _client().post("/api/vocab/nope/review")
    assert r.status_code == 404


def test_overview_has_m2_fields(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "DATA_DIR", str(tmp_path))
    monkeypatch.setattr(main.weather_mod, "fetch_weather",
                        lambda lat, lon, timeout=5.0: {"temp": 25, "humidity": 60, "desc": "晴", "icon": "☀️"})
    body = _client().get("/api/overview").json()
    assert body["progress"] is not None
    assert body["ielts"] is not None
    assert body["review_due"] == 0
```

- [ ] **Step 2: 跑测试确认失败** → 至少 `test_progress_route` 报 `AttributeError: module 'app.main' has no attribute 'progress_mod'`

- [ ] **Step 3: 实现（main.py 追加 import、模型、路由；overview 填真值）**

在 `main.py` 顶部 import 区加：

```python
from . import ielts as ielts_mod
from . import progress as progress_mod
from . import vocab as vocab_mod
```

在 NicknameIn 模型后追加：

```python
class IeltsPatch(BaseModel):
    target_score: float | None = None
    current_band: str | None = None
    stage: str | None = None
    exam_date: str | None = None
    skills: dict | None = None


class VocabIn(BaseModel):
    word: str
    meaning: str


class VocabPatch(BaseModel):
    meaning: str
```

在配置路由后追加：

```python
# ── 学习进度 ───────────────────────────────────────────────
@app.get("/api/progress")
def api_progress():
    return progress_mod.load_progress()


# ── 雅思 ───────────────────────────────────────────────────
@app.get("/api/ielts")
def api_get_ielts():
    return ielts_mod.get_ielts()


@app.patch("/api/ielts")
def api_patch_ielts(body: IeltsPatch):
    return ielts_mod.update_ielts(body.model_dump(exclude_none=True))


# ── 生词本 ─────────────────────────────────────────────────
@app.get("/api/vocab")
def api_list_vocab():
    return vocab_mod.list_words()


@app.get("/api/vocab/due")
def api_due_vocab():
    return vocab_mod.due_words()


@app.post("/api/vocab")
def api_add_vocab(body: VocabIn):
    return vocab_mod.add_word(body.word, body.meaning)


@app.patch("/api/vocab/{word_id}")
def api_update_vocab(word_id: str, body: VocabPatch):
    try:
        return vocab_mod.update_meaning(word_id, body.meaning)
    except KeyError:
        raise HTTPException(404, f"生词不存在：{word_id}")


@app.post("/api/vocab/{word_id}/review")
def api_review_vocab(word_id: str):
    try:
        return vocab_mod.review(word_id)
    except KeyError:
        raise HTTPException(404, f"生词不存在：{word_id}")


@app.delete("/api/vocab/{word_id}")
def api_delete_vocab(word_id: str):
    try:
        vocab_mod.delete_word(word_id)
        return {"ok": True}
    except KeyError:
        raise HTTPException(404, f"生词不存在：{word_id}")
```

overview 的 M2 占位替换为真值：

```python
        # ── M2 数据闭环 ──
        "progress": progress_mod.load_progress(),
        "ielts": ielts_mod.get_ielts(),
        "review_due": len(vocab_mod.due_words()),
        # ── M3 填充 ──
        "ideas_today": [],
```

- [ ] **Step 4: 跑全量测试确认通过**

Run: `python -m pytest workbench\tests -v`
Expected: `39 passed`（原 29 + 新增 10）

- [ ] **Step 5: Commit** → `feat: 进度/雅思/生词路由 + overview 真数据`

---

## Task 5: 学习页前端

**Files:**
- Modify: `workbench/static/index.html`
- Modify: `workbench/static/style.css`
- Modify: `workbench/static/app.js`

- [ ] **Step 1: index.html — 学习页占位替换为真结构**

```html
    <section class="page" id="page-study">
      <div class="page-head">
        <h1>📚 学习</h1>
        <p class="page-sub" id="study-subject">加载中…</p>
      </div>
      <div class="grid">
        <div class="card">
          <div class="card-title">📈 课程进度 <span class="plan-count" id="study-progress-count"></span></div>
          <ul class="stage-list" id="study-stages"></ul>
        </div>
        <div class="card">
          <div class="card-title">✅ 测验记录</div>
          <table class="simple-table">
            <thead><tr><th>章节</th><th>状态</th><th>结果</th></tr></thead>
            <tbody id="study-table"></tbody>
          </table>
        </div>
        <div class="card">
          <div class="card-title">🔄 断点状态</div>
          <div class="kv" id="study-meta"></div>
        </div>
      </div>
    </section>
```

- [ ] **Step 2: style.css 追加**

```css
/* 学习页 */
.stage-list { list-style: none; display: flex; flex-direction: column; gap: 8px; }
.stage-item { display: flex; align-items: center; gap: 10px; font-size: 14px; }
.stage-dot {
  width: 20px; height: 20px; border-radius: 50%; flex-shrink: 0;
  display: flex; align-items: center; justify-content: center; font-size: 12px;
}
.stage-dot.done { background: var(--accent); color: var(--card); }
.stage-dot.todo { background: var(--accent-soft); color: var(--accent-ink); }
.stage-item.done .stage-text { color: var(--muted); }

.simple-table { width: 100%; border-collapse: collapse; font-size: 14px; }
.simple-table th, .simple-table td {
  text-align: left; padding: 7px 10px;
  border-bottom: 1px solid var(--card-border);
}
.simple-table th { color: var(--muted); font-weight: 600; }

.kv { display: flex; flex-direction: column; gap: 8px; font-size: 14px; }
.kv-row { display: flex; justify-content: space-between; gap: 12px; }
.kv-row .k { color: var(--muted); }
.kv-row .v { color: var(--ink); font-weight: 600; text-align: right; }
```

- [ ] **Step 3: app.js — 学习页渲染**

```js
// ── 学习页 ──
async function loadStudyPage() {
  const stageList = document.getElementById("study-stages");
  const tableBody = document.getElementById("study-table");
  const metaEl = document.getElementById("study-meta");
  try {
    const p = await api("/api/progress");
    if (p.missing) throw new Error("missing");
    document.getElementById("study-subject").textContent = p.subject;
    document.getElementById("study-progress-count").textContent =
      `(${p.done_count}/${p.total_count})`;
    stageList.innerHTML = p.stages.map((s) => `
      <li class="stage-item ${s.done ? "done" : ""}">
        <span class="stage-dot ${s.done ? "done" : "todo"}">${s.done ? "✓" : "○"}</span>
        <span class="stage-text">${escapeHtml(s.text)}</span>
      </li>`).join("") || '<li class="plan-empty">暂无阶段数据</li>';
    tableBody.innerHTML = p.chapters.map((c) => `
      <tr><td>${escapeHtml(c.chapter)}</td><td>${escapeHtml(c.status)}</td><td>${escapeHtml(c.result)}</td></tr>`).join("");
    metaEl.innerHTML = `
      <div class="kv-row"><span class="k">最后更新</span><span class="v">${escapeHtml(p.updated)}</span></div>
      <div class="kv-row"><span class="k">章节测验</span><span class="v">通过 ${p.chapters.length} 章</span></div>`;
  } catch {
    stageList.innerHTML = '<li class="plan-empty">进度文件未找到或解析失败</li>';
    tableBody.innerHTML = "";
    metaEl.innerHTML = "";
  }
}
```

- [ ] **Step 4: 手动验证**（浏览器打开 `#/study`，应显示科目/阶段清单/测验表）

---

## Task 6: 雅思页前端（看板 + 生词本）

**Files:**
- Modify: `workbench/static/index.html`
- Modify: `workbench/static/style.css`
- Modify: `workbench/static/app.js`

- [ ] **Step 1: index.html — 雅思页占位替换**

```html
    <section class="page" id="page-ielts">
      <div class="page-head">
        <h1>🎯 雅思</h1>
        <p class="page-sub">目标 6.5 · 基础强化</p>
      </div>
      <div class="grid">
        <div class="card">
          <div class="card-title">📊 进度看板</div>
          <div class="ielts-board">
            <div class="board-big" id="ielts-target">目标 —</div>
            <div class="board-row"><span class="k">当前水平</span><span class="v" id="ielts-band">—</span></div>
            <div class="board-row"><span class="k">备考阶段</span><span class="v" id="ielts-stage">—</span></div>
            <div class="board-row"><span class="k">考试日期</span><span class="v" id="ielts-exam">未定</span></div>
            <div class="skills" id="ielts-skills"></div>
          </div>
        </div>
        <div class="card">
          <div class="card-title">📖 生词本 · 今日复习 <span class="plan-count" id="vocab-due-count"></span></div>
          <form class="plan-form" id="vocab-form">
            <input class="plan-input" id="vocab-word" type="text" placeholder="单词" autocomplete="off">
            <input class="plan-input" id="vocab-meaning" type="text" placeholder="释义" autocomplete="off">
            <button class="btn-small" type="submit">添加</button>
          </form>
          <div class="vocab-due" id="vocab-due"></div>
        </div>
        <div class="card">
          <div class="card-title">🗂 全部生词 <span class="plan-count" id="vocab-total-count"></span></div>
          <ul class="vocab-list" id="vocab-list"></ul>
        </div>
      </div>
    </section>
```

- [ ] **Step 2: style.css 追加**

```css
/* 雅思页 */
.ielts-board { display: flex; flex-direction: column; gap: 10px; }
.board-big { font-size: 30px; font-weight: 700; text-align: center; color: var(--accent-ink); }
.board-row { display: flex; justify-content: space-between; font-size: 14px; }
.board-row .k { color: var(--muted); }
.board-row .v { font-weight: 600; }
.skills { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin-top: 6px; }
.skill-item {
  background: var(--bg); border-radius: 9px; padding: 8px 12px;
  display: flex; justify-content: space-between; font-size: 13.5px;
}
.skill-item .k { color: var(--muted); }
.skill-item .v { font-weight: 700; color: var(--accent-ink); }

.btn-small {
  border: none; background: var(--accent); color: var(--card);
  border-radius: 9px; padding: 0 16px; font-size: 14px; font-weight: 600; cursor: pointer;
}

.vocab-due { display: flex; flex-direction: column; gap: 8px; margin-bottom: 6px; }
.vocab-due-item {
  display: flex; align-items: center; gap: 10px;
  background: var(--bg); border-radius: 9px; padding: 9px 12px;
}
.vocab-due-item .word { font-weight: 700; font-size: 15px; min-width: 110px; }
.vocab-due-item .meaning { flex: 1; color: var(--muted); font-size: 13.5px; }
.vocab-due-item .stage-tag { font-size: 11.5px; color: var(--accent-ink); background: var(--accent-soft); padding: 2px 8px; border-radius: 20px; }

.vocab-list { list-style: none; display: flex; flex-direction: column; gap: 6px; }
.vocab-item {
  display: flex; align-items: center; gap: 10px;
  background: var(--bg); border-radius: 9px; padding: 8px 12px; font-size: 14px;
}
.vocab-item .word { font-weight: 600; min-width: 110px; }
.vocab-item .meaning { flex: 1; color: var(--muted); }
.vocab-item .next { font-size: 12px; color: var(--muted); }
```

- [ ] **Step 3: app.js — 雅思页渲染 + 交互**

```js
// ── 雅思页 ──
async function loadIeltsPage() {
  loadIeltsBoard();
  loadVocab();
}

async function loadIeltsBoard() {
  try {
    const i = await api("/api/ielts");
    document.getElementById("ielts-target").textContent = `目标 ${i.target_score}`;
    document.getElementById("ielts-band").textContent = i.current_band;
    document.getElementById("ielts-stage").textContent = i.stage;
    document.getElementById("ielts-exam").textContent = i.exam_date || "未定";
    document.getElementById("ielts-skills").innerHTML = Object.entries(i.skills).map(
      ([k, v]) => `<div class="skill-item"><span class="k">${k}</span><span class="v">${v || "—"}</span></div>`
    ).join("");
  } catch {
    document.getElementById("ielts-target").textContent = "数据加载失败";
  }
}

async function loadVocab() {
  const dueEl = document.getElementById("vocab-due");
  const listEl = document.getElementById("vocab-list");
  try {
    const [due, all] = await Promise.all([api("/api/vocab/due"), api("/api/vocab")]);
    document.getElementById("vocab-due-count").textContent = due.length ? `(${due.length})` : "";
    document.getElementById("vocab-total-count").textContent = `(${all.length})`;
    dueEl.innerHTML = due.length ? due.map((w) => `
      <div class="vocab-due-item">
        <span class="word">${escapeHtml(w.word)}</span>
        <span class="meaning">${escapeHtml(w.meaning)}</span>
        <span class="stage-tag">${w.stage + 1}/5</span>
        <button class="plan-del" data-review="${w.id}" title="复习打卡">✓</button>
      </div>`).join("") : '<div class="plan-empty">今天没有到期的生词 🎉</div>';
    listEl.innerHTML = all.length ? all.map((w) => `
      <li class="vocab-item">
        <span class="word">${escapeHtml(w.word)}</span>
        <span class="meaning">${escapeHtml(w.meaning)}</span>
        <span class="next">${w.next ? "下次 " + w.next : "🎓 已毕业"}</span>
        <button class="plan-del" data-del="${w.id}" title="删除">✕</button>
      </li>`).join("") : '<li class="plan-empty">还没有生词，先加一个吧</li>';
  } catch {
    dueEl.innerHTML = '<div class="plan-empty">生词数据加载失败</div>';
  }
}

// 添加生词
document.getElementById("vocab-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const word = document.getElementById("vocab-word").value.trim();
  const meaning = document.getElementById("vocab-meaning").value.trim();
  if (!word || !meaning) return;
  document.getElementById("vocab-word").value = "";
  document.getElementById("vocab-meaning").value = "";
  try {
    await api("/api/vocab", { method: "POST", body: JSON.stringify({ word, meaning }) });
  } catch { /* 静默 */ }
  loadVocab();
});

// 复习打卡 / 删除（事件委托）
document.getElementById("vocab-due").addEventListener("click", async (e) => {
  const btn = e.target.closest("[data-review]");
  if (!btn) return;
  try {
    await api(`/api/vocab/${btn.dataset.review}/review`, { method: "POST" });
  } catch { /* 静默 */ }
  loadVocab();
});
document.getElementById("vocab-list").addEventListener("click", async (e) => {
  const btn = e.target.closest("[data-del]");
  if (!btn) return;
  try {
    await api(`/api/vocab/${btn.dataset.del}`, { method: "DELETE" });
  } catch { /* 静默 */ }
  loadVocab();
});
```

- [ ] **Step 4: navigate() 增加页面加载**

```js
  if (page === "home") loadHome();
  if (page === "study") loadStudyPage();
  if (page === "ielts") loadIeltsPage();
```

---

## Task 7: 首页卡片换真数据

**Files:**
- Modify: `workbench/static/index.html`
- Modify: `workbench/static/app.js`

- [ ] **Step 1: index.html — 两张占位卡替换**

```html
        <!-- 学习进度 -->
        <div class="card">
          <div class="card-title">📚 学习进度</div>
          <div class="home-line" id="home-progress-line">加载中…</div>
          <div class="mini-bar"><i id="home-progress-bar" style="width:0%"></i></div>
          <div class="home-sub" id="home-progress-sub"></div>
        </div>

        <!-- 雅思速览 -->
        <div class="card">
          <div class="card-title">🎯 雅思速览</div>
          <div class="home-line" id="home-ielts-line">加载中…</div>
          <div class="home-sub" id="home-ielts-sub"></div>
        </div>
```

- [ ] **Step 2: style.css 追加**

```css
/* 首页真数据卡 */
.home-line { font-size: 15px; font-weight: 700; margin-bottom: 8px; }
.home-sub { color: var(--muted); font-size: 13px; margin-top: 8px; }
.mini-bar { height: 8px; border-radius: 4px; background: var(--accent-soft); overflow: hidden; }
.mini-bar i { display: block; height: 100%; background: var(--accent); border-radius: 4px; transition: width 0.4s; }
```

- [ ] **Step 3: app.js — loadHome 里加两个加载器**

```js
// 首页学习进度卡
async function loadHomeProgress() {
  const line = document.getElementById("home-progress-line");
  const bar = document.getElementById("home-progress-bar");
  const sub = document.getElementById("home-progress-sub");
  try {
    const p = await api("/api/progress");
    if (p.missing) throw new Error("missing");
    const ratio = p.total_count ? Math.round((p.done_count / p.total_count) * 100) : 0;
    line.textContent = p.subject || "学习进度";
    bar.style.width = ratio + "%";
    sub.textContent = `阶段完成 ${p.done_count}/${p.total_count} · 测验通过 ${p.chapters.length} 章`;
  } catch {
    line.textContent = "进度文件未找到";
    sub.textContent = "";
  }
}

// 首页雅思速览卡
async function loadHomeIelts() {
  const line = document.getElementById("home-ielts-line");
  const sub = document.getElementById("home-ielts-sub");
  try {
    const ov = await api("/api/overview");
    line.textContent = `目标 ${ov.ielts.target_score}`;
    sub.textContent = `今日到期生词 ${ov.review_due} 个 · ${ov.ielts.current_band}`;
  } catch {
    line.textContent = "雅思数据加载失败";
    sub.textContent = "";
  }
}
```

并加入 loadHome()：

```js
function loadHome() {
  loadGreeting();
  loadClock();
  loadPlan();
  loadWeather();
  loadHomeProgress();
  loadHomeIelts();
}
```

---

## Task 8: 端到端走查

- [ ] **Step 1: 起服务**

```bash
cd workbench && python run.py
```

- [ ] **Step 2: 浏览器验证**（puppeteer 或手测）
  - 首页：学习进度卡显示真实科目与进度条；雅思速览卡显示目标分与到期生词数
  - `#/study`：科目、阶段清单（带勾/圈）、测验记录表格
  - `#/ielts`：看板四科、添加生词 → 出现在全部生词；到期队列逻辑
  - 复习打卡 → stage 推进，词条移出到期队列

- [ ] **Step 3: 全量测试**

Run: `python -m pytest workbench\tests -v` → 全绿

- [ ] **Step 4: Commit** → `docs: M2 README 更新`

---

## 自检清单（写作时已核对）
- [x] 规格覆盖：§4 学习页/雅思页/首页卡 ↔ Task 5/6/7；艾宾浩斯 ↔ Task 3；overview ↔ Task 4
- [x] 无占位符：每个任务含完整代码
- [x] 类型一致：`review_due`/`progress`/`ielts` 字段名在 API 与前端一致
