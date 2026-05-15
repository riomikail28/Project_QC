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
            const response = await fetch(`${API_BASE}${endpoint}`, {
                headers: this._headers(),
                credentials: 'include'
            });
            try {
                return await this._handleResponse(response);
            } catch (err) {
                if (err && err.retry) {
                    const retryResp = await fetch(`${API_BASE}${endpoint}`, { headers: this._headers(), credentials: 'include' });
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
            const response = await fetch(`${API_BASE}${endpoint}`, {
                method: 'POST',
                headers: this._headers(),
                body: JSON.stringify(data),
                credentials: 'include'
            });
            try {
                return await this._handleResponse(response);
            } catch (err) {
                if (err && err.retry) {
                    const retryResp = await fetch(`${API_BASE}${endpoint}`, { method: 'POST', headers: this._headers(), body: JSON.stringify(data), credentials: 'include' });
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
            const response = await fetch(`${API_BASE}${endpoint}`, {
                method: 'PATCH',
                headers: this._headers(),
                body: JSON.stringify(data),
                credentials: 'include'
            });
            try {
                return await this._handleResponse(response);
            } catch (err) {
                if (err && err.retry) {
                    const retryResp = await fetch(`${API_BASE}${endpoint}`, { method: 'PATCH', headers: this._headers(), body: JSON.stringify(data), credentials: 'include' });
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
            const response = await fetch(`${API_BASE}${endpoint}`, {
                method: 'DELETE',
                headers: this._headers(),
                credentials: 'include'
            });
            try {
                return await this._handleResponse(response);
            } catch (err) {
                if (err && err.retry) {
                    const retryResp = await fetch(`${API_BASE}${endpoint}`, { method: 'DELETE', headers: this._headers(), credentials: 'include' });
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
            const response = await fetch(`${API_BASE}${endpoint}`, {
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
                    const retryResp = await fetch(`${API_BASE}${endpoint}`, { method: 'POST', headers: { 'Authorization': `Bearer ${localStorage.getItem('qc_token')}` }, body: formData, credentials: 'include' });
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
            const error = new Error(data.detail || data.error || 'Request failed');
            error.status = response.status;
            // Attempt refresh once on 401 before redirecting
            if (error.status === 401) {
                try {
                    // call refresh endpoint
                    const refreshRes = await fetch(`${API_BASE}/staff/refresh`, { method: 'POST', credentials: 'include' });
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
    }
};
