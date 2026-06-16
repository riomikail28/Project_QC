/**
 * QC Central Kitchen — Utilities
 */

const Utils = {
    formatDate(dateStr) {
        if (!dateStr) return '-';
        const date = new Date(dateStr);
        return date.toLocaleDateString('id-ID', {
            day: '2-digit',
            month: 'short',
            year: 'numeric'
        });
    },

    formatTime(dateStr) {
        if (!dateStr) return '-';
        const date = new Date(dateStr);
        return date.toLocaleTimeString('id-ID', {
            hour: '2-digit',
            minute: '2-digit'
        });
    },

    formatTemp(temp) {
        if (temp === null || temp === undefined) return '-';
        return `${parseFloat(temp).toFixed(1)}°C`;
    },

    getStatusColor(status) {
        switch (status?.toUpperCase()) {
            case 'PASS': return '#22c55e';
            case 'WARNING': return '#f59e0b';
            case 'FAIL': return '#ef4444';
            default: return '#64748b';
        }
    },

    thumbnailUrl(url) {
        const raw = String(url || '').split(';')[0].trim();
        if (!raw) return '';
        if (!/^https?:\/\//i.test(raw)) return raw;
        const separator = raw.includes('?') ? '&' : '?';
        return `${raw}${separator}width=180&quality=65`;
    }
};
