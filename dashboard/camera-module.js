/**
 * QC Central Kitchen — Camera Module v2.0
 * Fix: permission handling, image compression, offline-safe storage
 */

import localforage from 'https://cdn.jsdelivr.net/npm/localforage@1.10.0/dist/localforage.min.js';

// ─── Constants ────────────────────────────────────────────────────────────────
const MAX_SIZE_KB   = 800;
const JPEG_QUALITY  = 0.82;
const PHOTO_STORE   = 'qc_pending_photos';
const SYNC_TAG      = 'sync-qc-photos';

// ─── 1. Request camera permission with graceful fallback ──────────────────────
export async function requestCamera(videoEl) {
  const constraints = [
    { video: { facingMode: 'environment', width: { ideal: 1280 } } }, // rear cam HD
    { video: { facingMode: 'environment' } },                          // rear cam any
    { video: true }                                                     // any cam
  ];

  for (const c of constraints) {
    try {
      const stream = await navigator.mediaDevices.getUserMedia(c);
      if (videoEl) {
        videoEl.srcObject = stream;
        await videoEl.play();
      }
      return stream;
    } catch (err) {
      if (err.name === 'NotAllowedError') {
        // User denied — show settings guide, stop trying
        showPermissionGuide();
        throw err;
      }
      // OverconstrainedError / NotFoundError → try next constraint
      console.warn('[Camera] constraint failed, trying fallback:', err.name);
    }
  }
  throw new Error('Tidak ada kamera yang tersedia di perangkat ini.');
}

function showPermissionGuide() {
  const msg =
    'Izin kamera ditolak.\n\n' +
    'Cara mengaktifkan:\n' +
    '• Chrome Android: Pengaturan → Privasi → Izin Situs → Kamera\n' +
    '• Safari iOS: Pengaturan iPhone → Safari → Kamera → Izinkan\n\n' +
    'Setelah mengaktifkan, muat ulang halaman ini.';
  alert(msg);
}

// ─── 2. Capture photo from video stream ──────────────────────────────────────
export function captureFrame(videoEl) {
  const canvas = document.createElement('canvas');
  canvas.width  = videoEl.videoWidth;
  canvas.height = videoEl.videoHeight;
  canvas.getContext('2d').drawImage(videoEl, 0, 0);
  return canvas; // return canvas so we can preview + compress
}

// ─── 3. Compress image to target size ────────────────────────────────────────
export function compressImage(file, maxKB = MAX_SIZE_KB, quality = JPEG_QUALITY) {
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.onerror = reject;

    img.onload = () => {
      // Scale down if file is larger than target
      const scaleFactor = file.size > maxKB * 1024
        ? Math.sqrt((maxKB * 1024) / file.size)
        : 1;

      const canvas  = document.createElement('canvas');
      canvas.width  = Math.round(img.width  * scaleFactor);
      canvas.height = Math.round(img.height * scaleFactor);

      const ctx = canvas.getContext('2d');
      ctx.imageSmoothingEnabled = true;
      ctx.imageSmoothingQuality = 'high';
      ctx.drawImage(img, 0, 0, canvas.width, canvas.height);

      canvas.toBlob(
        blob => blob ? resolve(blob) : reject(new Error('Kompresi gagal')),
        'image/jpeg',
        quality
      );
    };

    img.src = URL.createObjectURL(file instanceof Blob ? file : new Blob([file]));
  });
}

// Overload for canvas (from captureFrame)
export function compressCanvas(canvas, maxKB = MAX_SIZE_KB, quality = JPEG_QUALITY) {
  return new Promise((resolve, reject) => {
    canvas.toBlob(async blob => {
      if (!blob) return reject(new Error('Canvas toBlob gagal'));
      if (blob.size <= maxKB * 1024) return resolve(blob);

      // Need to scale down
      const ratio   = Math.sqrt((maxKB * 1024) / blob.size);
      const c2      = document.createElement('canvas');
      c2.width      = Math.round(canvas.width  * ratio);
      c2.height     = Math.round(canvas.height * ratio);
      c2.getContext('2d').drawImage(canvas, 0, 0, c2.width, c2.height);
      c2.toBlob(
        b => b ? resolve(b) : reject(new Error('Re-compress gagal')),
        'image/jpeg', quality
      );
    }, 'image/jpeg', quality);
  });
}

// ─── 4. Save photo offline-first, schedule background sync ───────────────────
export async function savePhoto({ blob, batchId, ccp, operatorId, stationId }) {
  const key  = `${PHOTO_STORE}:${batchId}_${ccp}_${Date.now()}`;
  const meta = {
    key,
    batchId,
    ccp,
    operatorId,
    stationId,
    timestamp: new Date().toISOString(),
    synced: false
  };

  // Selalu simpan lokal dulu
  await localforage.setItem(key, { blob, meta });
  console.info('[QC] Foto disimpan lokal:', key);

  // Coba langsung upload jika online
  if (navigator.onLine) {
    try {
      const url = await uploadToSupabase(blob, meta);
      meta.synced   = true;
      meta.publicUrl = url;
      await localforage.setItem(key, { blob: null, meta }); // hapus blob setelah upload
      console.info('[QC] Foto berhasil diupload:', url);
      return { success: true, url, offline: false };
    } catch (err) {
      console.warn('[QC] Upload gagal, akan sync nanti:', err.message);
    }
  }

  // Daftarkan background sync
  await scheduleBackgroundSync();
  return { success: true, offline: true, key };
}

// ─── 5. Upload ke Supabase Storage ───────────────────────────────────────────
async function uploadToSupabase(blob, meta) {
  const { SUPABASE_URL, SUPABASE_ANON_KEY } = getSupabaseConfig();
  const filename = `${meta.stationId}/${meta.batchId}/${meta.ccp}_${Date.now()}.jpg`;

  const res = await fetch(
    `${SUPABASE_URL}/storage/v1/object/qc-photos/${filename}`,
    {
      method : 'POST',
      headers: {
        'Authorization': `Bearer ${SUPABASE_ANON_KEY}`,
        'Content-Type' : 'image/jpeg',
        'x-upsert'     : 'false'
      },
      body: blob
    }
  );

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.message || `HTTP ${res.status}`);
  }

  return `${SUPABASE_URL}/storage/v1/object/public/qc-photos/${filename}`;
}

// ─── 6. Background sync scheduler ────────────────────────────────────────────
async function scheduleBackgroundSync() {
  if (!('serviceWorker' in navigator) || !('SyncManager' in window)) {
    // Fallback: listen for online event
    window.addEventListener('online', syncPendingPhotos, { once: true });
    return;
  }
  try {
    const reg = await navigator.serviceWorker.ready;
    await reg.sync.register(SYNC_TAG);
    console.info('[QC] Background sync terdaftar:', SYNC_TAG);
  } catch (err) {
    console.warn('[QC] Background sync tidak didukung:', err.message);
    window.addEventListener('online', syncPendingPhotos, { once: true });
  }
}

// ─── 7. Sync semua foto pending ───────────────────────────────────────────────
export async function syncPendingPhotos() {
  const keys = await localforage.keys();
  const pending = keys.filter(k => k.startsWith(PHOTO_STORE + ':'));

  console.info(`[QC] Sync ${pending.length} foto pending...`);
  let synced = 0;

  for (const key of pending) {
    const item = await localforage.getItem(key);
    if (!item || item.meta.synced) continue;

    try {
      const url = await uploadToSupabase(item.blob, item.meta);
      await localforage.setItem(key, {
        blob: null,
        meta: { ...item.meta, synced: true, publicUrl: url }
      });
      synced++;
    } catch (err) {
      console.warn('[QC] Gagal sync foto:', key, err.message);
    }
  }

  console.info(`[QC] Sync selesai: ${synced}/${pending.length}`);
  return synced;
}

// ─── 8. Util ──────────────────────────────────────────────────────────────────
function getSupabaseConfig() {
  return {
    SUPABASE_URL     : window.QC_CONFIG?.supabaseUrl     || '',
    SUPABASE_ANON_KEY: window.QC_CONFIG?.supabaseAnonKey || ''
  };
}

export async function getPendingCount() {
  const keys = await localforage.keys();
  return keys.filter(k => k.startsWith(PHOTO_STORE + ':')).length;
}
