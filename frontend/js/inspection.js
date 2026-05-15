/**
 * QC Central Kitchen - Inspection Controller
 * Uses real backend data only. Empty datasets render empty states.
 */

const Inspection = {
    async init() {
        this.bindPhotoValidation();
        await this.loadAll();
    },

    async loadAll() {
        this.setLoading();
        try {
            const [summary, batches, products, submissions] = await Promise.all([
                API.get('/inspection/summary'),
                API.get('/inspection/active-batches'),
                API.get('/inspection/product-shortcuts'),
                API.get('/inspection/recent-submissions'),
            ]);
            this.renderSummary(summary.data || {});
            this.renderBatches(batches.data || []);
            this.renderProducts(products.data || []);
            this.renderSubmissions(submissions.data || []);
            if (window.lucide) lucide.createIcons();
        } catch (error) {
            this.renderError(error);
        }
    },

    setLoading() {
        ['inspectionPass', 'inspectionHold', 'inspectionActive'].forEach(id => {
            const el = document.getElementById(id);
            if (el) el.textContent = '...';
        });
        this.setHtml('activeBatchList', '<div class="skeleton skeleton-card"></div>');
        this.setHtml('productGrid', '<div class="skeleton skeleton-card"></div>');
        this.setHtml('recentSubmissionList', '<div class="skeleton skeleton-card"></div>');
    },

    renderSummary(data) {
        this.text('inspectionPass', data.pass ?? 0);
        this.text('inspectionHold', data.hold_pending ?? 0);
        this.text('inspectionActive', data.active_batches ?? 0);
    },

    renderBatches(rows) {
        const container = document.getElementById('activeBatchList');
        if (!container) return;
        if (!rows.length) {
            container.innerHTML = this.emptyState('No inspection data yet', 'Create first batch to start QC inspection activity.', true);
            return;
        }
        container.innerHTML = rows.map(batch => `
            <div class="alert-card" onclick="window.location.href='batch_detail.html?id=${batch.id}'">
                <div class="alert-icon"><i data-lucide="package"></i></div>
                <div class="alert-info">
                    <h4>${this.escape(batch.batch_code || '-')}</h4>
                    <p>${this.escape(batch.product_name || 'Unknown product')}</p>
                </div>
                <div class="alert-status ${this.statusClass(batch.status)}">${this.escape(batch.status || 'pending')}</div>
            </div>
        `).join('');
    },

    renderProducts(rows) {
        const container = document.getElementById('productGrid');
        if (!container) return;
        if (!rows.length) {
            container.innerHTML = this.emptyState('No products available yet', 'Product shortcuts appear after product master data is added.');
            return;
        }
        container.innerHTML = rows.map(product => `
            <button class="metric-card" type="button" style="padding:12px;text-align:left;cursor:pointer;border:0" onclick="window.location.href='new_batch.html'">
                <div style="font-size:11px;color:var(--primary);font-weight:800;">${this.escape(product.product_code || '-')}</div>
                <div style="font-size:12px;font-weight:600;margin-top:4px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">
                    ${this.escape(product.product_name || 'Unnamed product')}
                </div>
            </button>
        `).join('');
    },

    renderSubmissions(rows) {
        const container = document.getElementById('recentSubmissionList');
        if (!container) return;
        if (!rows.length) {
            container.innerHTML = this.emptyState('No recent submissions', 'Data will appear after staff submit QC activity.');
            return;
        }
        container.innerHTML = rows.map(row => `
            <div class="alert-card">
                <div class="alert-icon"><i data-lucide="${row.photo_url ? 'image' : 'clipboard-check'}"></i></div>
                <div class="alert-info">
                    <h4>${this.escape(row.batch_code || '-')}</h4>
                    <p>${this.escape(row.product_name || 'QC submission')}${row.created_at ? ` - ${this.time(row.created_at)}` : ''}</p>
                </div>
                <span class="status-badge ${this.statusClass(row.status)}">${this.escape(row.status || 'pending')}</span>
            </div>
        `).join('');
    },

    renderError(error) {
        const retry = '<button class="btn-primary" type="button" onclick="Inspection.loadAll()">Retry</button>';
        const html = `<div class="empty-state"><i data-lucide="database"></i><h3>Unable to load data</h3><p>${this.escape(error.message || 'Retry')}</p>${retry}</div>`;
        this.setHtml('activeBatchList', html);
        this.setHtml('productGrid', html);
        this.setHtml('recentSubmissionList', html);
        this.renderSummary({ pass: 0, hold_pending: 0, active_batches: 0 });
        if (window.lucide) lucide.createIcons();
    },

    bindPhotoValidation() {
        const input = document.getElementById('qcPhoto');
        const zone = document.querySelector('.upload-zone');
        if (!input || !zone) return;
        input.addEventListener('change', event => {
            const files = Array.from(event.target.files || []);
            if (!files.length) return;
            try {
                files.forEach(file => API.validatePhoto(file));
                const suffix = files.length > 1 ? ` (${files.length})` : '';
                zone.querySelector('span').textContent = `Upload berhasil dipilih${suffix}`;
            } catch (err) {
                alert(err.message || 'Upload gagal');
                input.value = '';
                zone.querySelector('span').textContent = 'Ambil foto evidence produk, suhu, atau barcode.';
            }
        });
    },

    emptyState(title, message, includeButton = false) {
        return `
            <div class="empty-state">
                <i data-lucide="database"></i>
                <h3>${title}</h3>
                <p>${message}</p>
                ${includeButton ? '<button class="btn-primary" type="button" onclick="window.location.href=\'new_batch.html\'">Create first batch</button>' : ''}
            </div>
        `;
    },

    statusClass(status) {
        return { pass: 'success', warning: 'warning', hold: 'warning', pending: 'muted', fail: 'danger', failed: 'danger' }[String(status || '').toLowerCase()] || 'muted';
    },

    time(value) {
        try {
            return new Date(value).toLocaleString('id-ID', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' });
        } catch {
            return '';
        }
    },

    text(id, value) {
        const el = document.getElementById(id);
        if (el) el.textContent = value;
    },

    setHtml(id, value) {
        const el = document.getElementById(id);
        if (el) el.innerHTML = value;
    },

    escape(value) {
        return String(value ?? '').replace(/[&<>"']/g, char => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[char]));
    }
};
