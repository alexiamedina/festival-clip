// Keeps copies of the app and the AI library on the phone, so the app
// still opens at a festival with no signal.
// - App files: try the internet first (so updates show up), else the copy.
// - The AI library from cdn.jsdelivr.net: use the copy if we have one.
// (The AI model itself is saved by the AI library in its own storage.)
const CACHE = "raveclip-v1";

self.addEventListener("install", () => self.skipWaiting());
self.addEventListener("activate", (e) => e.waitUntil(self.clients.claim()));

self.addEventListener("fetch", (e) => {
  const req = e.request;
  if (req.method !== "GET") return;
  const url = new URL(req.url);
  if (url.origin === location.origin) {
    e.respondWith(
      fetch(req).then((res) => {
        const copy = res.clone();
        caches.open(CACHE).then((c) => c.put(req, copy));
        return res;
      }).catch(() => caches.match(req))
    );
  } else if (url.hostname === "cdn.jsdelivr.net") {
    e.respondWith(
      caches.match(req).then((hit) => hit || fetch(req).then((res) => {
        const copy = res.clone();
        caches.open(CACHE).then((c) => c.put(req, copy));
        return res;
      }))
    );
  }
});
