/* ═══════════════════════════════════════
   个人工作台前端逻辑
   hash 路由 · 时钟 · 天气 · 今日计划 · 学习 · 雅思生词本
   设计原则：每个卡片独立加载、独立容错，坏一个不影响整页
   ═══════════════════════════════════════ */

// ── 基础请求封装 ──
async function api(path, options = {}) {
  const resp = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!resp.ok) throw new Error(`${path} → HTTP ${resp.status}`);
  return resp.json();
}

// ── hash 路由 ──
const PAGES = ["home", "study", "ielts", "ideas", "review", "tools"];

function navigate() {
  const hash = location.hash.replace(/^#\//, "") || "home";
  const page = PAGES.includes(hash) ? hash : "home";
  document.querySelectorAll(".nav-item").forEach((el) =>
    el.classList.toggle("active", el.dataset.page === page));
  document.querySelectorAll(".page").forEach((el) =>
    el.classList.toggle("active", el.id === `page-${page}`));
  if (page === "home") loadHome();
  if (page === "study") loadStudyPage();
  if (page === "ielts") loadIeltsPage();
}

// ── 首页：各卡片并行加载，互不拖累 ──
function loadHome() {
  loadGreeting();
  loadClock();
  loadPlan();
  loadWeather();
  loadHomeCards();
}

// 问候语 + 日期行
async function loadGreeting() {
  try {
    const ov = await api("/api/overview");
    document.getElementById("greeting").textContent = `你好，${ov.nickname} 👋`;
    document.getElementById("today-line").textContent = `${ov.date} · 今日天气看板 · ${ov.city}`;
    document.getElementById("sidebar-nickname").textContent = ov.nickname;
  } catch {
    document.getElementById("greeting").textContent = "你好 👋";
    document.getElementById("today-line").textContent = "服务连接失败";
  }
}

// 首页学习/雅思卡片（一次 overview 拿全，单卡容错）
async function loadHomeCards() {
  try {
    const ov = await api("/api/overview");
    renderHomeProgress(ov.progress);
    renderHomeIelts(ov.ielts, ov.review_due);
  } catch {
    document.getElementById("home-progress-body").textContent = "加载失败";
    document.getElementById("home-ielts-body").textContent = "加载失败";
  }
}

function renderHomeProgress(p) {
  const el = document.getElementById("home-progress-body");
  if (!p || p.missing || !p.subject) {
    el.innerHTML = '<div class="placeholder">未找到 study_progress.md</div>';
    return;
  }
  const done = p.done_count;
  const total = p.total_count || 0;
  const pct = total ? Math.round((done / total) * 100) : 0;
  el.innerHTML = `
    <div class="big-number">${escapeHtml(p.subject)}</div>
    <div class="muted-line">阶段完成 ${done}/${total} · 测验 ${p.chapters.length} 章</div>
    <div class="skill-bar" style="margin-top:10px"><i style="width:${pct}%"></i></div>
    <div class="muted-line" style="margin-top:6px">最后更新 ${p.updated || "—"}</div>`;
}

function renderHomeIelts(ielts, reviewDue) {
  const el = document.getElementById("home-ielts-body");
  if (!ielts) {
    el.innerHTML = '<div class="placeholder">雅思数据加载失败</div>';
    return;
  }
  const reviewText = reviewDue > 0 ? `<span class="vocab-stage">⏰ ${reviewDue} 个生词到期</span>` : "今日无复习任务";
  el.innerHTML = `
    <div class="big-number">目标 ${ielts.target_score} 分</div>
    <div class="muted-line">当前 ${ielts.current_band || "—"} · ${escapeHtml(ielts.stage)}</div>
    <div class="muted-line" style="margin-top:10px">${reviewText}</div>`;
}

// 时钟（每秒刷新）
function loadClock() {
  const timeEl = document.getElementById("clock-time");
  const dateEl = document.getElementById("clock-date");
  const weekdays = ["日", "一", "二", "三", "四", "五", "六"];
  const tick = () => {
    const now = new Date();
    const hh = String(now.getHours()).padStart(2, "0");
    const mm = String(now.getMinutes()).padStart(2, "0");
    timeEl.textContent = `${hh}:${mm}`;
    dateEl.textContent =
      `${now.getFullYear()}年${now.getMonth() + 1}月${now.getDate()}日 星期${weekdays[now.getDay()]}`;
  };
  tick();
  setInterval(tick, 1000);
}

// 天气（单卡容错：失败只影响这张卡）
async function loadWeather() {
  const el = document.getElementById("weather-line");
  try {
    const w = await api("/api/weather");
    if (w.error) throw new Error("degraded");
    el.textContent = `${w.icon} ${w.desc} ${w.temp}°C · 湿度 ${w.humidity}%`;
  } catch {
    el.textContent = "🌡️ 天气暂不可用";
  }
}

// ── 今日计划 ──
async function loadPlan() {
  const listEl = document.getElementById("plan-list");
  try {
    const plan = await api("/api/plan");
    renderPlan(plan.items);
  } catch {
    listEl.innerHTML = '<li class="plan-empty">计划加载失败</li>';
  }
}

function renderPlan(items) {
  const listEl = document.getElementById("plan-list");
  document.getElementById("plan-count").textContent = items.length ? `(${items.length})` : "";
  if (!items.length) {
    listEl.innerHTML = '<li class="plan-empty">今天还没有计划，先加一项吧 ✨</li>';
    return;
  }
  listEl.innerHTML = items
    .map(
      (it) => `
    <li class="plan-item ${it.done ? "done" : ""}">
      <button class="plan-check ${it.done ? "checked" : ""}" data-id="${it.id}" title="完成">✓</button>
      <span class="plan-text">${escapeHtml(it.text)}</span>
      <button class="plan-del" data-id="${it.id}" title="删除">✕</button>
    </li>`
    )
    .join("");
}

// 转义 HTML：防止用户输入被当作标签执行（XSS 防护）
function escapeHtml(s) {
  return s.replace(/[&<>"']/g, (c) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;",
  })[c]);
}

// 新增计划：回车提交
document.getElementById("plan-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const input = document.getElementById("plan-input");
  const text = input.value.trim();
  if (!text) return;
  input.value = "";
  try {
    await api("/api/plan/items", { method: "POST", body: JSON.stringify({ text }) });
  } catch { /* 失败由 loadPlan 兜底提示 */ }
  loadPlan();
});

// 列表事件委托：勾选 / 删除 共用一个监听
// 好处：列表增删后不用重新绑定事件，性能好且不易出 bug
document.getElementById("plan-list").addEventListener("click", async (e) => {
  const check = e.target.closest(".plan-check");
  const del = e.target.closest(".plan-del");
  if (!check && !del) return;
  const id = (check || del).dataset.id;
  try {
    if (check) {
      await api(`/api/plan/items/${id}`, {
        method: "PATCH",
        body: JSON.stringify({ done: !check.classList.contains("checked") }),
      });
    } else {
      await api(`/api/plan/items/${id}`, { method: "DELETE" });
    }
  } catch { /* 同上 */ }
  loadPlan();
});

// ── 学习页 ──
async function loadStudyPage() {
  try {
    const p = await api("/api/progress");
    renderStudy(p);
  } catch {
    document.getElementById("study-subject").textContent = "加载失败";
  }
}

function renderStudy(p) {
  document.getElementById("study-subject").textContent = p.subject || "（未设置科目）";
  document.getElementById("study-meta").textContent =
    `最后更新 ${p.updated || "—"} · 阶段完成 ${p.done_count}/${p.total_count}`;

  // 阶段清单
  const stagesEl = document.getElementById("study-stages");
  if (!p.stages.length) {
    stagesEl.innerHTML = '<li class="vocab-empty">暂无阶段记录</li>';
  } else {
    stagesEl.innerHTML = p.stages
      .map((s) => `
      <li class="stage-item ${s.done ? "done" : ""}">
        <span class="stage-mark">${s.done ? "✅" : "⬜"}</span>
        <span class="stage-text">${escapeHtml(s.text)}</span>
      </li>`)
      .join("");
  }

  // 测验记录表
  const tableEl = document.getElementById("study-chapters");
  if (!p.chapters.length) {
    tableEl.innerHTML = '<tr><td class="vocab-empty">暂无测验记录</td></tr>';
  } else {
    tableEl.innerHTML = `
      <tr><th>章节</th><th>状态</th><th>结果</th></tr>
      ${p.chapters
        .map((c) => `<tr><td>${escapeHtml(c.chapter)}</td><td>${escapeHtml(c.status)}</td><td>${escapeHtml(c.result)}</td></tr>`)
        .join("")}`;
  }
}

// ── 雅思页 ──
async function loadIeltsPage() {
  loadIeltsBoard();
  loadVocab();
  loadVocabDue();
}

async function loadIeltsBoard() {
  const el = document.getElementById("ielts-board-body");
  try {
    const i = await api("/api/ielts");
    const skillBars = Object.entries(i.skills)
      .map(([name, band]) => {
        const pct = band ? Math.min(100, Math.round((parseFloat(band) / 9) * 100)) : 0;
        return `
        <div class="skill-row">
          <span class="skill-name">${escapeHtml(name)}</span>
          <div class="skill-bar"><i style="width:${pct}%"></i></div>
          <span class="skill-value">${escapeHtml(band) || "—"}</span>
        </div>`;
      })
      .join("");
    el.innerHTML = `
      <div class="board-grid">
        <div class="board-stat"><div class="num">${i.target_score}</div><div class="label">目标分</div></div>
        <div class="board-stat"><div class="num">${escapeHtml(i.current_band) || "—"}</div><div class="label">当前水平</div></div>
      </div>
      <div class="muted-line" style="margin-top:10px">阶段：${escapeHtml(i.stage)}${i.exam_date ? ` · 考试：${escapeHtml(i.exam_date)}` : ""}</div>
      <div style="margin-top:8px">${skillBars}</div>`;
  } catch {
    el.innerHTML = '<div class="placeholder">雅思数据加载失败</div>';
  }
}

async function loadVocab() {
  const listEl = document.getElementById("vocab-list");
  try {
    const words = await api("/api/vocab");
    listEl.innerHTML = words.length
      ? words.map((w) => vocabItemHtml(w)).join("")
      : '<li class="vocab-empty">生词本是空的，添加第一个单词吧 📖</li>';
  } catch {
    listEl.innerHTML = '<li class="vocab-empty">加载失败</li>';
  }
}

async function loadVocabDue() {
  const listEl = document.getElementById("vocab-due-list");
  try {
    const due = await api("/api/vocab/due");
    document.getElementById("vocab-due-count").textContent = due.length ? `(${due.length})` : "";
    listEl.innerHTML = due.length
      ? due.map((w) => `
        <li class="vocab-item">
          <span class="vocab-word">${escapeHtml(w.word)}</span>
          <span class="vocab-meaning">${escapeHtml(w.meaning)}</span>
          <button class="btn-small" data-review="${w.id}">打卡</button>
        </li>`).join("")
      : '<li class="vocab-empty">今天没有到期的单词 🎉</li>';
  } catch {
    listEl.innerHTML = '<li class="vocab-empty">加载失败</li>';
  }
}

function vocabItemHtml(w) {
  const stageLabel = w.stage >= 5 ? "🎓 毕业" : `第 ${w.stage + 1} 轮复习`;
  return `
    <li class="vocab-item">
      <span class="vocab-word">${escapeHtml(w.word)}</span>
      <span class="vocab-meaning">${escapeHtml(w.meaning)}</span>
      <span class="vocab-stage">${stageLabel}${w.next ? " · " + w.next : ""}</span>
      <button class="plan-del" data-del="${w.id}" title="删除">✕</button>
    </li>`;
}

// 添加生词
document.getElementById("vocab-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const wordEl = document.getElementById("vocab-word");
  const meaningEl = document.getElementById("vocab-meaning");
  const word = wordEl.value.trim();
  const meaning = meaningEl.value.trim();
  if (!word) return;
  wordEl.value = "";
  meaningEl.value = "";
  try {
    await api("/api/vocab", { method: "POST", body: JSON.stringify({ word, meaning }) });
  } catch { /* 兜底由 loadVocab 提示 */ }
  loadVocab();
  loadVocabDue();
});

// 复习打卡 / 删除（事件委托）
document.getElementById("vocab-due-list").addEventListener("click", async (e) => {
  const btn = e.target.closest("[data-review]");
  if (!btn) return;
  try {
    await api(`/api/vocab/${btn.dataset.review}/review`, { method: "POST" });
  } catch { /* 同上 */ }
  loadVocabDue();
  loadVocab();
  loadHomeCards();
});

document.getElementById("vocab-list").addEventListener("click", async (e) => {
  const btn = e.target.closest("[data-del]");
  if (!btn) return;
  try {
    await api(`/api/vocab/${btn.dataset.del}`, { method: "DELETE" });
  } catch { /* 同上 */ }
  loadVocab();
  loadVocabDue();
});

// ── 启动 ──
window.addEventListener("hashchange", navigate);
navigate();
