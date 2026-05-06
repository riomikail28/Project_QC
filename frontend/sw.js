const CACHE_NAME = 'qc-central-v1';
const ASSETS = [
    './',
    './dashboard.html',
    './login.html',
    '../css/dashboard.css',
    '../css/login.css',
    '../js/api.js',
    '../js/auth.js',
    '../js/ui-mobile.js'
];

self.addEventListener('install', (e) => {
    e.waitUntil(
        caches.open(CACHE_NAME).then((cache) => cache.addAll(ASSETS))
    );
});

self.addEventListener('fetch', (e) => {
    e.respondWith(
        caches.match(e.request).then((res) => res || fetch(e.request))
    );
});
