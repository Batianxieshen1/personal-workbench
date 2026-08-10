/* ═══════════════════════════════════════
   个人工作台前端逻辑
   hash 路由 · 时钟 · 天气 · 今日计划 · 学习 · 雅思生词本
   设计原则：每个卡片独立加载、独立容错，坏一个不影响整页
   ═══════════════════════════════════════ */

// ── i18n 中英双语 ──
const I18N = {
  zh: {
    "brand": "个人工作台",
    "nav.group.today": "🗓 今日",
    "nav.group.study": "📖 学习",
    "nav.group.record": "✨ 记录",
    "nav.group.sys": "⚙️ 系统",
    "nav.home": "首页", "nav.study": "学习", "nav.ielts": "雅思", "nav.ideas": "灵感",
    "nav.review": "复盘", "nav.stats": "统计", "nav.tools": "工具",
    "nav.news": "资讯", "nav.funds": "基金",
    "page.study": "📚 学习", "page.ielts": "🎯 雅思", "page.ideas": "💡 灵感",
    "page.review": "📝 复盘", "page.stats": "📊 统计", "page.tools": "🛠 工具",
    "page.news": "📰 资讯", "page.funds": "💰 基金涨跌",
    "guide.title": "今日行动",
    "card.plan": "今日计划", "card.progress": "学习进度", "card.ielts": "雅思速览",
    "card.ideas": "今日灵感", "card.review": "内容复盘", "card.links": "资源收藏",
    "card.subject": "科目", "card.stages": "当前阶段", "card.plan-info": "备考计划",
    "card.pomodoro": "番茄钟", "card.quiz": "测验记录", "card.board": "进度看板",
    "card.due": "今日复习队列", "card.template": "雅思任务模板", "card.vocab": "生词本",
    "card.batch": "今日批次", "card.manual": "手动添加", "card.summary": "每日总结",
    "card.weekly": "周报", "card.content": "内容复盘", "card.streak": "连续学习",
    "card.week-rate": "本周完成率", "card.adopt": "灵感采用率", "card.trend": "近 7 天完成趋势",
    "card.douyin": "抖音视频提取", "card.obsidian": "Obsidian 联动",
    "card.settings": "设置", "card.data": "数据",
    "card.news": "新闻简讯", "card.funds": "基金涨跌",
  },
  en: {
    "brand": "Workbench",
    "nav.group.today": "🗓 TODAY",
    "nav.group.study": "📖 STUDY",
    "nav.group.record": "✨ RECORDS",
    "nav.group.sys": "⚙️ SYSTEM",
    "nav.home": "Home", "nav.study": "Study", "nav.ielts": "IELTS", "nav.ideas": "Ideas",
    "nav.review": "Review", "nav.stats": "Stats", "nav.tools": "Tools",
    "nav.news": "News", "nav.funds": "Funds",
    "page.study": "📚 Study", "page.ielts": "🎯 IELTS", "page.ideas": "💡 Ideas",
    "page.review": "📝 Review", "page.stats": "📊 Stats", "page.tools": "🛠 Tools",
    "page.news": "📰 News", "page.funds": "💰 Funds",
    "guide.title": "Today's Plan",
    "card.plan": "Today's Plan", "card.progress": "Study Progress", "card.ielts": "IELTS",
    "card.ideas": "Today's Ideas", "card.review": "Review", "card.links": "Bookmarks",
    "card.subject": "Subject", "card.stages": "Milestones", "card.plan-info": "Study Plan",
    "card.pomodoro": "Pomodoro", "card.quiz": "Quiz Log", "card.board": "Dashboard",
    "card.due": "Review Queue", "card.template": "IELTS Tasks", "card.vocab": "Vocabulary",
    "card.batch": "Today's Batch", "card.manual": "Add Manually", "card.summary": "Daily Summary",
    "card.weekly": "Weekly Report", "card.content": "Content Review", "card.streak": "Streak",
    "card.week-rate": "Week Rate", "card.adopt": "Adoption Rate", "card.trend": "7-Day Trend",
    "card.douyin": "Douyin Extract", "card.obsidian": "Obsidian",
    "card.settings": "Settings", "card.data": "Data",
    "card.news": "News", "card.funds": "Funds",
  },
};

let LANG = "zh";
function t(key) {
  return (I18N[LANG] && I18N[LANG][key]) || I18N.zh[key] || key;
}
function applyI18n() {
  // 只替换"叶子元素"（不含子元素的节点），避免误删按钮/计数等子结构
  document.querySelectorAll("[data-i18n]").forEach((el) => {
    if (el.children.length === 0) el.textContent = t(el.dataset.i18n);
  });
}
// 启动时从后端读取语言偏好
async function initLanguage() {
  try {
    const cfg = await api("/api/config");
    LANG = cfg.language === "en" ? "en" : "zh";
  } catch { /* 默认中文 */ }
  applyI18n();
  document.dispatchEvent(new CustomEvent("lang-ready"));
}

// ── 基础请求封装（30 秒超时，防止 AI 慢时无限等待） ──
async function api(path, options = {}) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 30000);
  try {
    const resp = await fetch(path, {
      headers: { "Content-Type": "application/json" },
      signal: controller.signal,
      ...options,
    });
    if (!resp.ok) throw new Error(`${path} → HTTP ${resp.status}`);
    return resp.json();
  } finally {
    clearTimeout(timer);
  }
}

// ── hash 路由 ──
const PAGES = ["home", "study", "ielts", "ideas", "review", "stats", "news", "funds", "tools"];

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
  if (page === "stats") loadStatsPage();
  if (page === "news") loadNews();
  if (page === "funds") { loadFunds(); loadFundManager(); }
  if (page === "tools") loadToolsPage();
}

// ── 首页：各卡片并行加载，互不拖累 ──
function loadHome() {
  loadGreeting();
  loadClock();
  loadPlan();
  loadWeather();
  loadHomeCards();
  loadGuide();
  loadGuideNav();
  loadNotify();
}

// ── 浏览器通知提醒 ──
function notify(title, body) {
  if (!("Notification" in window) || Notification.permission !== "granted") return;
  try { new Notification(title, { body }); } catch { /* 静默 */ }
}

async function checkAndNotify() {
  if (!("Notification" in window) || Notification.permission !== "granted") return;
  try {
    const due = await api("/api/vocab/due");
    if (due.length) notify("⏰ 生词到期了", `今天有 ${due.length} 个生词要复习（艾宾浩斯）`);
    const today = new Date().toISOString().slice(0, 10);
    const r = await api(`/api/reviews?date=${today}`);
    if (!r.summary) notify("📝 别忘了写总结", "今天的总结还没写，睡前花 2 分钟回顾一下");
  } catch { /* 通知失败不影响使用 */ }
}

document.getElementById("notify-btn").addEventListener("click", async () => {
  const btn = document.getElementById("notify-btn");
  if (!("Notification" in window)) {
    btn.textContent = "浏览器不支持";
    return;
  }
  const perm = await Notification.requestPermission();
  if (perm === "granted") {
    btn.textContent = "🔔 已开启";
    notify("✅ 提醒已开启", "生词到期 / 总结未写时会提醒你");
    checkAndNotify();
  } else {
    btn.textContent = "🔕 被拒绝了（浏览器设置里开）";
  }
});

// 已授权时每次回首页自动检查
function loadNotify() {
  if ("Notification" in window && Notification.permission === "granted") {
    document.getElementById("notify-btn").textContent = "🔔 已开启";
    checkAndNotify();
  }
}

// ── 今日行动指南 ──
const GUIDE_DOT = { 1: "🔴", 2: "🔴", 3: "🟡", 4: "🟡", 5: "🟢" };

// AI 晨间导航（独立加载，失败只隐藏该块）
async function loadGuideNav() {
  const el = document.getElementById("guide-nav");
  el.innerHTML = '<div class="muted-line">🤖 正在生成今日导航…</div>';
  try {
    const nav = await api("/api/guide/nav");
    if (nav.error) {
      el.innerHTML = "";
      return;
    }
    el.innerHTML = '<div class="guide-nav-text"></div>';
    typewriter(el.querySelector(".guide-nav-text"), nav.text);
  } catch {
    el.innerHTML = "";
  }
}

async function loadGuide(retry = true) {
  const listEl = document.getElementById("guide-list");
  try {
    const actions = await api("/api/guide");
    document.getElementById("guide-count").textContent = actions.length ? `(${actions.length})` : "";
    if (!actions.length) {
      listEl.innerHTML = '<li class="guide-item" style="border:none">🎉 今日行动全部完成，休息吧！</li>';
      return;
    }
    listEl.innerHTML = actions
      .map((a) => `
      <li class="guide-item">
        <span class="guide-dot">${GUIDE_DOT[a.priority] || "🔵"}</span>
        <span class="guide-text">${escapeHtml(a.text)}</span>
        <button class="btn-small ghost" data-guide-page="${a.page}" data-guide-target="${a.target}">去处理 →</button>
      </li>`)
      .join("");
    // 一键跳转 + 聚焦
    listEl.querySelectorAll("[data-guide-page]").forEach((btn) => {
      btn.addEventListener("click", () => {
        location.hash = `#/${btn.dataset.guidePage}`;
        setTimeout(() => {
          const el = document.getElementById(btn.dataset.guideTarget);
          if (el) {
            el.scrollIntoView({ behavior: "smooth", block: "center" });
            if (el.tagName === "INPUT" || el.tagName === "TEXTAREA") el.focus();
          }
        }, 300);
      });
    });
  } catch (e) {
    // 失败自动重试一次（服务重启瞬间的连接拒绝很常见），再失败显示原因
    if (retry) {
      setTimeout(() => loadGuide(false), 1200);
      listEl.innerHTML = '<li class="guide-item" style="border:none">🔄 加载中…</li>';
      return;
    }
    listEl.innerHTML = `<li class="guide-item" style="border:none">⚠️ 指南加载失败（${escapeHtml(e.message || "未知错误")}）</li>`;
  }
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
      : '<div class="placeholder">还没有收藏<br><a class="nav-link" href="#/tools">去工具页添加 →</a></div>';
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
      el.innerHTML = `<div class="home-idea" style="color:var(--danger)">⚠️ 今天还没写总结</div><div class="muted-line" style="margin-top:6px"><a class="nav-link" href="#/review">去写 →</a></div>`;
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
  let lastMinute = "";
  const tick = () => {
    const now = new Date();
    const hh = String(now.getHours()).padStart(2, "0");
    const mm = String(now.getMinutes()).padStart(2, "0");
    const minute = `${hh}:${mm}`;
    timeEl.textContent = minute;
    // 分钟变化时来一次脉冲动效
    if (minute !== lastMinute) {
      timeEl.classList.remove("tick");
      void timeEl.offsetWidth;  // 强制重排，让动画可重放
      timeEl.classList.add("tick");
      lastMinute = minute;
    }
    dateEl.textContent =
      `${now.getFullYear()}年${now.getMonth() + 1}月${now.getDate()}日 星期${weekdays[now.getDay()]}`;
  };
  tick();
  // 防泄漏：每次进入首页先清掉旧定时器再启动（loadHome 会被反复调用）
  if (window.__clockTimer) clearInterval(window.__clockTimer);
  window.__clockTimer = setInterval(tick, 1000);
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
    listEl.innerHTML = '<li class="plan-empty">✨ 今天还没有计划，先加一项吧</li>';
    return;
  }
  // 重要任务排前面（未完成的在前）
  const sorted = [...items].sort((a, b) => {
    if ((b.important || false) !== (a.important || false)) return (b.important ? 1 : 0) - (a.important ? 1 : 0);
    return (a.done ? 1 : 0) - (b.done ? 1 : 0);
  });
  listEl.innerHTML = sorted
    .map((it) => {
      const doneAt = it.done_at ? ` · ${it.done_at.slice(11, 16)} 完成` : "";
      return `
    <li class="plan-item ${it.done ? "done" : ""}">
      <button class="plan-check ${it.done ? "checked" : ""}" data-id="${it.id}" title="完成">✓</button>
      <button class="plan-star ${it.important ? "on" : ""}" data-star="${it.id}" title="标记重要">★</button>
      <span class="plan-text" data-edit="${it.id}" title="双击编辑">${escapeHtml(it.text)}${doneAt ? `<span class="muted-line" style="font-size:11px">${doneAt}</span>` : ""}</span>
      <button class="plan-del" data-id="${it.id}" title="删除">✕</button>
    </li>`;
    })
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

// 列表事件委托：勾选 / 删除 / 星标 / 双击编辑 共用一个监听
document.getElementById("plan-list").addEventListener("click", async (e) => {
  const star = e.target.closest("[data-star]");
  if (star) {
    try {
      await api(`/api/plan/items/${star.dataset.star}`, {
        method: "PATCH",
        body: JSON.stringify({ important: !star.classList.contains("on") }),
      });
    } catch { /* 兜底 */ }
    loadPlan();
    return;
  }
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

// 双击编辑计划文字
document.getElementById("plan-list").addEventListener("dblclick", async (e) => {
  const span = e.target.closest("[data-edit]");
  if (!span) return;
  const current = span.childNodes[0]?.textContent?.trim() || "";
  const text = prompt("修改计划内容：", current);
  if (text === null || !text.trim()) return;
  try {
    await api(`/api/plan/items/${span.dataset.edit}`, {
      method: "PATCH",
      body: JSON.stringify({ text: text.trim() }),
    });
  } catch { /* 兜底 */ }
  loadPlan();
});

// ── 学习页 ──
async function loadStudyPage() {
  loadStudyPlan();
  try {
    const p = await api("/api/progress");
    renderStudy(p);
  } catch {
    document.getElementById("study-subject").textContent = "加载失败";
  }
}

// 备考计划卡
async function loadStudyPlan() {
  const el = document.getElementById("study-plan-stages");
  try {
    const plan = await api("/api/plan-info");
    if (plan.missing || !plan.stages.length) {
      el.innerHTML = '<li class="vocab-empty">未找到 study_plan.md</li>';
      return;
    }
    el.innerHTML = plan.stages
      .map((s) => `
      <li class="stage-item ${s.done ? "done" : ""}">
        <span class="stage-mark">${s.done ? "✅" : "⬜"}</span>
        <span class="stage-text">${escapeHtml(s.text)}</span>
      </li>`)
      .join("");
  } catch {
    el.innerHTML = '<li class="vocab-empty">加载失败</li>';
  }
}

// 阶段勾选：点击写回 study_progress.md
function renderStudy(p) {
  document.getElementById("study-subject").textContent = p.subject || "（未设置科目）";
  document.getElementById("study-meta").textContent =
    `最后更新 ${p.updated || "—"} · 阶段完成 ${p.done_count}/${p.total_count}`;

  // 阶段清单（可点击勾选）
  const stagesEl = document.getElementById("study-stages");
  if (!p.stages.length) {
    stagesEl.innerHTML = '<li class="vocab-empty">暂无阶段记录</li>';
  } else {
    stagesEl.innerHTML = p.stages
      .map((s, i) => `
      <li class="stage-item ${s.done ? "done" : ""}" style="cursor:pointer">
        <button class="plan-check ${s.done ? "checked" : ""}" data-stage="${i}" title="点击切换完成状态">✓</button>
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

// 勾选事件委托
document.getElementById("study-stages").addEventListener("click", async (e) => {
  const btn = e.target.closest("[data-stage]");
  if (!btn) return;
  const index = parseInt(btn.dataset.stage, 10);
  const willDone = !btn.classList.contains("checked");
  try {
    await api(`/api/progress/stages/${index}`, {
      method: "PATCH",
      body: JSON.stringify({ done: willDone }),
    });
  } catch { /* 兜底 */ }
  loadStudyPage();
  loadHomeCards();
});

// 番茄钟完成提示音（Web Audio 生成三声"叮"，零依赖）
function playChime() {
  try {
    const Ctx = window.AudioContext || window.webkitAudioContext;
    const ctx = new Ctx();
    [0, 0.28, 0.56].forEach((t, i) => {
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.frequency.value = 880 + i * 220;
      osc.type = "sine";
      osc.connect(gain);
      gain.connect(ctx.destination);
      const start = ctx.currentTime + t;
      gain.gain.setValueAtTime(0.001, start);
      gain.gain.exponentialRampToValueAtTime(0.3, start + 0.02);
      gain.gain.exponentialRampToValueAtTime(0.001, start + 0.4);
      osc.start(start);
      osc.stop(start + 0.45);
    });
  } catch { /* 浏览器不支持则静默 */ }
}

// ── 番茄钟 ──
const POMODORO_SECONDS = 25 * 60;
let pomodoroLeft = POMODORO_SECONDS;
let pomodoroTimer = null;

function renderPomodoro() {
  const m = String(Math.floor(pomodoroLeft / 60)).padStart(2, "0");
  const s = String(pomodoroLeft % 60).padStart(2, "0");
  document.getElementById("pomodoro-time").textContent = `${m}:${s}`;
}

document.getElementById("pomodoro-start").addEventListener("click", () => {
  const btn = document.getElementById("pomodoro-start");
  if (pomodoroTimer) {
    clearInterval(pomodoroTimer);
    pomodoroTimer = null;
    btn.textContent = "▶ 继续";
    document.getElementById("pomodoro-status").textContent = "已暂停";
    return;
  }
  btn.textContent = "⏸ 暂停";
  document.getElementById("pomodoro-status").textContent = "专注中…";
  pomodoroTimer = setInterval(() => {
    pomodoroLeft -= 1;
    if (pomodoroLeft <= 0) {
      clearInterval(pomodoroTimer);
      pomodoroTimer = null;
      pomodoroLeft = POMODORO_SECONDS;
      btn.textContent = "▶ 开始";
      document.getElementById("pomodoro-status").textContent = "🍅 完成！休息一下吧";
      playChime();
      return;
    }
    renderPomodoro();
  }, 1000);
});

document.getElementById("pomodoro-reset").addEventListener("click", () => {
  if (pomodoroTimer) {
    clearInterval(pomodoroTimer);
    pomodoroTimer = null;
  }
  pomodoroLeft = POMODORO_SECONDS;
  document.getElementById("pomodoro-start").textContent = "▶ 开始";
  document.getElementById("pomodoro-status").textContent = "";
  renderPomodoro();
});

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
    // 编辑表单回填
    document.getElementById("ielts-target").value = i.target_score;
    document.getElementById("ielts-band").value = i.current_band;
    document.getElementById("ielts-stage").value = i.stage;
    document.getElementById("ielts-exam-date").value = i.exam_date || "";
    for (const [name, band] of Object.entries(i.skills)) {
      document.getElementById(`ielts-${name}`).value = band || "";
    }
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

// 看板保存
document.getElementById("ielts-save-btn").addEventListener("click", async () => {
  const statusEl = document.getElementById("ielts-save-status");
  const val = (id) => {
    const v = document.getElementById(id).value.trim();
    return v === "" ? null : v;
  };
  const skills = {};
  for (const name of ["听力", "阅读", "写作", "口语"]) {
    const v = val(`ielts-${name}`);
    if (v !== null) skills[name] = v;
  }
  try {
    const body = {
      target_score: val("ielts-target") === null ? null : parseFloat(val("ielts-target")),
      current_band: val("ielts-band"),
      stage: val("ielts-stage"),
      exam_date: val("ielts-exam-date"),
      skills,
    };
    await api("/api/ielts", { method: "PATCH", body: JSON.stringify(body) });
    statusEl.textContent = "✅ 已保存";
    toast("🎯 雅思看板已保存");
    loadIeltsBoard();
    loadHomeCards();
  } catch {
    statusEl.textContent = "❌ 保存失败";
  }
});

// 生词状态：搜索词 + 筛选
let vocabSearch = "";
let vocabFilter = "all";

async function loadVocab() {
  const listEl = document.getElementById("vocab-list");
  try {
    const words = await api("/api/vocab");
    // 统计
    const total = words.length;
    const graduated = words.filter((w) => w.stage >= 5).length;
    document.getElementById("vocab-stats").textContent =
      `共 ${total} · 复习中 ${total - graduated} · 已毕业 ${graduated}`;
    // 搜索 + 筛选
    const q = vocabSearch.toLowerCase();
    const filtered = words.filter((w) => {
      if (vocabFilter === "active" && w.stage >= 5) return false;
      if (vocabFilter === "done" && w.stage < 5) return false;
      if (q && !(w.word.toLowerCase().includes(q) || w.meaning.toLowerCase().includes(q))) return false;
      return true;
    });
    listEl.innerHTML = filtered.length
      ? filtered.map((w) => vocabItemHtml(w)).join("")
      : '<li class="vocab-empty">没有匹配的生词</li>';
  } catch {
    listEl.innerHTML = '<li class="vocab-empty">加载失败</li>';
  }
}

// 搜索输入
document.getElementById("vocab-search").addEventListener("input", (e) => {
  vocabSearch = e.target.value;
  loadVocab();
});

// 筛选按钮
document.querySelectorAll(".vocab-filter").forEach((btn) => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".vocab-filter").forEach((b) => b.classList.remove("active"));
    btn.classList.add("active");
    vocabFilter = btn.dataset.filter;
    loadVocab();
  });
});

async function loadVocabDue() {
  const listEl = document.getElementById("vocab-due-list");
  try {
    const due = await api("/api/vocab/due");
    document.getElementById("vocab-due-count").textContent = due.length ? `(${due.length})` : "";
    listEl.innerHTML = due.length
      ? due.map((w) => `
        <li class="flip-card" data-flip="${w.id}">
          <div class="flip-inner">
            <div class="flip-face">
              <span class="vocab-word">${escapeHtml(w.word)}</span>
              <span class="muted-line" style="font-size:11px">点击看释义</span>
            </div>
            <div class="flip-face flip-back">
              <span>${escapeHtml(w.meaning)}</span>
            </div>
          </div>
          <div style="display:flex;gap:6px;margin-top:6px">
            <button class="btn-small" data-review="${w.id}" data-known="true" title="认识，推进下一轮">✓ 认识</button>
            <button class="btn-small ghost" data-review="${w.id}" data-known="false" title="不认识，重新开始">↺ 不认识</button>
          </div>
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
  toast("📖 生词已添加");
});

// 复习打卡 / 删除（事件委托）
document.getElementById("vocab-due-list").addEventListener("click", async (e) => {
  // 翻转卡片：点卡片看释义
  const flip = e.target.closest("[data-flip]");
  if (flip && !e.target.closest("button")) {
    flip.classList.toggle("flipped");
    return;
  }
  const btn = e.target.closest("[data-review]");
  if (!btn) return;
  try {
    await api(`/api/vocab/${btn.dataset.review}/review`, {
      method: "POST",
      body: JSON.stringify({ known: btn.dataset.known === "true" }),
    });
  } catch { /* 同上 */ }
  toast(btn.dataset.known === "true" ? "✓ 记住了，推进一轮" : "↺ 已重置，重新复习");
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

// AI 挑今日最佳灵感
async function loadBestIdea() {
  const el = document.getElementById("ideas-best");
  try {
    const best = await api("/api/ideas/best");
    if (!best) {
      el.innerHTML = "";
      return;
    }
    el.innerHTML = `<div class="guide-nav-text">⭐ 今日推荐：${escapeHtml(best.text)}<br><span class="muted-line">理由：${escapeHtml(best.reason)}</span></div>`;
  } catch {
    el.innerHTML = "";
  }
}

// ── 灵感页 ──
async function loadIdeasPage() {
  loadBestIdea();
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
        <span class="vocab-meaning" style="flex:1">${escapeHtml(i.text)}${i.note ? `<div class="muted-line">📝 ${escapeHtml(i.note)}</div>` : ""}</span>
        <span class="vocab-stage">${i.source === "ai" ? "🤖 AI" : "✍️ 手动"}</span>
        <button class="btn-small ghost" data-idea-note="${i.id}" title="写备注">📝</button>
        ${action}
      </li>`;
    }).join("")
    : '<li class="vocab-empty">今日还没有灵感</li>';
}

function renderIdeasAll(all) {
  const listEl = document.getElementById("ideas-all-list");
  const src = document.getElementById("ideas-filter-source").value;
  const st = document.getElementById("ideas-filter-status").value;
  const filtered = all.filter((i) =>
    (src === "all" || i.source === src) && (st === "all" || i.status === st));
  listEl.innerHTML = filtered.length
    ? filtered.slice(0, 30).map((i) => `
      <li class="vocab-item">
        <span class="vocab-word" style="min-width:80px">${escapeHtml(i.date)}</span>
        <span class="vocab-meaning" style="flex:1">${escapeHtml(i.text)}${i.note ? `<div class="muted-line">📝 ${escapeHtml(i.note)}</div>` : ""}</span>
        <span class="vocab-stage">${i.status === "kept" ? "🔖 收藏" : i.status === "done" ? "✅ 已采用" : "🗑 已丢弃"}</span>
      </li>`).join("")
    : '<li class="vocab-empty">没有匹配的灵感</li>';
}

// 历史筛选
document.getElementById("ideas-filter-source").addEventListener("change", async () => {
  const all = await api("/api/ideas");
  renderIdeasAll(all);
});
document.getElementById("ideas-filter-status").addEventListener("change", async () => {
  const all = await api("/api/ideas");
  renderIdeasAll(all);
});

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
  const noteBtn = e.target.closest("[data-idea-note]");
  if (noteBtn) {
    const current = noteBtn.closest(".vocab-item")?.querySelector(".muted-line")?.textContent?.replace(/^📝 /, "") || "";
    const note = prompt("给这个灵感写备注/细化思路（可留空清除）：", current);
    if (note === null) return;
    try {
      await api(`/api/ideas/${noteBtn.dataset.ideaNote}`, { method: "PATCH", body: JSON.stringify({ note }) });
    } catch { /* 兜底 */ }
    loadIdeasPage();
    loadHomeCards();
    return;
  }
  if (!discard && !keep && !adopt) return;
  const el = discard || keep || adopt;
  const id = el.dataset.ideaDiscard || el.dataset.ideaKeep || el.dataset.ideaAdopt;
  const status = discard ? "discarded" : adopt ? "done" : "kept";
  const itemEl = el.closest(".vocab-item") || el.closest(".flip-card") || el.closest("li");
  if (itemEl) itemEl.classList.add("idea-leave");  // 先播放滑出动画
  await new Promise((r) => setTimeout(r, 240));
  try {
    await api(`/api/ideas/${id}`, { method: "PATCH", body: JSON.stringify({ status }) });
  } catch { /* 兜底 */ }
  loadIdeasPage();
  loadHomeCards();
  toast(status === "done" ? "⭐ 已采用，去做出内容吧" : status === "discarded" ? "🗑 已丢弃" : "🔖 已捡回");
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
      <div class="muted-line" style="margin:12px 0 6px">已采用的点子（点击 ✍️ 记录产出）：</div>
      ${adopted.length ? adopted.slice(0, 10).map((i) =>
        `<div class="home-idea">✅ ${escapeHtml(i.text)} <span class="muted-line">(${i.date})</span>
          ${i.outcome ? `<div class="muted-line">📎 ${escapeHtml(i.outcome)}</div>` : ""}
          <button class="btn-small ghost" data-outcome="${i.id}" style="margin-top:4px">✍️ 填产出</button>
        </div>`).join("")
        : '<div class="placeholder">还没有采用任何灵感，去灵感页把点子变成现实 🚀</div>'}`;
    // 产出按钮事件
    el.querySelectorAll("[data-outcome]").forEach((btn) => {
      btn.addEventListener("click", async () => {
        const item = adopted.find((a) => a.id === btn.dataset.outcome);
        const current = item?.outcome || "";
        const outcome = prompt("记录产出（如：链接 | 效果数据）：", current);
        if (outcome === null) return;
        try {
          await api(`/api/ideas/${btn.dataset.outcome}`, { method: "PATCH", body: JSON.stringify({ outcome }) });
        } catch { /* 兜底 */ }
        loadContentReview();
      });
    });
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
    toast("📝 总结已保存");
  } catch {
    document.getElementById("review-date-label").textContent = "（保存失败）";
  }
});

// 同步到 Obsidian 日记
document.getElementById("review-obsidian-btn").addEventListener("click", async () => {
  const date = document.getElementById("review-date-picker").value || new Date().toISOString().slice(0, 10);
  const summary = document.getElementById("review-summary").value;
  const statusEl = document.getElementById("review-obsidian-status");
  if (!summary.trim()) {
    statusEl.textContent = "❌ 总结是空的，先写或先保存";
    return;
  }
  try {
    const r = await api("/api/reviews/sync-obsidian", {
      method: "POST",
      body: JSON.stringify({ date, summary }),
    });
    statusEl.textContent = `✅ 已写入 ${date}.md（Obsidian 里刷新即可看到）`;
    toast("📓 已同步到 Obsidian 日记");
  } catch {
    statusEl.textContent = "❌ 同步失败";
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

// ── 统计页 ──
function setRing(el, pct) {
  el.style.setProperty("--pct", Math.max(0, Math.min(100, pct)));
  el.querySelector("span").textContent = `${Math.round(pct)}${el.dataset.unit || "%"}`;
}

async function loadStatsPage() {
  try {
    const s = await api("/api/stats");
    // 连续天数（单位：天）
    const streakEl = document.getElementById("stat-streak");
    streakEl.dataset.unit = " 天";
    streakEl.style.setProperty("--pct", Math.min(100, s.streak_days * 10));
    countUp(streakEl, s.streak_days, " 天");

    // 本周完成率
    setRing(document.getElementById("stat-week"), s.week.rate * 100);
    document.getElementById("stat-week-detail").textContent =
      `已完成 ${s.week.done}/${s.week.total} 项`;

    // 生词本
    const v = s.vocab;
    document.getElementById("stat-vocab").innerHTML = `
      <div class="muted-line">共 ${v.total} 个 · 复习中 ${v.active} · 已毕业 ${v.graduated} · 今日新增 ${v.added_today}</div>
      <div class="skill-bar" style="margin-top:8px"><i style="width:${v.total ? Math.round(v.graduated / v.total * 100) : 0}%"></i></div>
      <div class="muted-line" style="margin-top:6px">毕业率 ${v.total ? Math.round(v.graduated / v.total * 100) : 0}%</div>`;

    // 灵感采用率
    setRing(document.getElementById("stat-ideas"), s.ideas.adopt_rate * 100);
    document.getElementById("stat-ideas-detail").textContent =
      `已采用 ${s.ideas.done}/${s.ideas.total} · 收藏 ${s.ideas.kept} · 丢弃 ${s.ideas.discarded}`;

    // 近 7 天完成趋势（SVG 折线）
    renderDailyChart(s.daily || []);
  } catch {
    document.querySelectorAll("#page-stats .card-body, #page-stats .stat-ring").forEach((el) => {
      el.textContent = "加载失败";
    });
  }
}

// SVG 折线图
function renderDailyChart(daily) {
  const svg = document.getElementById("stat-chart");
  const labelsEl = document.getElementById("stat-chart-labels");
  const W = 300, H = 80, PAD = 6;
  const max = Math.max(1, ...daily.map((d) => d.done));
  const pts = daily.map((d, i) => {
    const x = PAD + (i * (W - PAD * 2)) / (daily.length - 1 || 1);
    const y = H - PAD - (d.done / max) * (H - PAD * 2);
    return [x, y];
  });
  const line = pts.map((p, i) => `${i ? "L" : "M"}${p[0].toFixed(1)},${p[1].toFixed(1)}`).join(" ");
  const area = `${line} L${W - PAD},${H - PAD} L${PAD},${H - PAD} Z`;
  svg.innerHTML = `
    <defs>
      <linearGradient id="chartGrad" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0%" stop-color="#c9a35f" stop-opacity="0.35"/>
        <stop offset="100%" stop-color="#c9a35f" stop-opacity="0.02"/>
      </linearGradient>
    </defs>
    <path d="${area}" fill="url(#chartGrad)"/>
    <path d="${line}" fill="none" stroke="#c9a35f" stroke-width="2" stroke-linecap="round"
          stroke-dasharray="600" stroke-dashoffset="600">
      <animate attributeName="stroke-dashoffset" from="600" to="0" dur="0.9s" fill="freeze"/>
    </path>
    ${pts.map(([x, y]) => `<circle cx="${x}" cy="${y}" r="2.6" fill="#b8894a"/>`).join("")}
  `;
  labelsEl.innerHTML = daily.map((d) => `<span>${d.date}</span>`).join("");
}

// ── 新闻简讯 ──
let newsTab = "ai";

async function loadNews(refresh = false) {
  const listEl = document.getElementById("news-list");
  listEl.innerHTML = '<li class="news-item" style="justify-content:center;color:var(--muted)">加载中…</li>';
  try {
    const data = await api(`/api/news?tab=${newsTab}${refresh ? "&refresh=1" : ""}`);
    renderNews(data);
  } catch {
    listEl.innerHTML = '<li class="news-item" style="justify-content:center;color:var(--muted)">⚠️ 新闻加载失败</li>';
  }
  loadNewsHealth();
}

// 资讯源健康状态：每个源一个小圆点（绿=正常，红=失败）
async function loadNewsHealth() {
  const el = document.getElementById("news-health");
  if (!el) return;
  try {
    const health = await api("/api/news/health");
    const names = {
      "ai": ["aihot"],
      "domestic": ["百度热搜", "今日头条", "IT之家"],
      "global": ["BBC中文", "Hacker News", "TechCrunch"],
    }[newsTab] || [];
    el.innerHTML = names
      .map((n) => {
        const h = health[n];
        const cls = h ? (h.ok ? "health-ok" : "health-bad") : "health-unknown";
        const title = h ? `${n}：${h.ok ? "正常" : `失败 ${h.fails} 次 · ${h.last_at}`}` : `${n}：未检测`;
        return `<span class="health-dot ${cls}" title="${title}">${escapeHtml(n)}</span>`;
      })
      .join("");
  } catch {
    el.innerHTML = "";
  }
}

function renderNews(data) {
  const listEl = document.getElementById("news-list");
  listEl.innerHTML = `
    <li class="news-meta">
      <span class="news-updated">🕐 更新于 ${escapeHtml(data.fetched_at || "—")}</span>
      <button class="btn-small ghost news-refresh" title="手动刷新">🔄 刷新</button>
    </li>`;
  if (!data.items.length) {
    listEl.innerHTML += '<li class="news-item" style="justify-content:center;color:var(--muted)">暂无新闻</li>';
    return;
  }
  listEl.innerHTML += data.items
    .map((n) => `
      <li class="news-item">
        <a href="${escapeHtml(n.url)}" target="_blank" rel="noopener">${escapeHtml(n.title)}</a>
        <span class="news-src">${escapeHtml(n.source)}</span>
        <span class="news-time">${escapeHtml(n.time)}</span>
      </li>`)
    .join("");
  // 刷新按钮（innerHTML 重建后重新绑定）
  listEl.querySelector(".news-refresh").addEventListener("click", () => loadNews(true));
}

document.getElementById("news-tabs").addEventListener("click", (e) => {
  const btn = e.target.closest("[data-news-tab]");
  if (!btn) return;
  newsTab = btn.dataset.newsTab;
  document.querySelectorAll(".news-tab").forEach((b) => b.classList.toggle("active", b === btn));
  loadNews();
});

// ── 基金涨跌 ──
async function loadFunds() {
  const body = document.getElementById("funds-body");
  body.innerHTML = "加载中…";
  try {
    const data = await api("/api/funds");
    renderFunds(data);
  } catch {
    body.innerHTML = "⚠️ 基金数据加载失败";
  }
}

function renderFunds(data) {
  const body = document.getElementById("funds-body");
  document.getElementById("funds-updated").textContent = `更新 ${data.ts}`;
  if (!data.funds.length) {
    body.innerHTML = "暂无关注基金，去工具页添加";
    return;
  }
  body.innerHTML = data.funds
    .map((f) => {
      const cls = f.change_pct > 0 ? "funds-up" : f.change_pct < 0 ? "funds-down" : "";
      const arrow = f.change_pct > 0 ? "▲" : f.change_pct < 0 ? "▼" : "—";
      return `
      <div class="funds-row" data-fund="${f.code}" title="点击查看走势">
        <span class="funds-name">${escapeHtml(f.name)}</span>
        <span class="funds-value">${f.latest.toFixed(4)}</span>
        <span class="funds-change ${cls}">${arrow} ${f.change_pct > 0 ? "+" : ""}${f.change_pct.toFixed(2)}%</span>
      </div>`;
    })
    .join("");
}

// 点击基金展开 30 天走势
document.getElementById("funds-body").addEventListener("click", async (e) => {
  const row = e.target.closest("[data-fund]");
  if (!row) return;
  const code = row.dataset.fund;
  const next = row.nextElementSibling;
  if (next && next.classList.contains("funds-chart-box")) {
    next.remove();
    return;
  }
  const box = document.createElement("div");
  box.className = "funds-chart-box";
  box.innerHTML = "走势加载中…";
  row.after(box);
  try {
    const hist = await api(`/api/funds/history?code=${code}`);
    box.innerHTML = "";
    box.appendChild(chartSvg(hist.points, hist.name));
  } catch {
    box.innerHTML = "走势加载失败";
  }
});

// 折线图（基金走势通用）：红涨绿跌
function chartSvg(points) {
  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  svg.setAttribute("viewBox", "0 0 300 90");
  svg.setAttribute("preserveAspectRatio", "none");
  const W = 300, H = 90, PAD = 6;
  const vals = points.map((p) => p.value);
  const min = Math.min(...vals), max = Math.max(...vals);
  const span = max - min || 1;
  const pts = points.map((p, i) => {
    const x = PAD + (i * (W - PAD * 2)) / (points.length - 1 || 1);
    const y = H - PAD - ((p.value - min) / span) * (H - PAD * 2);
    return [x, y];
  });
  const line = pts.map((p, i) => `${i ? "L" : "M"}${p[0].toFixed(1)},${p[1].toFixed(1)}`).join(" ");
  const up = vals[vals.length - 1] >= vals[0];
  const color = up ? "#c0392b" : "#1e8449";  // 红涨绿跌
  const area = `${line} L${W - PAD},${H - PAD} L${PAD},${H - PAD} Z`;
  svg.innerHTML = `
    <defs>
      <linearGradient id="fgGrad" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0%" stop-color="${color}" stop-opacity="0.3"/>
        <stop offset="100%" stop-color="${color}" stop-opacity="0.02"/>
      </linearGradient>
    </defs>
    <path d="${area}" fill="url(#fgGrad)"/>
    <path d="${line}" fill="none" stroke="${color}" stroke-width="1.8" stroke-linecap="round"/>
    <circle cx="${pts[pts.length - 1][0]}" cy="${pts[pts.length - 1][1]}" r="2.5" fill="${color}"/>
  `;
  return svg;
}

// ── 工具页 ──
async function loadToolsPage() {
  loadLinksManager();
  loadDouyinHistory();
  try {
    const cfg = await api("/api/config");
    document.getElementById("set-nickname").value = cfg.nickname;
    document.getElementById("set-city").value = cfg.city;
    document.getElementById("set-lat").value = cfg.lat;
    document.getElementById("set-lon").value = cfg.lon;
    document.getElementById("set-language").value = cfg.language || "zh";
    document.getElementById("set-status").textContent = `当前：${cfg.city}（${cfg.lat}, ${cfg.lon}）`;
  } catch { /* 表单保持空 */ }
}

// 语言切换：保存后刷新页面（让所有文案按新语言重新渲染）
document.getElementById("set-language").addEventListener("change", async (e) => {
  const lang = e.target.value;
  try {
    await api("/api/config/language", { method: "PATCH", body: JSON.stringify({ language: lang }) });
    LANG = lang;
    applyI18n();
    toast(lang === "en" ? "🌐 Language switched to English" : "🌐 已切换为中文");
    setTimeout(() => location.reload(), 900);
  } catch {
    toast("❌ 切换失败");
  }
});

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
    toast(added ? `⚡ 已添加 ${added} 项雅思任务` : "这些任务今天已经有了");
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

// 抖音历史任务列表
async function loadDouyinHistory() {
  const el = document.getElementById("douyin-history");
  try {
    const jobs = await api("/api/tools/douyin/history");
    el.innerHTML = jobs.length
      ? jobs.slice(0, 10).map((j) => {
        const label = j.status === "done"
          ? `✅ ${j.result?.metadata?.["标题"]?.slice(0, 20) || "完成"}`
          : j.status === "error" ? `❌ ${j.error?.slice(0, 30) || "失败"}` : "⏳ " + j.status;
        return `<li class="vocab-item"><span class="vocab-word" style="min-width:70px">${j.job_id}</span><span class="vocab-meaning" style="flex:1">${escapeHtml(label)}</span></li>`;
      }).join("")
      : '<li class="vocab-empty">还没有任务记录</li>';
  } catch {
    el.innerHTML = '<li class="vocab-empty">加载失败</li>';
  }
}

// ── 快捷键：N 快速加计划，G 回首页，S 学习页 ──
document.addEventListener("keydown", (e) => {
  if (e.target.matches("input, textarea, select")) return;  // 输入时不触发
  if (e.key === "n" || e.key === "N") {
    location.hash = "#/home";
    setTimeout(() => document.getElementById("plan-input")?.focus(), 100);
  } else if (e.key === "g" || e.key === "G") {
    location.hash = "#/home";
  } else if (e.key === "s" || e.key === "S") {
    location.hash = "#/study";
  }
});

// ── 基金管理（工具页） ──
async function loadFundManager() {
  const el = document.getElementById("set-fund-list");
  try {
    const data = await api("/api/funds");
    el.innerHTML = data.funds
      .map((f) => `
        <div class="vocab-item" style="margin-top:4px">
          <span class="vocab-word" style="min-width:70px">${f.code}</span>
          <span class="vocab-meaning" style="flex:1">${escapeHtml(f.name)}</span>
          <button class="plan-del" data-fund-del="${f.code}" title="取消关注">✕</button>
        </div>`)
      .join("") || '<div class="muted-line">还没有关注基金</div>';
  } catch {
    el.innerHTML = '<div class="muted-line">加载失败</div>';
  }
}

document.getElementById("set-fund-add-btn").addEventListener("click", async () => {
  const input = document.getElementById("set-fund");
  const code = input.value.trim();
  if (!/^\d{6}$/.test(code)) {
    toast("请输入 6 位基金代码");
    return;
  }
  input.value = "";
  try {
    const r = await api("/api/funds", { method: "POST", body: JSON.stringify({ code }) });
    toast(r.duplicate ? `已关注过 ${code}` : `✅ 已添加 ${r.name || code}`);
  } catch {
    toast("❌ 代码无效或无法获取");
  }
  loadFundManager();
  loadFunds();
});

document.getElementById("set-fund-list").addEventListener("click", async (e) => {
  const btn = e.target.closest("[data-fund-del]");
  if (!btn) return;
  try {
    await api(`/api/funds/${btn.dataset.fundDel}`, { method: "DELETE" });
  } catch { /* 兜底 */ }
  loadFundManager();
  loadFunds();
});

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
initLanguage();
navigate();

// ── Spotlight 光晕：鼠标位置 → CSS 变量 ──
document.addEventListener("mousemove", (e) => {
  const card = e.target.closest(".card");
  if (!card) return;
  const rect = card.getBoundingClientRect();
  card.style.setProperty("--mx", `${e.clientX - rect.left}px`);
  card.style.setProperty("--my", `${e.clientY - rect.top}px`);
});

// ── 夜间模式（localStorage 持久化） ──
const themeBtn = document.getElementById("theme-toggle");
function applyTheme(dark) {
  document.body.classList.toggle("dark", dark);
  themeBtn.textContent = dark ? "☀️" : "🌙";
  localStorage.setItem("workbench-dark", dark ? "1" : "0");
}
// 初始化：读取偏好（默认跟随系统）
(function initTheme() {
  const saved = localStorage.getItem("workbench-dark");
  if (saved === null) {
    applyTheme(window.matchMedia("(prefers-color-scheme: dark)").matches);
  } else {
    applyTheme(saved === "1");
  }
})();
themeBtn.addEventListener("click", () => {
  applyTheme(!document.body.classList.contains("dark"));
});

// ── 顶部加载进度条 ──
const progressBar = document.getElementById("progress-bar");
function startProgress() {
  progressBar.classList.remove("done");
  progressBar.classList.add("loading");
}
function finishProgress() {
  progressBar.classList.add("done");
  setTimeout(() => {
    progressBar.classList.remove("loading", "done");
    progressBar.style.opacity = "";
  }, 900);
}
// 每次导航触发一次进度条
window.addEventListener("hashchange", () => {
  startProgress();
  setTimeout(finishProgress, 500);
});
startProgress();
setTimeout(finishProgress, 600);

// ── Toast 通知横幅 ──
function toast(text, ms = 2200) {
  const wrap = document.getElementById("toast-wrap");
  const el = document.createElement("div");
  el.className = "toast";
  el.textContent = text;
  wrap.appendChild(el);
  setTimeout(() => {
    el.classList.add("out");
    setTimeout(() => el.remove(), 350);
  }, ms);
}

// ── Ripple 波纹（全局委托） ──
document.addEventListener("click", (e) => {
  const btn = e.target.closest(".btn-small");
  if (!btn) return;
  const rect = btn.getBoundingClientRect();
  const d = Math.max(rect.width, rect.height);
  const ink = document.createElement("span");
  ink.className = "ripple-ink";
  ink.style.width = ink.style.height = `${d}px`;
  ink.style.left = `${e.clientX - rect.left - d / 2}px`;
  ink.style.top = `${e.clientY - rect.top - d / 2}px`;
  btn.appendChild(ink);
  setTimeout(() => ink.remove(), 600);
});

// ── 数字 count-up（统计页） ──
function countUp(el, target, unit = "", dur = 900) {
  const start = performance.now();
  const from = 0;
  function frame(now) {
    const p = Math.min(1, (now - start) / dur);
    const eased = 1 - Math.pow(1 - p, 3);
    el.querySelector("span").textContent = `${Math.round(from + (target - from) * eased)}${unit}`;
    if (p < 1) requestAnimationFrame(frame);
  }
  requestAnimationFrame(frame);
}

// ── AI 导航打字机效果 ──
function typewriter(el, text, speed = 22) {
  el.classList.add("typing");
  let i = 0;
  const full = text;
  el.textContent = "";
  function step() {
    i += 1;
    el.textContent = full.slice(0, i);
    if (i < full.length) {
      setTimeout(step, speed);
    } else {
      el.classList.remove("typing");
    }
  }
  step();
}

// ── 移动端汉堡抽屉 ──
const sidebarEl = document.getElementById("sidebar");
const overlayEl = document.getElementById("sidebar-overlay");
const hamburgerEl = document.getElementById("hamburger");

function closeSidebar() {
  sidebarEl.classList.remove("open");
  overlayEl.classList.remove("show");
}

hamburgerEl.addEventListener("click", () => {
  const open = sidebarEl.classList.toggle("open");
  overlayEl.classList.toggle("show", open);
});
overlayEl.addEventListener("click", closeSidebar);
// 切页后自动收起抽屉
document.querySelectorAll(".nav-item").forEach((item) => {
  item.addEventListener("click", closeSidebar);
});
