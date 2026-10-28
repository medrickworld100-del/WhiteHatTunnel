const C='ts1';
const F=['./','index.html','manifest.json','assets/logo.jpg','assets/icon-192.png','assets/icon-512.png'];
self.addEventListener('install',e=>e.waitUntil(caches.open(C).then(c=>c.addAll(F))));
self.addEventListener('fetch',e=>e.respondWith(caches.match(e.request).then(r=>r||fetch(e.request))));
