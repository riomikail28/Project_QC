/**
 * QC Central Kitchen — Camera Module v2.0
 * Fix: permission handling, image compression, offline-safe storage
 */

import localforage from 'https://cdn.jsdelivr.net/npm/localforage@1.10.0/+esm';


// ─── Constants ────────────────────────────────────────────────────────────────
const MAX_SIZE_KB   = 800;
const JPEG_QUALITY  = 0.82;
const PHOTO_STORE   = 'qc_pending_photos';
const SYNC_TAG      = 'sync-qc-evidence';
const DEFAULT_STORAGE_BUCKET = 'qc-evidence';
const ALLOWED_MIME_TYPES = new Set(['image/jpeg', 'image/png', 'image/webp']);


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
  validateUploadBlob(blob);
  const { SUPABASE_URL, SUPABASE_ANON_KEY, STORAGE_BUCKET } = getSupabaseConfig();
  const contentType = blob.type && ALLOWED_MIME_TYPES.has(blob.type) ? blob.type : 'image/jpeg';
  const filename = buildStoragePath(meta, extensionForMime(contentType));

  const res = await fetch(
    `${SUPABASE_URL}/storage/v1/object/${STORAGE_BUCKET}/${filename}`,
    {
      method : 'POST',
      headers: {
        'Authorization': `Bearer ${SUPABASE_ANON_KEY}`,
        'apikey'       : SUPABASE_ANON_KEY,
        'Content-Type' : contentType,
        'x-upsert'     : 'false'
      },
      body: blob
    }
  );

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.message || `HTTP ${res.status}`);
  }

  return `${SUPABASE_URL}/storage/v1/object/public/${STORAGE_BUCKET}/${filename}`;
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
  const config = window.QC_CONFIG || {};
  const supabaseUrl = String(config.supabaseUrl || '').replace(/\/+$/, '');
  const supabaseAnonKey = String(config.supabaseAnonKey || '');
  const storageBucket = String(config.supabaseStorageBucket || DEFAULT_STORAGE_BUCKET);

  if (!supabaseUrl || !supabaseAnonKey) {
    throw new Error('Supabase frontend config belum tersedia. Pastikan /js/config.js dimuat sebelum camera-module.js.');
  }
  if (!/^https:\/\/[a-z0-9-]+\.supabase\.co$/i.test(supabaseUrl)) {
    throw new Error('Supabase URL frontend tidak valid.');
  }
  if (isUnsafeSupabasePublicKey(supabaseAnonKey)) {
    throw new Error('Supabase service-role key tidak boleh dipakai di frontend.');
  }

  return {
    SUPABASE_URL: supabaseUrl,
    SUPABASE_ANON_KEY: supabaseAnonKey,
    STORAGE_BUCKET: storageBucket
  };
}

function isUnsafeSupabasePublicKey(key) {
  if (!key) return true;
  if (key.startsWith('sb_secret_')) return true;

  try {
    const payload = key.split('.')[1];
    if (!payload) return false;
    const decoded = JSON.parse(atob(payload.replace(/-/g, '+').replace(/_/g, '/')));
    return decoded.role === 'service_role';
  } catch (error) {
    return false;
  }
}

function validateUploadBlob(blob) {
  if (!blob || !blob.size) {
    throw new Error('Foto kosong atau tidak valid.');
  }
  if (blob.size > (window.QC_CONFIG?.maxUploadBytes || 10 * 1024 * 1024)) {
    throw new Error('Ukuran foto melebihi batas upload.');
  }
  if (blob.type && !ALLOWED_MIME_TYPES.has(blob.type)) {
    throw new Error('Format foto tidak didukung. Gunakan JPG, PNG, atau WEBP.');
  }
}

function buildStoragePath(meta = {}, extension = 'jpg') {
  const stationId = safePathPart(meta.stationId || 'unknown-station');
  const batchId = safePathPart(meta.batchId || 'unknown-batch');
  const ccp = safePathPart(meta.ccp || 'evidence');
  return `${stationId}/${batchId}/${ccp}_${Date.now()}.${extension}`;
}

function safePathPart(value) {
  return String(value)
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9_-]+/g, '-')
    .replace(/^-+|-+$/g, '')
    .slice(0, 80) || 'unknown';
}

function extensionForMime(contentType) {
  if (contentType === 'image/png') return 'png';
  if (contentType === 'image/webp') return 'webp';
  return 'jpg';
}

export async function getPendingCount() {
  const keys = await localforage.keys();
  return keys.filter(k => k.startsWith(PHOTO_STORE + ':')).length;
}
