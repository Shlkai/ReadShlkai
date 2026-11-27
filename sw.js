// Shikai: guarda o app e as bibliotecas para abrir sem internet.
const CACHE = 'shikai-v6';
const SHELL = ['./', './index.html', './manifest.webmanifest', './icon.svg', './icon-192.png', './icon-512.png', './lib/unrar.bundle.js',
  'lib/pdf.min.js',
  'lib/pdf.worker.min.js',
  'lib/jszip.min.js'];
self.addEventListener('install', e => { e.waitUntil(caches.open(CACHE).then(c => c.addAll(SHELL)).then(() => self.skipWaiting())); });
self.addEventListener('activate', e => { e.waitUntil(caches.keys().then(ks => Promise.all(ks.filter(k => k !== CACHE).map(k => caches.delete(k)))).then(() => self.clients.claim())); });
self.addEventListener('fetch', e => {
  const u = new URL(e.request.url);
  if (e.request.method !== 'GET' || u.hostname === 'www.googleapis.com') return; // downloads do Drive passam direto
  const isApp = u.origin === location.origin;
  const isLib = /cdnjs\.cloudflare\.com|fonts\.(googleapis|gstatic)\.com/.test(u.hostname);
  if (!isApp && !isLib) return;
  if (isApp && e.request.mode === 'navigate') {
    // página: tenta a versão nova, cai para a guardada se estiver offline
    e.respondWith(fetch(e.request, { cache: 'no-cache' }).then(r => { const c = r.clone(); caches.open(CACHE).then(k => k.put('./index.html', c)); return r; }).catch(() => caches.match('./index.html')));
    return;
  }
  e.respondWith(caches.match(e.request).then(hit => hit || fetch(e.request).then(r => { if (r.ok || r.type === 'opaque') { const c = r.clone(); caches.open(CACHE).then(k => k.put(e.request, c)); } return r; })));
});
