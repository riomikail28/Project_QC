const CACHE_NAME = 'qc-central-v5';
const PRECACHE_ASSETS = [
  '/',
  '/login.html',
  '/staff/',
  '/staff/dashboard.html',
  '/staff/monitoring.html',
  '/staff/inspection.html',
  '/staff/new_batch.html',
  '/staff/ccp_stage.html',
  '/css/dashboard.css',
  '/styles/global.css',
  '/styles/variables.css',
  '/js/config.js',
  '/js/api.js',
  '/js/auth.js',
  '/js/ui-mobile.js',
  '/js/image-compression.js',
  '/js/camera-module.js',
  '/js/performance-optimized.js',
  'https://cdn.jsdelivr.net/npm/localforage@1.10.0/+esm',
  'https://unpkg.com/lucide@latest',
  'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css'
];

self.addEventListener('install', (e) => {
  e.waitUntil(
    caches.open(CACHE_NAME)
      .then((cache) => cache.addAll(PRECACHE_ASSETS))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', (e) => {
  e.waitUntil(
    caches.keys().then((keys) => {
      return Promise.all(
        keys.map((key) => {
          if (key !== CACHE_NAME) {
            return caches.delete(key);
          }
        })
      );
    }).then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', (e) => {
  const url = new URL(e.request.url);

  // Hanya tangani request HTTP/HTTPS (bypass chrome-extension, data:, dll.)
  if (!url.protocol.startsWith('http')) {
    return;
  }

  // Jangan cache request API, Supabase RPC, Google Sheets, atau non-GET requests
  if (
    url.pathname.startsWith('/api/') || 
    url.pathname.startsWith('/v1/') || 
    url.hostname.includes('script.google.com') ||
    url.hostname.includes('supabase.co') ||
    e.request.method !== 'GET'
  ) {
    return; // Langsung bypass ke network
  }

  // Stale-While-Revalidate strategy untuk static assets (HTML, CSS, JS, Font, Logo, Icons)
  e.respondWith(
    caches.match(e.request).then((cachedResponse) => {
      // Jalankan network fetch
      const fetchPromise = fetch(e.request).then((networkResponse) => {
        if (networkResponse && networkResponse.status === 200) {
          const responseToCache = networkResponse.clone();
          caches.open(CACHE_NAME).then((cache) => {
            cache.put(e.request, responseToCache);
          });
        }
        return networkResponse;
      });

      // Jika ada di cache, kembalikan versi cache langsung dan biarkan fetch berjalan di background
      if (cachedResponse) {
        // Tangani kegagalan fetch di background (misal offline/CSP block) agar tidak menyebabkan TypeError
        fetchPromise.catch((err) => console.warn("Background fetch failed:", err));
        return cachedResponse;
      }

      // Jika tidak ada di cache, kembalikan fetchPromise dari network
      return fetchPromise;
    }).catch(() => {
      // Fallback offline untuk navigasi utama jika gagal total
      if (e.request.mode === 'navigate') {
        return caches.match('/login.html');
      }
    })
  );
});
