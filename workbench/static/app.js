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
  if (page === "ideas") loadIdeasPage();
  if (page === "review") loadReviewPage();
  if (page === "tools") loadToolsPage();
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
    renderHomeIdeas(ov.ideas_today);
    renderHomeReview();
  } catch {
    document.getElementById("home-progress-body").textContent = "加载失败";
    document.getElementById("home-ielts-body").textContent = "加载失败";
  }
  loadHomeLinks();
}

// 首页收藏卡
async function loadHomeLinks() {
  const body = document.getElementById("home-links-body");
  try {
    const links = await api("/api/links");
    document.getElementById("home-links-count").textContent = links.length ? `(${links.length})` : "";
    body.innerHTML = links.length
      ? links.slice(0, 5).map((l) => `
        <div class="home-idea"><a class="nav-link" href="${escapeHtml(l.url)}" target="_blank" rel="noopener">🔗 ${escapeHtml(l.title)}</a>${l.note ? `<span class="muted-line"> — ${escapeHtml(l.note)}</span>` : ""}</div>`).join("")
      : '<div class="placeholder">还没有收藏，去工具页添加</div>';
  } catch {
    body.innerHTML = '<div class="placeholder">收藏加载失败</div>';
  }
}

// 首页灵感卡：今天有灵感就展示，没有就懒加载触发 AI 生成
function renderHomeIdeas(ideas) {
  const body = document.getElementById("home-ideas-body");
  document.getElementById("home-ideas-count").textContent = ideas.length ? `(${ideas.length})` : "";
  if (ideas.length) {
    body.innerHTML = ideas
      .slice(0, 3)
      .map((t) => `<div class="home-idea">💡 ${escapeHtml(t)}</div>`)
      .join("");
    return;
  }
  body.innerHTML = '<div class="placeholder">今日灵感正在生成…</div>';
  ensureTodayIdeas();  // 懒加载：为空才触发 AI（幂等，不会重复生成）
}

// 幂等生成今日灵感；AI 不可用时降级提示
async function ensureTodayIdeas() {
  try {
    const items = await api("/api/ideas/generate", { method: "POST" });
    const kept = items.filter((i) => i.status === "kept");
    renderHomeIdeas(kept.map((i) => i.text));
  } catch (e) {
    document.getElementById("home-ideas-body").innerHTML =
      '<div class="placeholder">🤖 AI 未配置或不可用<br>可在「灵感」页手动添加</div>';
  }
}

// 首页复盘卡：显示今日总结是否已写
async function renderHomeReview() {
  const el = document.getElementById("home-review-body");
  try {
    const r = await api("/api/reviews");
    const today = new Date().toISOString().slice(0, 10);
    if (r.summary) {
      el.innerHTML = `<div class="home-idea">📝 今日总结已写（${r.summary.length} 字）</div><div class="muted-line" style="margin-top:6px"><a class="nav-link" href="#/review">去查看 →</a></div>`;
    } else {
      el.innerHTML = `<div class="home-idea">今日总结还没写</div><div class="muted-line" style="margin-top:6px"><a class="nav-link" href="#/review">去写 →</a></div>`;
    }
  } catch {
    el.innerHTML = '<div class="placeholder">复盘数据加载失败</div>';
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

// ── 灵感页 ──
async function loadIdeasPage() {
  try {
    const all = await api("/api/ideas");
    const today = new Date().toISOString().slice(0, 10);
    const todayItems = all.filter((i) => i.date === today);
    renderIdeasToday(todayItems);
    renderIdeasAll(all);
    document.getElementById("ideas-ai-status").textContent =
      todayItems.length ? `今日已生成 ${todayItems.length} 条` : "今日批次为空，点击「换一批」生成";
  } catch {
    document.getElementById("ideas-today-list").innerHTML = '<li class="vocab-empty">加载失败</li>';
  }
}

function renderIdeasToday(items) {
  const listEl = document.getElementById("ideas-today-list");
  document.getElementById("ideas-today-count").textContent = items.length ? `(${items.length})` : "";
  listEl.innerHTML = items.length
    ? items.map((i) => {
      const action = i.status === "done"
        ? `<span class="vocab-stage">✅ 已采用</span>`
        : i.status === "discarded"
          ? `<button class="btn-small" data-idea-keep="${i.id}">捡回</button>`
          : `<button class="btn-small ghost" data-idea-discard="${i.id}">丢弃</button>
             <button class="btn-small" data-idea-adopt="${i.id}">✅ 采用</button>`;
      return `
      <li class="vocab-item">
        <span class="vocab-meaning" style="flex:1">${escapeHtml(i.text)}</span>
        <span class="vocab-stage">${i.source === "ai" ? "🤖 AI" : "✍️ 手动"}</span>
        ${action}
      </li>`;
    }).join("")
    : '<li class="vocab-empty">今日还没有灵感</li>';
}

function renderIdeasAll(all) {
  const listEl = document.getElementById("ideas-all-list");
  listEl.innerHTML = all.length
    ? all.slice(0, 20).map((i) => `
      <li class="vocab-item">
        <span class="vocab-word" style="min-width:80px">${escapeHtml(i.date)}</span>
        <span class="vocab-meaning" style="flex:1">${escapeHtml(i.text)}</span>
        <span class="vocab-stage">${i.status === "kept" ? "已收藏" : "已丢弃"}</span>
      </li>`).join("")
    : '<li class="vocab-empty">还没有任何灵感，添加或生成一个吧</li>';
}

// 换一批：AI 不可用时显示"重新连接"按钮
document.getElementById("ideas-generate-btn").addEventListener("click", async () => {
  const btn = document.getElementById("ideas-generate-btn");
  btn.textContent = "生成中…";
  btn.disabled = true;
  try {
    await api("/api/ideas/generate", { method: "POST" });
    document.getElementById("ideas-ai-fallback").style.display = "none";
    loadIdeasPage();
  } catch {
    document.getElementById("ideas-ai-status").textContent = "🤖 AI 不可用（未配置 key 或服务异常）";
    document.getElementById("ideas-ai-fallback").style.display = "inline-block";
  } finally {
    btn.textContent = "🎲 换一批";
    btn.disabled = false;
  }
});

document.getElementById("ideas-ai-fallback").addEventListener("click", () => {
  document.getElementById("ideas-generate-btn").click();
});

// 手动添加
document.getElementById("ideas-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const input = document.getElementById("ideas-text");
  const text = input.value.trim();
  if (!text) return;
  input.value = "";
  try {
    await api("/api/ideas", { method: "POST", body: JSON.stringify({ text }) });
  } catch { /* 兜底 */ }
  loadIdeasPage();
});

// 收藏/丢弃/采用（事件委托）
document.getElementById("ideas-today-list").addEventListener("click", async (e) => {
  const discard = e.target.closest("[data-idea-discard]");
  const keep = e.target.closest("[data-idea-keep]");
  const adopt = e.target.closest("[data-idea-adopt]");
  if (!discard && !keep && !adopt) return;
  const el = discard || keep || adopt;
  const id = el.dataset.ideaDiscard || el.dataset.ideaKeep || el.dataset.ideaAdopt;
  const status = discard ? "discarded" : adopt ? "done" : "kept";
  try {
    await api(`/api/ideas/${id}`, { method: "PATCH", body: JSON.stringify({ status }) });
  } catch { /* 兜底 */ }
  loadIdeasPage();
  loadHomeCards();
});

// ── 复盘页 ──
function isoWeek(date) {
  const d = new Date(Date.UTC(date.getFullYear(), date.getMonth(), date.getDate()));
  const dayNum = d.getUTCDay() || 7;
  d.setUTCDate(d.getUTCDate() + 4 - dayNum);
  const yearStart = new Date(Date.UTC(d.getUTCFullYear(), 0, 1));
  const weekNo = Math.ceil((((d - yearStart) / 86400000) + 1) / 7);
  return `${d.getUTCFullYear()}-W${String(weekNo).padStart(2, "0")}`;
}

async function loadReviewPage() {
  const today = new Date().toISOString().slice(0, 10);
  document.getElementById("review-date-picker").value = today;
  loadReviewForDate(today);
  loadContentReview();
  const week = isoWeek(new Date());
  document.getElementById("weekly-label").textContent = `（${week}）`;
  try {
    const w = await api(`/api/weekly?week=${week}`);
    if (w.summary) document.getElementById("weekly-summary").value = w.summary;
  } catch { /* 保持空 */ }
}

async function loadReviewForDate(dateStr) {
  document.getElementById("review-date-label").textContent = `（${dateStr}）`;
  try {
    const r = await api(`/api/reviews?date=${dateStr}`);
    document.getElementById("review-summary").value = r.summary || "";
  } catch { /* 保持空 */ }
}

// 内容复盘：灵感状态统计
async function loadContentReview() {
  const el = document.getElementById("content-review-body");
  try {
    const r = await api("/api/reviews/content");
    const { stats, adopted } = r;
    el.innerHTML = `
      <div class="board-grid" style="grid-template-columns:repeat(3,1fr)">
        <div class="board-stat"><div class="num">${stats.kept}</div><div class="label">🔖 收藏待做</div></div>
        <div class="board-stat"><div class="num">${stats.done}</div><div class="label">✅ 已采用</div></div>
        <div class="board-stat"><div class="num">${stats.discarded}</div><div class="label">🗑 已丢弃</div></div>
      </div>
      <div class="muted-line" style="margin:12px 0 6px">已采用的点子：</div>
      ${adopted.length ? adopted.slice(0, 10).map((i) =>
        `<div class="home-idea">✅ ${escapeHtml(i.text)} <span class="muted-line">(${i.date})</span></div>`).join("")
        : '<div class="placeholder">还没有采用任何灵感，去灵感页把点子变成现实 🚀</div>'}`;
  } catch {
    el.innerHTML = '<div class="placeholder">内容复盘加载失败</div>';
  }
}

// 日期选择器：回看历史总结
document.getElementById("review-date-picker").addEventListener("change", (e) => {
  if (e.target.value) loadReviewForDate(e.target.value);
});

document.getElementById("review-ai-btn").addEventListener("click", async () => {
  const btn = document.getElementById("review-ai-btn");
  btn.textContent = "起草中…";
  btn.disabled = true;
  const today = new Date().toISOString().slice(0, 10);
  try {
    const r = await api("/api/reviews/ai-draft", { method: "POST", body: JSON.stringify({ date: today }) });
    document.getElementById("review-summary").value = r.draft;
  } catch {
    document.getElementById("review-date-label").textContent = "（AI 不可用，请手动写）";
  } finally {
    btn.textContent = "🤖 AI 起草";
    btn.disabled = false;
  }
});

document.getElementById("review-save-btn").addEventListener("click", async () => {
  const today = new Date().toISOString().slice(0, 10);
  try {
    await api("/api/reviews", {
      method: "POST",
      body: JSON.stringify({ date: today, summary: document.getElementById("review-summary").value }),
    });
    document.getElementById("review-date-label").textContent = "（已保存 ✅）";
    loadHomeCards();
  } catch {
    document.getElementById("review-date-label").textContent = "（保存失败）";
  }
});

document.getElementById("weekly-ai-btn").addEventListener("click", async () => {
  const btn = document.getElementById("weekly-ai-btn");
  btn.textContent = "生成中…";
  btn.disabled = true;
  const week = isoWeek(new Date());
  try {
    const r = await api("/api/weekly/ai-draft", { method: "POST", body: JSON.stringify({ week }) });
    document.getElementById("weekly-summary").value = r.draft;
  } catch {
    document.getElementById("weekly-label").textContent = "（本周暂无记录或 AI 不可用）";
  } finally {
    btn.textContent = "🤖 AI 生成";
    btn.disabled = false;
  }
});

document.getElementById("weekly-save-btn").addEventListener("click", async () => {
  const week = isoWeek(new Date());
  try {
    await api("/api/weekly", {
      method: "POST",
      body: JSON.stringify({ week, summary: document.getElementById("weekly-summary").value }),
    });
    document.getElementById("weekly-label").textContent = "（已保存 ✅）";
  } catch {
    document.getElementById("weekly-label").textContent = "（保存失败）";
  }
});

// ── 工具页 ──
async function loadToolsPage() {
  loadLinksManager();
  try {
    const cfg = await api("/api/config");
    document.getElementById("set-nickname").value = cfg.nickname;
    document.getElementById("set-city").value = cfg.city;
    document.getElementById("set-lat").value = cfg.lat;
    document.getElementById("set-lon").value = cfg.lon;
    document.getElementById("set-status").textContent = `当前：${cfg.city}（${cfg.lat}, ${cfg.lon}）`;
  } catch { /* 表单保持空 */ }
}

// 抖音提取：提交 → 轮询任务 → 渲染结果
document.getElementById("douyin-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const input = document.getElementById("douyin-input");
  const text = input.value.trim();
  const ocr = document.getElementById("douyin-ocr").checked;
  if (!text) return;
  const box = document.getElementById("douyin-result");
  box.innerHTML = '<div class="muted-line">⏳ 已提交，正在后台解析（语音转文字需要几分钟）…</div>';
  try {
    const { job_id } = await api("/api/tools/douyin", {
      method: "POST",
      body: JSON.stringify({ text, ocr }),
    });
    pollDouyinJob(job_id);
  } catch (err) {
    box.innerHTML = `<div class="muted-line">❌ ${escapeHtml(err.message)}</div>`;
  }
});

async function pollDouyinJob(jobId) {
  const box = document.getElementById("douyin-result");
  for (let i = 0; i < 600; i++) {  // 最多轮询 10 分钟
    await new Promise((r) => setTimeout(r, 1000));
    let job;
    try {
      job = await api(`/api/tools/douyin/${jobId}`);
    } catch {
      box.innerHTML = '<div class="muted-line">❌ 任务查询失败</div>';
      return;
    }
    if (job.status === "running" || job.status === "pending") {
      box.innerHTML = `<div class="muted-line">⏳ ${job.status === "running" ? "解析中（通常 1-5 分钟）" : "排队中"}…</div>`;
      continue;
    }
    if (job.status === "error") {
      box.innerHTML = `<div class="muted-line">❌ 提取失败：${escapeHtml(job.error || "未知错误")}</div>`;
      return;
    }
    // done
    const r = job.result || {};
    const meta = r.metadata || {};
    const lines = [];
    if (meta.标题) lines.push(`📌 ${meta.标题}`);
    if (meta.作者) lines.push(`👤 ${meta.作者}`);
    if (meta["时长(秒)"]) lines.push(`⏱ ${Math.round(meta["时长(秒)"] / 60)} 分钟`);
    if (typeof r.transcript_length === "number") lines.push(`🗣 字幕 ${r.transcript_length} 字`);
    if (typeof r.ocr_count === "number") lines.push(`🔍 OCR ${r.ocr_count} 段`);
    if (r.report_path) lines.push(`📄 报告：${r.report_path}`);
    box.innerHTML = lines.length
      ? `<div class="muted-line">✅ 提取完成</div>${lines.map((l) => `<div class="home-idea">${l}</div>`).join("")}`
      : `<div class="muted-line">✅ 完成（无摘要输出）</div>`;
    return;
  }
  box.innerHTML = '<div class="muted-line">⏱ 轮询超时，请稍后在任务列表查看</div>';
}

// Obsidian 跳转：从服务端拿 URI 后交给浏览器协议处理器
document.querySelectorAll(".obsidian-btn").forEach((btn) => {
  btn.addEventListener("click", async () => {
    const kind = btn.dataset.obsidian;
    try {
      const { uri } = await api(`/api/obsidian/${kind}`);
      window.location.href = uri;
    } catch {
      btn.textContent = "获取失败";
      setTimeout(() => btn.textContent = kind === "daily" ? "📅 打开/新建今日日记" : "打开失败", 1500);
    }
  });
});

// 设置：昵称 / 城市 / 手动坐标
document.getElementById("set-nickname-btn").addEventListener("click", async () => {
  const nickname = document.getElementById("set-nickname").value.trim();
  if (!nickname) return;
  try {
    await api("/api/config/nickname", { method: "PATCH", body: JSON.stringify({ nickname }) });
    document.getElementById("set-status").textContent = "✅ 昵称已保存";
    loadGreeting();
  } catch {
    document.getElementById("set-status").textContent = "❌ 保存失败";
  }
});

document.getElementById("set-city-btn").addEventListener("click", async () => {
  const city = document.getElementById("set-city").value.trim();
  if (!city) return;
  try {
    const cfg = await api("/api/config/city", { method: "PATCH", body: JSON.stringify({ city }) });
    document.getElementById("set-lat").value = cfg.lat;
    document.getElementById("set-lon").value = cfg.lon;
    document.getElementById("set-status").textContent = `✅ 已定位到 ${cfg.city}`;
  } catch (e) {
    document.getElementById("set-status").textContent = "❌ 找不到该城市，请用手动坐标";
  }
});

document.getElementById("set-coords-btn").addEventListener("click", async () => {
  const city = document.getElementById("set-city").value.trim() || "自定义";
  const lat = parseFloat(document.getElementById("set-lat").value);
  const lon = parseFloat(document.getElementById("set-lon").value);
  if (Number.isNaN(lat) || Number.isNaN(lon)) {
    document.getElementById("set-status").textContent = "❌ 坐标必须是数字";
    return;
  }
  try {
    await api("/api/config/coords", { method: "PATCH", body: JSON.stringify({ city, lat, lon }) });
    document.getElementById("set-status").textContent = `✅ 已设置 ${city}（${lat}, ${lon}）`;
  } catch {
    document.getElementById("set-status").textContent = "❌ 保存失败";
  }
});

// 雅思任务模板：一键把常用任务加进今日计划
const IELTS_TEMPLATE = [
  "背 50 个雅思单词",
  "雅思听力练习 1 套",
  "精读 1 篇英文文章",
  "口语话题练习 5 分钟",
];

document.getElementById("ielts-template-btn").addEventListener("click", async () => {
  const statusEl = document.getElementById("ielts-template-status");
  try {
    // 已有的计划文本，避免重复添加
    const plan = await api("/api/plan");
    const existing = new Set(plan.items.map((i) => i.text));
    let added = 0;
    for (const t of IELTS_TEMPLATE) {
      if (!existing.has(t)) {
        await api("/api/plan/items", { method: "POST", body: JSON.stringify({ text: t }) });
        added++;
      }
    }
    statusEl.textContent = added ? `✅ 已添加 ${added} 项到今日计划` : "这些任务今天已经有了";
  } catch {
    statusEl.textContent = "❌ 添加失败";
  }
});

// ── 首页卡片拖拽排序（localStorage 记住顺序） ──
const HOME_ORDER_KEY = "home-card-order";

function applyHomeOrder() {
  try {
    const order = JSON.parse(localStorage.getItem(HOME_ORDER_KEY));
    if (!Array.isArray(order)) return;
    const grid = document.querySelector("#page-home .grid");
    const cards = grid.querySelectorAll(".card");
    const byId = new Map(cards.forEach ? [...cards].map((c) => [c.id, c]) : []);
    order.forEach((id) => {
      const card = byId.get(id);
      if (card) grid.appendChild(card);
    });
  } catch { /* 忽略损坏的存储 */ }
}

function setupHomeDrag() {
  const grid = document.querySelector("#page-home .grid");
  let dragged = null;
  grid.addEventListener("dragstart", (e) => {
    const card = e.target.closest(".card");
    if (!card) return;
    dragged = card;
    card.classList.add("dragging");
    e.dataTransfer.effectAllowed = "move";
  });
  grid.addEventListener("dragend", (e) => {
    const card = e.target.closest(".card");
    if (card) card.classList.remove("dragging");
    // 保存新顺序
    const order = [...grid.querySelectorAll(".card")].map((c) => c.id);
    localStorage.setItem(HOME_ORDER_KEY, JSON.stringify(order));
  });
  grid.addEventListener("dragover", (e) => {
    e.preventDefault();
    if (!dragged) return;
    const target = e.target.closest(".card");
    if (!target || target === dragged) return;
    const rect = target.getBoundingClientRect();
    const after = e.clientY > rect.top + rect.height / 2;
    grid.insertBefore(dragged, after ? target.nextSibling : target);
  });
}

// ── 资源收藏管理（工具页） ──
async function loadLinksManager() {
  const listEl = document.getElementById("links-list");
  try {
    const links = await api("/api/links");
    document.getElementById("links-count").textContent = links.length ? `(${links.length})` : "";
    listEl.innerHTML = links.length
      ? links.map((l) => `
        <li class="vocab-item">
          <a class="nav-link" href="${escapeHtml(l.url)}" target="_blank" rel="noopener" style="min-width:100px">${escapeHtml(l.title)}</a>
          <span class="vocab-meaning" style="flex:1">${escapeHtml(l.url)}</span>
          <button class="plan-del" data-link-del="${l.id}" title="删除">✕</button>
        </li>`).join("")
      : '<li class="vocab-empty">还没有收藏</li>';
  } catch {
    listEl.innerHTML = '<li class="vocab-empty">加载失败</li>';
  }
}

document.getElementById("links-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const title = document.getElementById("link-title").value.trim();
  const url = document.getElementById("link-url").value.trim();
  if (!title || !url) return;
  document.getElementById("link-title").value = "";
  document.getElementById("link-url").value = "";
  try {
    await api("/api/links", { method: "POST", body: JSON.stringify({ title, url }) });
  } catch (err) {
    document.getElementById("links-count").textContent = "（链接必须以 http(s):// 开头）";
    setTimeout(() => loadLinksManager(), 1500);
    return;
  }
  loadLinksManager();
  loadHomeLinks();
});

document.getElementById("links-list").addEventListener("click", async (e) => {
  const btn = e.target.closest("[data-link-del]");
  if (!btn) return;
  try {
    await api(`/api/links/${btn.dataset.linkDel}`, { method: "DELETE" });
  } catch { /* 兜底 */ }
  loadLinksManager();
  loadHomeLinks();
});

// ── 启动 ──
window.addEventListener("hashchange", navigate);
applyHomeOrder();
setupHomeDrag();
navigate();
