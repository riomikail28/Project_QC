/**
 * QC Central Kitchen - Inspection Controller
 * Uses real backend data only. Empty datasets render empty states.
 */

const Inspection = {
    async init() {
        this.bindPhotoValidation();
        this.bindSubmit();
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
            container.innerHTML = this.emptyState('Belum ada batch aktif', 'Tambahkan batch produksi pertama untuk mulai QC inspection.', 'Tambah Batch', 'new_batch.html');
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
            container.innerHTML = this.emptyState('Belum ada product master', 'Tambahkan master produk dari admin panel agar shortcut produk tampil.', 'Tambah Produk', '/admin/#products');
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
            container.innerHTML = this.emptyState('Belum ada QC submission', 'Data akan muncul setelah staff submit QC batch pertama.', 'Submit QC Batch', 'new_batch.html');
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
        const retry = '<button class="btn-primary" type="button" onclick="Inspection.loadAll()">Muat Ulang</button>';
        const html = `<div class="empty-state"><i data-lucide="database"></i><h3>Data inspection belum tersedia</h3><p>${this.escape(error.message || 'Coba muat ulang data production.')}</p>${retry}</div>`;
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

    bindSubmit() {
        const button = document.getElementById('submitQcBtn');
        if (!button) return;
        button.addEventListener('click', () => this.submitQc(button));
    },

    async submitQc(button) {
        const original = button.innerHTML;
        const barcode = document.getElementById('qcBarcode')?.value?.trim();
        const temperature = document.getElementById('qcTemp')?.value;
        const ccpStage = document.getElementById('qcStage')?.value;
        const files = Array.from(document.getElementById('qcPhoto')?.files || []);
        if (!barcode) {
            alert('Barcode batch wajib diisi.');
            return;
        }
        try {
            files.forEach(file => API.validatePhoto(file));
        } catch (err) {
            alert(err.message || 'Upload gagal');
            return;
        }

        const user = Auth.user() || {};
        const formData = new FormData();
        formData.append('barcode', barcode);
        formData.append('batch_code', barcode);
        formData.append('temperature', temperature || '');
        formData.append('ccp_stage', ccpStage || '');
        formData.append('qc_status', this.deriveStatus(temperature));
        formData.append('staff_id', user.id || user.user_id || user.sub || '');
        formData.append('staff_name', user.full_name || user.name || user.username || '');
        files.forEach(file => formData.append('photo', file));

        try {
            button.disabled = true;
            button.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Menyimpan...';
            const response = await API.upload('/inspection/submit', formData);
            if (!response.success) throw new Error(response.message || response.error || 'Submit gagal');
            ['qcBarcode', 'qcTemp', 'qcStage'].forEach(id => localStorage.removeItem(id));
            const photo = document.getElementById('qcPhoto');
            if (photo) photo.value = '';
            const zoneText = document.querySelector('.upload-zone span');
            if (zoneText) zoneText.textContent = 'Ambil foto evidence produk, suhu, atau barcode.';
            alert('QC inspection tersimpan.');
            await this.loadAll();
        } catch (error) {
            alert(`Submit QC gagal: ${error.message || 'server tidak merespons'}`);
        } finally {
            button.disabled = false;
            button.innerHTML = original;
        }
    },

    deriveStatus(temperature) {
        if (temperature === '' || temperature === null || temperature === undefined) return 'pending';
        const temp = Number(temperature);
        if (Number.isNaN(temp)) return 'pending';
        return temp >= -80 && temp <= 100 ? 'pass' : 'warning';
    },

    emptyState(title, message, buttonLabel = '', href = '') {
        return `
            <div class="empty-state">
                <i data-lucide="database"></i>
                <h3>${title}</h3>
                <p>${message}</p>
                ${buttonLabel ? `<button class="btn-primary" type="button" onclick="window.location.href='${href}'">${buttonLabel}</button>` : ''}
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
