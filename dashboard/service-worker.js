/**
 * QC Central Kitchen — Service Worker v2.0
 * Fix: background sync untuk upload foto saat offline
 */

const CACHE_NAME   = 'qc-app-v2';
const SYNC_TAG     = 'sync-qc-photos';
const PHOTO_STORE  = 'qc_pending_photos';

// ─── Assets yang di-cache untuk offline ──────────────────────────────────────
const STATIC_ASSETS = [
  '/',
  '/dashboard/operator.html',
  '/dashboard/login.html',
  '/dashboard/app.js',
  '/dashboard/style.css',
  '/dashboard/camera-module.js',
  '/dashboard/ocr-reader.js',
  'https://cdn.jsdelivr.net/npm/localforage@1.10.0/dist/localforage.min.js'
];

// ─── Install: cache static assets ────────────────────────────────────────────
self.addEventListener('install', event => {
  self.skipWaiting();
  event.waitUntil(
    caches.open(CACHE_NAME).then(cache =>
      cache.addAll(STATIC_ASSETS.map(url => new Request(url, { cache: 'reload' })))
        .catch(err => console.warn('[SW] Gagal cache assets:', err))
    )
  );
});

// ─── Activate: hapus cache lama ───────────────────────────────────────────────
self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(keys =>
      Promise.all(keys.filter(k => k !== CACHE_NAME).map(k => caches.delete(k)))
    ).then(() => self.clients.claim())
  );
});

// ─── Fetch: strategi Cache-First untuk static, Network-First untuk API ────────
self.addEventListener('fetch', event => {
  const { request } = event;
  const url = new URL(request.url);

  // Abaikan non-GET dan Chrome Extension
  if (request.method !== 'GET' || url.protocol === 'chrome-extension:') return;

  // API Supabase → Network-First, fallback ke cache
  if (url.hostname.includes('supabase')) {
    event.respondWith(networkFirst(request));
    return;
  }

  // Static assets → Cache-First
  event.respondWith(cacheFirst(request));
});

async function cacheFirst(request) {
  const cached = await caches.match(request);
  if (cached) return cached;
  try {
    const response = await fetch(request);
    if (response.ok) {
      const cache = await caches.open(CACHE_NAME);
      cache.put(request, response.clone());
    }
    return response;
  } catch {
    return new Response('Offline — konten tidak tersedia', { status: 503 });
  }
}

async function networkFirst(request) {
  try {
    const response = await fetch(request);
    if (response.ok) {
      const cache = await caches.open(CACHE_NAME);
      cache.put(request, response.clone());
    }
    return response;
  } catch {
    const cached = await caches.match(request);
    return cached || new Response(JSON.stringify({ error: 'Offline' }), {
      status: 503,
      headers: { 'Content-Type': 'application/json' }
    });
  }
}

// ─── Background Sync: upload foto pending ────────────────────────────────────
self.addEventListener('sync', event => {
  if (event.tag === SYNC_TAG) {
    event.waitUntil(syncPendingPhotos());
  }
});

async function syncPendingPhotos() {
  // Gunakan IndexedDB langsung dari SW (localforage tidak tersedia di SW)
  const db = await openPhotoDb();
  const tx = db.transaction('photos', 'readwrite');
  const store = tx.objectStore('photos');
  const pending = await getAllPending(store);

  console.info(`[SW Sync] ${pending.length} foto pending ditemukan`);

  for (const item of pending) {
    try {
      const url = await uploadBlob(item.blob, item.meta);
      // Mark as synced
      item.meta.synced   = true;
      item.meta.publicUrl = url;
      item.blob           = null; // bebaskan memori
      const putTx = db.transaction('photos', 'readwrite');
      putTx.objectStore('photos').put(item);
      await txComplete(putTx);
      console.info('[SW Sync] Upload berhasil:', item.meta.key);
    } catch (err) {
      console.warn('[SW Sync] Upload gagal, akan coba lagi:', err.message);
    }
  }

  // Kirim notifikasi ke semua tab
  const clients = await self.clients.matchAll();
  clients.forEach(client =>
    client.postMessage({ type: 'SYNC_COMPLETE', count: pending.length })
  );
}

// ─── IndexedDB helper (di SW tidak bisa pakai localforage) ───────────────────
function openPhotoDb() {
  return new Promise((resolve, reject) => {
    const req = indexedDB.open('qc-photos-db', 1);
    req.onupgradeneeded = e => {
      e.target.result.createObjectStore('photos', { keyPath: 'meta.key' });
    };
    req.onsuccess = e => resolve(e.target.result);
    req.onerror   = e => reject(e.target.error);
  });
}

function getAllPending(store) {
  return new Promise((resolve, reject) => {
    const results = [];
    const req = store.openCursor();
    req.onsuccess = e => {
      const cursor = e.target.result;
      if (!cursor) return resolve(results);
      if (!cursor.value.meta.synced) results.push(cursor.value);
      cursor.continue();
    };
    req.onerror = e => reject(e.target.error);
  });
}

function txComplete(tx) {
  return new Promise((resolve, reject) => {
    tx.oncomplete = resolve;
    tx.onerror    = e => reject(e.target.error);
  });
}

async function uploadBlob(blob, meta) {
  // Ambil config dari IndexedDB (disimpan saat login)
  const configDb = await openPhotoDb();
  const tx       = configDb.transaction('photos', 'readonly');
  const config   = await getConfig(tx);

  const filename = `${meta.stationId}/${meta.batchId}/${meta.ccp}_${Date.now()}.jpg`;
  const res = await fetch(
    `${config.supabaseUrl}/storage/v1/object/qc-photos/${filename}`,
    {
      method : 'POST',
      headers: {
        'Authorization': `Bearer ${config.supabaseAnonKey}`,
        'Content-Type' : 'image/jpeg',
        'x-upsert'     : 'false'
      },
      body: blob
    }
  );

  if (!res.ok) throw new Error(`Upload gagal HTTP ${res.status}`);
  return `${config.supabaseUrl}/storage/v1/object/public/qc-photos/${filename}`;
}

function getConfig(tx) {
  return new Promise((resolve, reject) => {
    const req = tx.objectStore('photos').get('__config__');
    req.onsuccess = e => resolve(e.target.result || {});
    req.onerror   = e => reject(e.target.error);
  });
}
