/**
 * QC Central Kitchen — API Client
 * Centralized fetch wrapper for backend communication.
 */

const API_BASE = window.location.origin.includes('localhost') || window.location.origin.includes('127.0.0.1') 
    ? 'http://localhost:5000/api' 
    : '/api';

const API = {
    // PERFORMANCE_OPTIMIZED: shared memory cache + in-flight request dedupe for fast route switching.
    _cache: new Map(),
    _pending: new Map(),

    async get(endpoint) {
        const url = this._url(endpoint);
        const pendingKey = `GET:${url}`;
        if (this._pending.has(pendingKey)) return this._pending.get(pendingKey);
        const request = this._getNetwork(endpoint).finally(() => this._pending.delete(pendingKey));
        this._pending.set(pendingKey, request);
        return request;
    },

    async getCached(endpoint, ttlMs = 60000, options = {}) {
        const key = options.cacheKey || this._cacheKey(endpoint);
        const cached = this._cache.get(key);
        if (!options.force && cached && Date.now() < cached.expiresAt) {
            return cached.data;
        }
        const data = await this.get(endpoint);
        this._setCache(key, data, ttlMs);
        return data;
    },

    async getSWR(endpoint, options = {}) {
        const ttlMs = options.ttlMs ?? 60000;
        const key = options.cacheKey || this._cacheKey(endpoint);
        const cached = this._cache.get(key);
        const isFresh = cached && Date.now() < cached.expiresAt;

        if (cached && !options.force) {
            if (!isFresh && options.revalidate !== false) {
                this.get(endpoint)
                    .then(data => {
                        this._setCache(key, data, ttlMs);
                        options.onUpdate?.(data);
                    })
                    .catch(error => options.onError?.(error));
            }
            return cached.data;
        }

        const data = await this.get(endpoint);
        this._setCache(key, data, ttlMs);
        return data;
    },

    hasFreshCache(endpoint, cacheKey = null) {
        const cached = this._cache.get(cacheKey || this._cacheKey(endpoint));
        return Boolean(cached && Date.now() < cached.expiresAt);
    },

    clearCache(pattern = null) {
        if (!pattern) {
            this._cache.clear();
            return;
        }
        for (const key of this._cache.keys()) {
            if (key.includes(pattern)) this._cache.delete(key);
        }
    },

    async _getNetwork(endpoint) {
        try {
            const url = this._url(endpoint);
            const started = performance.now();
            const response = await fetch(url, {
                headers: this._headers(),
                credentials: 'include'
            });
            try {
                const data = await this._handleResponse(response);
                this._metric('API response time', endpoint, started);
                return data;
            } catch (err) {
                if (err && err.retry) {
                    const retryResp = await fetch(url, { headers: this._headers(), credentials: 'include' });
                    const data = await this._handleResponse(retryResp);
                    this._metric('API response time', `${endpoint} retry`, started);
                    return data;
                }
                throw err;
            }
        } catch (error) {
            console.error(`GET ${endpoint} failed:`, error);
            throw error;
        }
    },

    async post(endpoint, data) {
        try {
            const url = this._url(endpoint);
            const started = performance.now();
            const response = await fetch(url, {
                method: 'POST',
                headers: this._headers(),
                body: JSON.stringify(data),
                credentials: 'include'
            });
            try {
                const result = await this._handleResponse(response);
                this._afterMutation(endpoint);
                this._metric('API response time', `POST ${endpoint}`, started);
                return result;
            } catch (err) {
                if (err && err.retry) {
                    const retryResp = await fetch(url, { method: 'POST', headers: this._headers(), body: JSON.stringify(data), credentials: 'include' });
                    const result = await this._handleResponse(retryResp);
                    this._afterMutation(endpoint);
                    this._metric('API response time', `POST ${endpoint} retry`, started);
                    return result;
                }
                throw err;
            }
        } catch (error) {
            console.error(`POST ${endpoint} failed:`, error);
            throw error;
        }
    },

    async patch(endpoint, data) {
        try {
            const url = this._url(endpoint);
            const started = performance.now();
            const response = await fetch(url, {
                method: 'PATCH',
                headers: this._headers(),
                body: JSON.stringify(data),
                credentials: 'include'
            });
            try {
                const result = await this._handleResponse(response);
                this._afterMutation(endpoint);
                this._metric('API response time', `PATCH ${endpoint}`, started);
                return result;
            } catch (err) {
                if (err && err.retry) {
                    const retryResp = await fetch(url, { method: 'PATCH', headers: this._headers(), body: JSON.stringify(data), credentials: 'include' });
                    const result = await this._handleResponse(retryResp);
                    this._afterMutation(endpoint);
                    this._metric('API response time', `PATCH ${endpoint} retry`, started);
                    return result;
                }
                throw err;
            }
        } catch (error) {
            console.error(`PATCH ${endpoint} failed:`, error);
            throw error;
        }
    },

    async delete(endpoint) {
        try {
            const url = this._url(endpoint);
            const started = performance.now();
            const response = await fetch(url, {
                method: 'DELETE',
                headers: this._headers(),
                credentials: 'include'
            });
            try {
                const result = await this._handleResponse(response);
                this._afterMutation(endpoint);
                this._metric('API response time', `DELETE ${endpoint}`, started);
                return result;
            } catch (err) {
                if (err && err.retry) {
                    const retryResp = await fetch(url, { method: 'DELETE', headers: this._headers(), credentials: 'include' });
                    const result = await this._handleResponse(retryResp);
                    this._afterMutation(endpoint);
                    this._metric('API response time', `DELETE ${endpoint} retry`, started);
                    return result;
                }
                throw err;
            }
        } catch (error) {
            console.error(`DELETE ${endpoint} failed:`, error);
            throw error;
        }
    },

    async upload(endpoint, formData) {
        try {
            const url = this._url(endpoint);
            const started = performance.now();
            const response = await fetch(url, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${localStorage.getItem('qc_token')}`
                },
                body: formData,
                credentials: 'include'
            });
            try {
                const result = await this._handleResponse(response);
                this._afterMutation(endpoint);
                this._metric('API response time', `UPLOAD ${endpoint}`, started);
                return result;
            } catch (err) {
                if (err && err.retry) {
                    const retryResp = await fetch(url, { method: 'POST', headers: { 'Authorization': `Bearer ${localStorage.getItem('qc_token')}` }, body: formData, credentials: 'include' });
                    const result = await this._handleResponse(retryResp);
                    this._afterMutation(endpoint);
                    this._metric('API response time', `UPLOAD ${endpoint} retry`, started);
                    return result;
                }
                throw err;
            }
        } catch (error) {
            console.error(`UPLOAD ${endpoint} failed:`, error);
            throw error;
        }
    },

    validatePhoto(file) {
        const allowedTypes = ['image/jpeg', 'image/png', 'image/webp'];
        if (!file) throw new Error('Upload gagal: file kosong');
        if (!allowedTypes.includes(file.type)) {
            throw new Error(`Upload gagal: format ${file.name || 'file'} tidak didukung. Gunakan JPG, PNG, atau WEBP.`);
        }
        if (file.size > 10 * 1024 * 1024) {
            throw new Error(`Upload gagal: ukuran ${file.name || 'file'} melebihi 10MB.`);
        }
    },

    async uploadPhotos(files, endpoint = '/storage/upload') {
        const photos = Array.from(files || []);
        photos.forEach(file => this.validatePhoto(file));
        const prepared = await this.preparePhotos(photos);
        return Promise.all(prepared.map(file => {
            const formData = new FormData();
            formData.append('photo', file);
            return this.upload(endpoint, formData);
        }));
    },

    async uploadPhotoToSupabase(file, meta = {}) {
        this.validatePhoto(file);
        const photo = await this.preparePhoto(file);
        const config = this._supabaseConfig();
        const storagePath = this._storagePath(photo, meta);
        const response = await fetch(`${config.url}/storage/v1/object/${config.bucket}/${storagePath}`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${config.anonKey}`,
                'apikey': config.anonKey,
                'Content-Type': photo.type,
                'x-upsert': 'false'
            },
            body: photo
        });

        if (!response.ok) {
            const error = await response.json().catch(() => ({}));
            throw new Error(error.message || `Upload Supabase gagal (${response.status})`);
        }

        return {
            url: `${config.url}/storage/v1/object/public/${config.bucket}/${storagePath}`,
            storage_path: storagePath,
            bucket: config.bucket
        };
    },

    async preparePhoto(file, options = {}) {
        this.validatePhoto(file);
        if (window.ImageCompression?.compressImage) {
            return await window.ImageCompression.compressImage(file, options);
        }
        if (typeof window.compressImage === 'function') {
            return await window.compressImage(file, options);
        }
        return file;
    },

    async preparePhotos(files, options = {}) {
        const photos = Array.from(files || []);
        photos.forEach(file => this.validatePhoto(file));
        if (window.ImageCompression?.compressImages) {
            return await window.ImageCompression.compressImages(photos, options);
        }
        return Promise.all(photos.map(file => this.preparePhoto(file, options)));
    },

    _supabaseConfig() {
        const config = window.QC_CONFIG || {};
        const url = String(config.supabaseUrl || '').replace(/\/+$/, '');
        const anonKey = String(config.supabaseAnonKey || '');
        const bucket = String(config.supabaseStorageBucket || 'qc-evidence');

        if (!url || !anonKey) {
            throw new Error('Konfigurasi Supabase frontend belum tersedia.');
        }
        if (!/^https:\/\/[a-z0-9-]+\.supabase\.co$/i.test(url)) {
            throw new Error('URL Supabase frontend tidak valid.');
        }
        if (this._isUnsafeSupabaseKey(anonKey)) {
            throw new Error('Supabase service-role key tidak boleh digunakan di frontend.');
        }

        return { url, anonKey, bucket };
    },

    _isUnsafeSupabaseKey(key) {
        if (!key || key.startsWith('sb_secret_')) return true;
        try {
            const payload = key.split('.')[1];
            if (!payload) return false;
            const decoded = JSON.parse(atob(payload.replace(/-/g, '+').replace(/_/g, '/')));
            return decoded.role === 'service_role';
        } catch (error) {
            return false;
        }
    },

    _storagePath(file, meta = {}) {
        const extension = this._extensionForPhoto(file);
        const staffId = this._safePathPart(meta.staffId || 'staff');
        const source = this._safePathPart(meta.source || 'inspection');
        const category = this._categoryPath(source);
        const timestamp = new Date().toISOString().slice(0, 10);
        const random = (crypto.randomUUID ? crypto.randomUUID() : `${Date.now()}-${Math.random()}`).replace(/[^a-z0-9-]/gi, '');
        return `staff/${staffId}/${category}/${timestamp}/${source}-${random}.${extension}`;
    },

    _categoryPath(source) {
        if (source.includes('temperature') || source.includes('monitoring')) return 'temperature';
        if (source.includes('barcode')) return 'barcode';
        if (source.includes('ccp')) return 'ccp';
        return 'inspection';
    },

    _safePathPart(value) {
        return String(value || 'unknown')
            .trim()
            .toLowerCase()
            .replace(/[^a-z0-9_-]+/g, '-')
            .replace(/^-+|-+$/g, '')
            .slice(0, 80) || 'unknown';
    },

    _extensionForPhoto(file) {
        if (file.type === 'image/png') return 'png';
        if (file.type === 'image/webp') return 'webp';
        return 'jpg';
    },

    _url(endpoint) {
        const raw = String(endpoint || '');
        if (/^https?:\/\//i.test(raw)) return raw;
        const path = raw.startsWith('/') ? raw : `/${raw}`;
        if (path === '/api' || path.startsWith('/api/')) return path;
        return `${API_BASE}${path}`;
    },

    _cacheKey(endpoint) {
        return `GET:${this._url(endpoint)}`;
    },

    _setCache(key, data, ttlMs) {
        this._cache.set(key, {
            data,
            expiresAt: Date.now() + ttlMs,
            storedAt: Date.now()
        });
    },

    _afterMutation(endpoint) {
        const path = String(endpoint || '');
        this.clearCache('dashboard');
        ['dashboard', 'monitoring', 'reports', 'batches', 'findings', 'products', 'staff', 'facility', 'inspection'].forEach(pattern => {
            if (path.includes(pattern)) this.clearCache(pattern);
        });
    },

    _metric(label, endpoint, started) {
        const duration = Math.round(performance.now() - started);
        console.info(`[PERFORMANCE_OPTIMIZED] ${label}: ${endpoint} ${duration}ms`);
    },

    _headers() {
        return {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${localStorage.getItem('qc_token')}`
        };
    },

    async _handleResponse(response) {
        const text = await response.text();
        let data = {};
        try {
            data = text ? JSON.parse(text) : {};
        } catch (error) {
            data = { error: text || 'Invalid server response' };
        }
        if (!response.ok) {
            const serverMessage = this._errorMessage(data, response);
            const error = new Error(serverMessage);
            error.status = response.status;
            error.data = data;
            // Attempt refresh once on 401 before redirecting
            if (error.status === 401) {
                try {
                    // call refresh endpoint
                    const refreshRes = await fetch(this._url('/staff/refresh'), { method: 'POST', credentials: 'include' });
                    if (refreshRes.ok) {
                        const refreshed = await refreshRes.json();
                        if (refreshed && refreshed.token) {
                            localStorage.setItem('qc_token', refreshed.token);
                            // Retry original request by returning a rejected promise that caller may re-run
                            throw Object.assign(new Error('Retry'), { retry: true });
                        }
                    }
                } catch (e) {
                    // fallthrough to logout
                }

                localStorage.removeItem('qc_token');
                localStorage.removeItem('qc_user');
                if (!window.location.pathname.endsWith('login.html')) {
                    window.location.href = '/login.html';
                }
            }
            throw error;
        }
        return data;
    },

    _errorMessage(data, response) {
        const raw = data || {};
        const message = raw.message || raw.detail || raw.error;
        if (typeof message === 'string' && message.trim()) {
            return message.trim();
        }
        if (raw.error_code) {
            return `Request gagal (${raw.error_code})`;
        }
        if (response.status === 400) return 'Request tidak valid. Periksa data yang dikirim.';
        if (response.status === 404) return 'Data tidak ditemukan atau sudah berubah.';
        if (response.status === 409) return 'Data masih dipakai oleh relasi lain.';
        if (response.status === 503) return 'Supabase belum terkoneksi atau environment production belum valid.';
        return `Request gagal (${response.status} ${response.statusText || 'Error'})`;
    }
};
