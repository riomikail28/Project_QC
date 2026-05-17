/**
 * QC Central Kitchen — API Client
 * Centralized fetch wrapper for backend communication.
 */

const API_BASE = window.location.origin.includes('localhost') || window.location.origin.includes('127.0.0.1') 
    ? 'http://localhost:5000/api' 
    : '/api';

const API = {
    async get(endpoint) {
        try {
            const url = this._url(endpoint);
            const response = await fetch(url, {
                headers: this._headers(),
                credentials: 'include'
            });
            try {
                return await this._handleResponse(response);
            } catch (err) {
                if (err && err.retry) {
                    const retryResp = await fetch(url, { headers: this._headers(), credentials: 'include' });
                    return await this._handleResponse(retryResp);
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
            const response = await fetch(url, {
                method: 'POST',
                headers: this._headers(),
                body: JSON.stringify(data),
                credentials: 'include'
            });
            try {
                return await this._handleResponse(response);
            } catch (err) {
                if (err && err.retry) {
                    const retryResp = await fetch(url, { method: 'POST', headers: this._headers(), body: JSON.stringify(data), credentials: 'include' });
                    return await this._handleResponse(retryResp);
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
            const response = await fetch(url, {
                method: 'PATCH',
                headers: this._headers(),
                body: JSON.stringify(data),
                credentials: 'include'
            });
            try {
                return await this._handleResponse(response);
            } catch (err) {
                if (err && err.retry) {
                    const retryResp = await fetch(url, { method: 'PATCH', headers: this._headers(), body: JSON.stringify(data), credentials: 'include' });
                    return await this._handleResponse(retryResp);
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
            const response = await fetch(url, {
                method: 'DELETE',
                headers: this._headers(),
                credentials: 'include'
            });
            try {
                return await this._handleResponse(response);
            } catch (err) {
                if (err && err.retry) {
                    const retryResp = await fetch(url, { method: 'DELETE', headers: this._headers(), credentials: 'include' });
                    return await this._handleResponse(retryResp);
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
            const response = await fetch(url, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${localStorage.getItem('qc_token')}`
                },
                body: formData,
                credentials: 'include'
            });
            try {
                return await this._handleResponse(response);
            } catch (err) {
                if (err && err.retry) {
                    const retryResp = await fetch(url, { method: 'POST', headers: { 'Authorization': `Bearer ${localStorage.getItem('qc_token')}` }, body: formData, credentials: 'include' });
                    return await this._handleResponse(retryResp);
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
        return Promise.all(photos.map(file => {
            const formData = new FormData();
            formData.append('photo', file);
            return this.upload(endpoint, formData);
        }));
    },

    async uploadPhotoToSupabase(file, meta = {}) {
        this.validatePhoto(file);
        const config = this._supabaseConfig();
        const storagePath = this._storagePath(file, meta);
        const response = await fetch(`${config.url}/storage/v1/object/${config.bucket}/${storagePath}`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${config.anonKey}`,
                'apikey': config.anonKey,
                'Content-Type': file.type,
                'x-upsert': 'false'
            },
            body: file
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
