/* 个人工作台 Service Worker：静态资源缓存（离线可用）。

策略：
- install：预缓存页面骨架
- fetch：静态资源缓存优先 + 回源更新；/api/* 一律不拦截（保证数据新鲜）
注意：SW 仅在安全上下文生效（localhost / HTTPS），局域网 IP 需要部署 HTTPS。
*/
const CACHE = "workbench-v2";
const ASSETS = ["/", "/style.css", "/app.js", "/icon.svg", "/manifest.webmanifest"];

self.addEventListener("install", (e) => {
  e.waitUntil(
    caches.open(CACHE).then((c) => c.addAll(ASSETS)).then(() => self.skipWaiting())
  );
});

self.addEventListener("activate", (e) => {
  e.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (e) => {
  const url = new URL(e.request.url);
  if (url.pathname.startsWith("/api/")) return;  // API 不缓存
  e.respondWith(
    caches.match(e.request).then((hit) => hit || fetch(e.request).then((resp) => {
      const copy = resp.clone();
      caches.open(CACHE).then((c) => c.put(e.request, copy));
      return resp;
    }))
  );
});
