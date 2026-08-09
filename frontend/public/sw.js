/*
 * Student Life OS — service worker (adapted from Shiori-v1/client/public/sw.js)
 *
 * Strategy:
 *  - STATIC: cache-first for same-origin JS/CSS/fonts/images (hashed, immutable).
 *  - API:    network-first, falling back to the last cached response when
 *            offline, so the dashboard keeps working on a flaky connection.
 *  - NAV:    network-first for navigations with an offline shell fallback to
 *            the cached index.html.
 *
 * Version the cache name; on activate, old caches are purged.
 */
const VERSION = 'v1';
const CACHE = `student-os-${VERSION}`;
const SHELL_CACHE = `${CACHE}-shell`;
const API_CACHE = `${CACHE}-api`;

self.addEventListener('install', (e) => {
  e.waitUntil(
    caches.open(SHELL_CACHE).then((c) => c.add('/index.html')),
  );
  self.skipWaiting();
});

self.addEventListener('activate', (e) => {
  e.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => !k.startsWith(CACHE)).map((k) => caches.delete(k))),
    ),
  );
  self.clients.claim();
});

self.addEventListener('fetch', (e) => {
  const { request } = e;
  const url = new URL(request.url);

  // Only handle same-origin requests.
  if (url.origin !== self.location.origin) return;

  // API calls: network-first with cached fallback.
  if (url.pathname.startsWith('/api/')) {
    e.respondWith(
      fetch(request)
        .then((res) => {
          if (res.ok) {
            const clone = res.clone();
            caches.open(API_CACHE).then((c) => c.put(request, clone));
          }
          return res;
        })
        .catch(() =>
          caches.match(request).then((cached) => cached || Response.error()),
        ),
    );
    return;
  }

  // Navigations: network-first, fall back to the offline shell.
  if (request.mode === 'navigate') {
    e.respondWith(
      fetch(request)
        .then((res) => {
          if (res.ok) {
            const clone = res.clone();
            caches.open(SHELL_CACHE).then((c) => c.put('/index.html', clone));
          }
          return res;
        })
        .catch(() => caches.match('/index.html').then((shell) => shell || Response.error())),
    );
    return;
  }

  // Static assets: cache-first (hashed filenames are immutable in production).
  if (
    request.destination === 'script' ||
    request.destination === 'style' ||
    request.destination === 'font' ||
    request.destination === 'image'
  ) {
    e.respondWith(
      caches.match(request).then(
        (cached) =>
          cached ||
          fetch(request).then((res) => {
            const clone = res.clone();
            caches.open(CACHE).then((c) => c.put(request, clone));
            return res;
          }),
      ),
    );
    return;
  }
});
