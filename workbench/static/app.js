/* ═══════════════════════════════════════
   个人工作台前端逻辑
   hash 路由 · 时钟 · 天气 · 今日计划
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
}

// ── 首页：各卡片并行加载，互不拖累 ──
function loadHome() {
  loadGreeting();
  loadClock();
  loadPlan();
  loadWeather();
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

// ── 启动 ──
window.addEventListener("hashchange", navigate);
navigate();
