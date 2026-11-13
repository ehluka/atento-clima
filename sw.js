// Atento Clima: guarda la app para abrir sin conexión; los datos siempre se piden a la red.
const V = 'ac-v11';
const SHELL = ['./', 'index.html', 'style.css', 'app.js', 'manifest.webmanifest', 'icons/icon.svg', 'icons/icon-192.png'];
self.addEventListener('install', e => { e.waitUntil(caches.open(V).then(c => c.addAll(SHELL))); self.skipWaiting(); });
self.addEventListener('activate', e => {
  e.waitUntil(caches.keys().then(ks => Promise.all(ks.filter(k => k !== V).map(k => caches.delete(k)))));
  self.clients.claim();
});
self.addEventListener('fetch', e => {
  const u = new URL(e.request.url);
  if (e.request.method !== 'GET' || u.origin !== location.origin || u.pathname.includes('/data/')) return;
  // Red primero (para tomar actualizaciones), caché si no hay conexión.
  e.respondWith(fetch(e.request).then(r => {
    const copy = r.clone(); caches.open(V).then(c => c.put(e.request, copy)); return r;
  }).catch(() => caches.match(e.request).then(r => r || caches.match('index.html'))));
});
