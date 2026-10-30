/* Increment this version for each release. Only exact public assets are cached. */
const CACHE = "gairus-public-20261030-1";
const PUBLIC_ASSETS = [
  "/offline.html",
  "/static/css/offline.css",
  "/icon-180.png",
  "/icon-192.png",
  "/icon-512.png"
];

self.addEventListener("install", event => {
  event.waitUntil(
    caches.open(CACHE).then(cache => cache.addAll(
      PUBLIC_ASSETS.map(path => new Request(path, {cache:"reload", credentials:"omit"}))
    ))
  );
  // No skipWaiting here: an update must never discard a draft automatically.
});

self.addEventListener("activate", event => {
  event.waitUntil((async () => {
    const keys = await caches.keys();
    await Promise.all(keys.filter(key =>
      key !== CACHE && (key === "gairus-v1" || key.startsWith("gairus-public-"))
    ).map(key => caches.delete(key)));
    await self.clients.claim();
  })());
});

self.addEventListener("message", event => {
  if (event.data?.type === "GAIRUS_ACTIVATE_UPDATE") self.skipWaiting();
});

self.addEventListener("fetch", event => {
  const request = event.request;
  const url = new URL(request.url);
  // No authenticated request, API, mutation, file, or third-party cache.
  if (request.method !== "GET" || url.origin !== self.location.origin ||
      request.headers.has("Authorization") || url.search) return;

  if (request.mode === "navigate" && url.pathname === "/") {
    event.respondWith(fetch(request).catch(() => caches.match("/offline.html")));
    return;
  }
  if (!PUBLIC_ASSETS.includes(url.pathname)) return;

  event.respondWith((async () => {
    const cache = await caches.open(CACHE);
    return (await cache.match(request)) || fetch(request);
  })());
});
