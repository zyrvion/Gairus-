/* Isolated worker contract tests. Browser QA separately checks the real worker. */
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

(async () => {
  const origin = "https://gairus.example";
  const listeners = new Map();
  const saved = new Map();
  const stores = new Set(["gairus-v1", "gairus-public-old", "unrelated-cache"]);
  let skipped = 0;
  let claimed = 0;
  let failNetwork = false;
  const cache = {
    async addAll(requests) {
      for (const request of requests) {
        assert.equal(request.credentials, "omit");
        assert.equal(request.cache, "reload");
        saved.set(new URL(request.url).pathname, new Response("public-only"));
      }
    },
    async match(request) {
      return saved.get(typeof request === "string" ? request : new URL(request.url).pathname)?.clone();
    }
  };
  const caches = {
    async open(name) { stores.add(name); return cache; },
    async keys() { return [...stores]; },
    async delete(name) { return stores.delete(name); },
    async match(request) { return cache.match(request); }
  };
  const self = {
    location:{origin},
    clients:{async claim() { claimed++; }},
    addEventListener(name, handler) { listeners.set(name, handler); },
    skipWaiting() { skipped++; }
  };
  class WorkerRequest {
    constructor(url, options) {
      this.url = new URL(url, origin).href;
      Object.assign(this, options);
    }
  }
  vm.runInNewContext(fs.readFileSync(path.join(__dirname, "../static/sw.js"), "utf8"), {
    self, caches, URL, Request:WorkerRequest,
    fetch:async () => {
      if (failNetwork) throw new Error("offline");
      return new Response("live-root");
    }
  });
  let pending;
  listeners.get("install")({waitUntil(value) { pending = value; }});
  await pending;
  assert.equal(skipped, 0, "install must not replace a worker automatically");
  assert.deepEqual([...saved.keys()].sort(), [
    "/icon-180.png", "/icon-192.png", "/icon-512.png",
    "/offline.html", "/static/css/offline.css"
  ]);
  assert(!saved.has("/"), "never cache a loaded shell");
  assert(!saved.has("/api/memory"), "never cache private data");
  listeners.get("activate")({waitUntil(value) { pending = value; }});
  await pending;
  assert.equal(claimed, 1);
  assert(stores.has("unrelated-cache"));
  assert(!stores.has("gairus-v1"));
  assert(!stores.has("gairus-public-old"));

  function fetchEvent(url, options={}) {
    let intercepted = false;
    let promise;
    const event = {
      request:{
        url:new URL(url, origin).href,
        method:options.method || "GET",
        mode:options.mode || "cors",
        headers:new Headers(options.headers || {})
      },
      respondWith(value) { intercepted = true; promise = value; }
    };
    listeners.get("fetch")(event);
    return {intercepted, promise};
  }
  for (const [url, options] of [
    ["/api/memory", {}],
    ["/api/missions", {mode:"navigate"}],
    ["/api/missions", {method:"POST"}],
    ["/offline.html", {method:"POST"}],
    ["/offline.html", {headers:{Authorization:"Bearer PRIVATE"}}],
    ["/private-download.wav", {}],
    ["/?secret=PRIVATE", {mode:"navigate"}],
    ["/offline.html?key=PRIVATE", {}],
    ["https://unrelated.example/offline.html", {}]
  ]) assert.equal(fetchEvent(url, options).intercepted, false, url);

  const onlineRoot = fetchEvent("/", {mode:"navigate"});
  assert.equal(await (await onlineRoot.promise).text(), "live-root");
  assert(!saved.has("/"));
  failNetwork = true;
  const offlineRoot = fetchEvent("/", {mode:"navigate"});
  assert.equal(await (await offlineRoot.promise).text(), "public-only");
  assert.equal(await (await fetchEvent("/offline.html").promise).text(), "public-only");
  listeners.get("message")({data:{type:"untrusted"}});
  assert.equal(skipped, 0);
  listeners.get("message")({data:{type:"GAIRUS_ACTIVATE_UPDATE"}});
  assert.equal(skipped, 1);
  console.log("PWA worker checks passed: privacy, offline, scoped cleanup, explicit update");
})().catch(error => { console.error(error); process.exitCode = 1; });
