/**
 * QC Central Kitchen - Performance Optimized API Client
 * Implements caching, request batching, and optimized loading strategies
 */

class OptimizedAPI {
    constructor() {
        this.baseURL = window.location.origin.includes('localhost') 
            ? 'http://localhost:5000/api' 
            : '/api';
        this.cache = new Map();
        this.cacheExpiry = new Map();
        this.requestQueue = [];
        this.batchTimeout = null;
        this.CACHE_DURATION = 5 * 60 * 1000; // 5 minutes
    }

    // Enhanced caching with TTL
    async get(endpoint, useCache = true) {
        if (useCache && this.isCached(endpoint)) {
            return this.cache.get(endpoint);
        }

        try {
            const response = await this.fetchWithRetry(endpoint, {
                headers: this.getHeaders()
            });
            const data = await this._handleResponse(response);
            
            if (useCache && response.ok) {
                this.setCache(endpoint, data);
            }
            
            return data;
        } catch (error) {
            console.error(`GET ${endpoint} failed:`, error);
            throw error;
        }
    }

    // Request batching for non-critical updates
    batchRequest(method, endpoint, data) {
        return new Promise((resolve, reject) => {
            this.requestQueue.push({
                method,
                endpoint,
                data,
                resolve,
                reject
            });

            if (!this.batchTimeout) {
                this.batchTimeout = setTimeout(() => {
                    this.processBatch();
                }, 100); // Batch requests within 100ms
            }
        });
    }

    async processBatch() {
        if (this.requestQueue.length === 0) return;

        const batch = this.requestQueue.splice(0, 10); // Process max 10 requests at once
        this.batchTimeout = null;

        const promises = batch.map(async (req) => {
            try {
                const response = await fetch(`${this.baseURL}${req.endpoint}`, {
                    method: req.method,
                    headers: this.getHeaders(),
                    body: JSON.stringify(req.data)
                });
                const data = await this._handleResponse(response);
                req.resolve(data);
            } catch (error) {
                req.reject(error);
            }
        });

        await Promise.allSettled(promises);
    }

    // Lazy loading for dashboard components
    async loadDashboardData() {
        const criticalData = await this.get('/qc/dashboard');
        
        // Load non-critical data in background
        setTimeout(async () => {
            try {
                const alerts = await this.get('/alerts', false);
                this.updateDashboardUI({ ...criticalData, alerts });
            } catch (error) {
                console.warn('Background data load failed:', error);
            }
        }, 500);

        return criticalData;
    }

    // Image optimization for uploads
    async uploadOptimizedImage(file, maxSizeKB = 500) {
        return new Promise((resolve, reject) => {
            const canvas = document.createElement('canvas');
            const ctx = canvas.getContext('2d');
            const img = new Image();

            img.onload = () => {
                // Calculate new dimensions to fit within max size
                let width = img.width;
                let height = img.height;
                const maxDimension = 1200;

                if (width > maxDimension || height > maxDimension) {
                    const ratio = Math.min(maxDimension / width, maxDimension / height);
                    width *= ratio;
                    height *= ratio;
                }

                canvas.width = width;
                canvas.height = height;
                ctx.drawImage(img, 0, 0, width, height);

                // Convert to blob with quality adjustment
                canvas.toBlob((blob) => {
                    if (blob.size <= maxSizeKB * 1024) {
                        resolve(blob);
                    } else {
                        // Further compress if needed
                        this.compressImage(canvas, maxSizeKB).then(resolve).catch(reject);
                    }
                }, 'image/jpeg', 0.8);
            };

            img.onerror = reject;
            img.src = URL.createObjectURL(file);
        });
    }

    compressImage(canvas, maxSizeKB) {
        return new Promise((resolve) => {
            let quality = 0.8;
            const compress = () => {
                canvas.toBlob((blob) => {
                    if (blob.size <= maxSizeKB * 1024 || quality <= 0.1) {
                        resolve(blob);
                    } else {
                        quality -= 0.1;
                        compress();
                    }
                }, 'image/jpeg', quality);
            };
            compress();
        });
    }

    // Offline support with service worker
    registerServiceWorker() {
        if ('serviceWorker' in navigator) {
            navigator.serviceWorker.register('/sw.js')
                .then(registration => {
                    console.log('Service Worker registered:', registration);
                    
                    // Detect updates to service worker and reload
                    registration.addEventListener('updatefound', () => {
                        const newWorker = registration.installing;
                        newWorker.addEventListener('statechange', () => {
                            if (newWorker.state === 'installed' && navigator.serviceWorker.controller) {
                                console.log('New Service Worker version available, reloading...');
                                window.location.reload();
                            }
                        });
                    });
                })
                .catch(error => {
                    console.warn('Service Worker registration failed:', error);
                });
        }
    }

    // Performance monitoring
    trackPerformance(metric, value) {
        if ('performance' in window) {
            performance.mark(`${metric}-start`);
            setTimeout(() => {
                performance.mark(`${metric}-end`);
                performance.measure(metric, `${metric}-start`, `${metric}-end`);
                const duration = performance.getEntriesByName(metric)[0].duration;
                console.log(`Performance: ${metric} took ${duration.toFixed(2)}ms`);
            }, 0);
        }
    }

    // Cache management
    isCached(endpoint) {
        const cached = this.cache.get(endpoint);
        const expiry = this.cacheExpiry.get(endpoint);
        return cached && expiry && Date.now() < expiry;
    }

    setCache(endpoint, data) {
        this.cache.set(endpoint, data);
        this.cacheExpiry.set(endpoint, Date.now() + this.CACHE_DURATION);
    }

    clearCache(pattern = null) {
        if (pattern) {
            for (const key of this.cache.keys()) {
                if (key.includes(pattern)) {
                    this.cache.delete(key);
                    this.cacheExpiry.delete(key);
                }
            }
        } else {
            this.cache.clear();
            this.cacheExpiry.clear();
        }
    }

    // Retry logic with exponential backoff
    async fetchWithRetry(endpoint, options, retries = 3) {
        try {
            return await fetch(`${this.baseURL}${endpoint}`, options);
        } catch (error) {
            if (retries > 0) {
                await new Promise(resolve => setTimeout(resolve, Math.pow(2, 4 - retries) * 1000));
                return this.fetchWithRetry(endpoint, options, retries - 1);
            }
            throw error;
        }
    }

    getHeaders() {
        return {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${localStorage.getItem('qc_token')}`,
            'X-Client-Version': '2.0.0'
        };
    }

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

    updateDashboardUI(data) {
        // Update UI without full refresh
        const event = new CustomEvent('dashboardUpdate', { detail: data });
        document.dispatchEvent(event);
    }
}

// Initialize optimized API client
window.OptimizedAPI = new OptimizedAPI();

// Auto-register service worker
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        window.OptimizedAPI.registerServiceWorker();
    });
} else {
    window.OptimizedAPI.registerServiceWorker();
}