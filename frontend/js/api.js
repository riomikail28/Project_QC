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
                headers: this._headers()
            });
            return await this._handleResponse(response);
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
                body: JSON.stringify(data)
            });
            return await this._handleResponse(response);
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
                body: JSON.stringify(data)
            });
            return await this._handleResponse(response);
        } catch (error) {
            console.error(`PATCH ${endpoint} failed:`, error);
            throw error;
        }
    },

    async delete(endpoint) {
        try {
            const response = await fetch(`${API_BASE}${endpoint}`, {
                method: 'DELETE',
                headers: this._headers()
            });
            return await this._handleResponse(response);
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
                body: formData
            });
            return await this._handleResponse(response);
        } catch (error) {
            console.error(`UPLOAD ${endpoint} failed:`, error);
            throw error;
        }
    },

    _headers() {
        return {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${localStorage.getItem('qc_token')}`
        };
    },

    async _handleResponse(response) {
        const text = await response.text();
        const data = text ? JSON.parse(text) : {};
        if (!response.ok) {
            const error = new Error(data.detail || data.error || 'Request failed');
            error.status = response.status;
            throw error;
        }
        return data;
    }
};
