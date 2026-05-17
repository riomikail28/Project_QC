/**
 * Simple mobile QC check.
 * One SKU/barcode submission creates one qc_report.
 */

const Inspection = {
    selectedStatus: 'pass',
    selectedStage: 'cooking_check',
    selectedBatch: null,
    forceNewBatch: false,

    async init() {
        this.bindStatus();
        this.bindStage();
        this.bindSkuLookup();
        this.bindBatchNew();
        this.bindPhotoValidation();
        this.bindSubmit();
        this.updateStageFields();
    },

    bindStatus() {
        document.querySelectorAll('.qc-status-option').forEach(button => {
            button.addEventListener('click', () => {
                this.selectedStatus = button.dataset.status || 'pass';
                document.querySelectorAll('.qc-status-option').forEach(item => {
                    item.classList.toggle('active', item === button);
                });
            });
        });
    },

    bindStage() {
        document.querySelectorAll('.qc-stage-option').forEach(button => {
            button.addEventListener('click', () => {
                this.selectedStage = button.dataset.stage || 'cooking_check';
                document.querySelectorAll('.qc-stage-option').forEach(item => {
                    item.classList.toggle('active', item === button);
                });
                this.updateStageFields();
            });
        });
    },

    bindSkuLookup() {
        const input = document.getElementById('qcSku');
        if (!input) return;
        let timer = null;
        input.addEventListener('input', () => {
            clearTimeout(timer);
            timer = setTimeout(() => this.lookupActiveBatches(input.value.trim()), 400);
        });
        if (input.value.trim()) this.lookupActiveBatches(input.value.trim());
    },

    bindBatchNew() {
        const button = document.getElementById('createNewBatchBtn');
        if (!button) return;
        button.addEventListener('click', () => {
            this.selectedBatch = null;
            this.forceNewBatch = true;
            document.querySelectorAll('.batch-choice').forEach(item => item.classList.remove('active'));
            button.textContent = 'Batch baru akan dibuat saat submit';
        });
    },

    updateStageFields() {
        const cooking = document.getElementById('cookingFields');
        const final = document.getElementById('finalFields');
        if (cooking) cooking.hidden = this.selectedStage !== 'cooking_check';
        if (final) final.hidden = this.selectedStage !== 'final_check';
    },

    bindPhotoValidation() {
        ['cookingPhoto', 'barcodePhoto', 'labelPhoto'].forEach(id => {
            const input = document.getElementById(id);
            if (!input) return;
            const zone = input.closest('.upload-zone');
            input.addEventListener('change', event => {
                const file = (event.target.files || [])[0];
                if (!file) return;
                try {
                    API.validatePhoto(file);
                    zone.querySelector('span').textContent = file.name;
                } catch (err) {
                    this.message(err.message || 'Upload gagal', true);
                    input.value = '';
                    zone.querySelector('span').textContent = 'Direkomendasikan, JPG/PNG/WEBP maksimal 10MB.';
                }
            });
        });
    },

    bindSubmit() {
        const button = document.getElementById('submitQcBtn');
        if (!button) return;
        button.addEventListener('click', () => this.submitQc(button));
    },

    async submitQc(button) {
        const original = button.innerHTML;
        const sku = document.getElementById('qcSku')?.value?.trim();
        const notes = document.getElementById('qcNotes')?.value?.trim();
        const temperature = document.getElementById('qcTemp')?.value;
        const cookingPhoto = (document.getElementById('cookingPhoto')?.files || [])[0];
        const barcodePhoto = (document.getElementById('barcodePhoto')?.files || [])[0];
        const labelPhoto = (document.getElementById('labelPhoto')?.files || [])[0];
        if (!sku) {
            this.message('SKU atau barcode wajib diisi.', true);
            return;
        }
        if (this.selectedStage === 'cooking_check' && !temperature) {
            this.message('Suhu masak wajib diisi untuk Cooking Check.', true);
            return;
        }
        try {
            [cookingPhoto, barcodePhoto, labelPhoto].filter(Boolean).forEach(file => API.validatePhoto(file));
        } catch (err) {
            this.message(err.message || 'Upload gagal', true);
            return;
        }

        const user = Auth.user() || {};
        const formData = new FormData();
        formData.append('sku_code', sku);
        formData.append('barcode', sku);
        formData.append('qc_stage', this.selectedStage);
        formData.append('qc_status', this.selectedStatus);
        formData.append('notes', notes || '');
        if (this.selectedStage === 'cooking_check') formData.append('temperature', temperature || '');
        if (this.selectedBatch?.id) formData.append('batch_id', this.selectedBatch.id);
        if (this.selectedBatch?.batch_code) formData.append('batch_code', this.selectedBatch.batch_code);
        if (this.forceNewBatch) formData.append('force_new_batch', '1');
        formData.append('staff_id', user.id || user.user_id || user.sub || '');
        formData.append('staff_name', user.full_name || user.name || user.username || '');
        if (cookingPhoto) formData.append('cooking_photo', cookingPhoto);
        if (barcodePhoto) formData.append('barcode_photo', barcodePhoto);
        if (labelPhoto) formData.append('label_photo', labelPhoto);

        try {
            button.disabled = true;
            button.innerHTML = '<i class="fas fa-spinner fa-spin"></i>Menyimpan...';
            const response = await API.upload('/inspection/submit', formData);
            if (!response.success) throw new Error(response.message || response.error || 'Submit gagal');
            ['qcSku', 'qcTemp', 'qcNotes'].forEach(id => {
                localStorage.removeItem(id);
                const el = document.getElementById(id);
                if (el) el.value = '';
            });
            ['cookingPhoto', 'barcodePhoto', 'labelPhoto'].forEach(id => {
                const input = document.getElementById(id);
                if (input) input.value = '';
            });
            document.querySelectorAll('.upload-zone span').forEach(item => {
                item.textContent = 'Direkomendasikan, JPG/PNG/WEBP maksimal 10MB.';
            });
            this.selectedBatch = null;
            this.forceNewBatch = false;
            this.renderActiveBatches([]);
            this.message('QC Check berhasil dikirim', false);
            if (typeof this.loadRecentSubmissions === 'function') this.loadRecentSubmissions();
        } catch (error) {
            this.message(`Gagal menyimpan QC check: ${error.message || 'server tidak merespons'}`, true);
        } finally {
            button.disabled = false;
            button.innerHTML = original;
        }
    },

    message(text, isError = false) {
        const el = document.getElementById('qcSubmitMessage');
        if (!el) return;
        el.textContent = text;
        el.classList.toggle('error', isError);
    },

    async lookupActiveBatches(sku) {
        const productEl = document.getElementById('productDetected');
        if (!sku) {
            if (productEl) productEl.textContent = 'Isi SKU untuk mencari batch aktif.';
            this.renderActiveBatches([]);
            return;
        }
        try {
            const response = await API.get(`/inspection/batches/active?sku=${encodeURIComponent(sku)}`);
            const batches = response?.data?.active_batches || [];
            if (productEl) {
                productEl.textContent = batches.length
                    ? `Ditemukan ${batches.length} batch aktif untuk SKU ini.`
                    : 'Produk tidak ditemukan atau belum ada batch aktif. Tetap bisa lanjut sebagai SKU manual.';
            }
            this.renderActiveBatches(batches);
        } catch (error) {
            if (productEl) productEl.textContent = 'Gagal mengecek batch aktif. Tetap bisa submit sebagai batch baru.';
            this.renderActiveBatches([]);
        }
    },

    renderActiveBatches(batches) {
        const panel = document.getElementById('activeBatchPanel');
        const list = document.getElementById('activeBatchList');
        if (!panel || !list) return;
        panel.hidden = !batches.length;
        list.innerHTML = '';
        batches.forEach(batch => {
            const button = document.createElement('button');
            button.type = 'button';
            button.className = 'batch-choice';
            button.innerHTML = `
                <strong>${this.escapeHtml(batch.batch_code || '-')}</strong>
                <span>${this.escapeHtml(batch.product_name || '-')}</span>
                <small>Stage terakhir: ${this.escapeHtml(batch.last_stage || '-')} | Status: ${this.escapeHtml(batch.last_status || '-')}</small>
            `;
            button.addEventListener('click', () => {
                this.selectedBatch = batch;
                this.forceNewBatch = false;
                document.querySelectorAll('.batch-choice').forEach(item => item.classList.toggle('active', item === button));
                const newBtn = document.getElementById('createNewBatchBtn');
                if (newBtn) newBtn.textContent = 'Buat Batch Baru Saat Submit';
            });
            list.appendChild(button);
        });
    },

    escapeHtml(value) {
        return String(value ?? '').replace(/[&<>"']/g, char => ({
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            '"': '&quot;',
            "'": '&#39;'
        }[char]));
    }
};
