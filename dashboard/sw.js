const CACHE_NAME = 'qc-app-cache-v1';
const URLS_TO_CACHE = [
  './index.html',
  './login.html',
  'https://cdn.tailwindcss.com',
  'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css',
  'https://unpkg.com/html5-qrcode',
  'https://cdnjs.cloudflare.com/ajax/libs/localforage/1.10.0/localforage.min.js'
];

// Install event - cache assets
self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => {
        return cache.addAll(URLS_TO_CACHE);
      })
  );
  self.skipWaiting();
});

// Activate event - clean up old caches
self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(cacheNames => {
      return Promise.all(
        cacheNames.filter(name => name !== CACHE_NAME).map(name => caches.delete(name))
      );
    })
  );
  self.clients.claim();
});

// Fetch event - network first, fallback to cache
self.addEventListener('fetch', event => {
  // Hanya intercept GET requests
  if (event.request.method !== 'GET') return;
  
  // Skip API calls from caching, we want fresh data or fail
  if (event.request.url.includes('/health') || 
      event.request.url.includes('/batch') || 
      event.request.url.includes('/facility') ||
      event.request.url.includes('/report')) return;

  event.respondWith(
    fetch(event.request)
      .catch(() => {
        return caches.match(event.request);
      })
  );
});

// Di service-worker.js
self.addEventListener('sync', event => {
  if (event.tag === 'sync-photos') {
    event.waitUntil(syncPendingPhotos());
  }
});
