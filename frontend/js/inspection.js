/**
 * Simple mobile QC check.
 * One SKU/barcode submission creates one qc_report.
 */

const Inspection = {
    selectedStatus: 'pass',
    selectedStage: 'cooking_check',
    selectedBatch: null,
    products: [],
    selectedProduct: null,
    manualMode: false,
    forceNewBatch: false,

    async init() {
        await this.loadProducts();
        this.bindProductSearch();
        this.bindManualSku();
        this.bindNotesToggle();
        this.bindStatus();
        this.bindStage();
        this.bindSkuLookup();
        this.bindBatchNew();
        this.bindCompletionState();
        this.bindPhotoValidation();
        this.bindSubmit();
        this.updateStageFields();
        this.updateSubmitState();
    },

    async loadProducts() {
        try {
            const response = await API.get('/inspection/products');
            this.products = response?.data || [];
            this.renderProductPrompt('Ketik minimal 2 huruf.');
        } catch (error) {
            this.products = [];
            this.message('Gagal memuat produk. Gunakan input manual jika perlu.', true);
            this.renderProductPrompt('Produk kosong. Gunakan input manual jika perlu.');
        }
    },

    bindProductSearch() {
        const input = document.getElementById('productSearch');
        if (!input) return;
        input.addEventListener('input', () => {
            this.selectedProduct = null;
            this.updateSelectedProductCard();
            const query = input.value.trim().toLowerCase();
            if (query.length < 2) {
                this.renderProductPrompt('Ketik minimal 2 huruf.');
                this.updateSubmitState();
                return;
            }
            const matches = this.products.filter(item => {
                const code = String(item.product_code || '').toLowerCase();
                const name = String(item.product_name || '').toLowerCase();
                return code.includes(query) || name.includes(query);
            });
            this.renderProductOptions(matches.slice(0, 5));
            this.updateSubmitState();
        });
    },

    bindManualSku() {
        const button = document.getElementById('manualSkuToggle');
        if (!button) return;
        button.addEventListener('click', () => {
            this.manualMode = !this.manualMode;
            this.selectedProduct = null;
            this.selectedBatch = null;
            this.forceNewBatch = false;
            const wrap = document.getElementById('manualSkuWrap');
            if (wrap) wrap.hidden = !this.manualMode;
            button.textContent = this.manualMode ? 'Pilih dari daftar produk' : 'Input Manual';
            this.updateSelectedProductCard();
            this.renderActiveBatches([]);
            const productMessage = document.getElementById('productDetected');
            if (productMessage) productMessage.textContent = this.manualMode
                ? 'Mode manual aktif.'
                : 'Pilih produk terlebih dahulu.';
            this.renderProductPrompt(this.manualMode ? '' : 'Ketik minimal 2 huruf.');
            this.updateSubmitState();
        });
    },

    bindNotesToggle() {
        const button = document.getElementById('notesToggle');
        const wrap = document.getElementById('notesWrap');
        if (!button || !wrap) return;
        button.addEventListener('click', () => {
            wrap.hidden = !wrap.hidden;
            button.textContent = wrap.hidden ? '+ Tambah Catatan' : '- Sembunyikan Catatan';
            if (!wrap.hidden) document.getElementById('qcNotes')?.focus();
        });
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
                this.updateSubmitState();
            });
        });
    },

    bindSkuLookup() {
        const input = document.getElementById('qcSku');
        if (!input) return;
        let timer = null;
        input.addEventListener('input', () => {
            clearTimeout(timer);
            this.updateSubmitState();
            timer = setTimeout(() => {
                if (this.manualMode) this.lookupActiveBatches(input.value.trim());
            }, 400);
        });
    },

    bindBatchNew() {
        const button = document.getElementById('createNewBatchBtn');
        if (!button) return;
        button.addEventListener('click', () => {
            this.selectedBatch = null;
            this.forceNewBatch = true;
            document.querySelectorAll('.batch-choice').forEach(item => item.classList.remove('active'));
            button.textContent = 'Batch baru akan dibuat';
        });
    },

    bindCompletionState() {
        ['productSearch', 'qcSku', 'qcTemp'].forEach(id => {
            const input = document.getElementById(id);
            if (input) input.addEventListener('input', () => this.updateSubmitState());
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
                this.renderPhotoPreview(id, file);
            } catch (err) {
                this.message(err.message || 'Upload gagal', true);
                input.value = '';
                zone.querySelector('span').textContent = 'Opsional, maksimal 10MB.';
                this.clearPhotoPreview(id);
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
        const manualSku = document.getElementById('qcSku')?.value?.trim();
        const sku = this.selectedProduct?.product_code || manualSku;
        const notes = document.getElementById('qcNotes')?.value?.trim();
        const temperature = document.getElementById('qcTemp')?.value;
        const cookingPhoto = (document.getElementById('cookingPhoto')?.files || [])[0];
        const barcodePhoto = (document.getElementById('barcodePhoto')?.files || [])[0];
        const labelPhoto = (document.getElementById('labelPhoto')?.files || [])[0];
        if (!this.selectedProduct && !manualSku) {
            this.message('Pilih produk atau masukkan SKU manual terlebih dahulu', true);
            return;
        }
        if (this.selectedStage === 'cooking_check' && !temperature) {
            this.message('Suhu masak wajib diisi.', true);
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
        if (this.selectedProduct?.id) formData.append('product_id', this.selectedProduct.id);
        formData.append('product_name', this.selectedProduct?.product_name || 'Manual SKU');
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
            ['productSearch', 'qcSku', 'qcTemp', 'qcNotes'].forEach(id => {
                localStorage.removeItem(id);
                const el = document.getElementById(id);
                if (el) el.value = '';
            });
            ['cookingPhoto', 'barcodePhoto', 'labelPhoto'].forEach(id => {
                const input = document.getElementById(id);
                if (input) input.value = '';
                this.clearPhotoPreview(id);
            });
            document.querySelectorAll('.upload-zone span').forEach(item => {
                item.textContent = 'Opsional, maksimal 10MB.';
            });
            this.selectedBatch = null;
            this.selectedProduct = null;
            this.manualMode = false;
            this.forceNewBatch = false;
            this.updateSelectedProductCard();
            this.renderActiveBatches([]);
            this.renderProductPrompt('Ketik minimal 2 huruf.');
            this.updateSubmitState();
            this.message('QC berhasil disimpan', false);
            if (typeof this.loadRecentSubmissions === 'function') this.loadRecentSubmissions();
        } catch (error) {
            this.message(`Gagal menyimpan QC: ${error.message || 'server tidak merespons'}`, true);
        } finally {
            button.disabled = false;
            button.innerHTML = original;
        }
    },

    updateSubmitState() {
        const button = document.getElementById('submitQcBtn');
        if (!button) return;
        const manualSku = document.getElementById('qcSku')?.value?.trim();
        const temperature = document.getElementById('qcTemp')?.value;
        const hasProduct = Boolean(this.selectedProduct || manualSku);
        const hasStageData = this.selectedStage !== 'cooking_check' || Boolean(temperature);
        button.disabled = !(hasProduct && hasStageData);
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
            if (productEl) productEl.textContent = 'Isi SKU untuk mencari batch.';
            this.renderActiveBatches([]);
            return;
        }
        try {
            const response = await API.get(`/inspection/batches/active?sku=${encodeURIComponent(sku)}`);
            const batches = response?.data?.active_batches || [];
            if (productEl) {
                productEl.textContent = batches.length
                    ? `Ditemukan ${batches.length} batch.`
                    : 'Produk tidak ditemukan atau belum ada batch aktif.';
            }
            this.renderActiveBatches(batches);
        } catch (error) {
            if (productEl) productEl.textContent = 'Gagal mengecek batch. Tetap bisa submit sebagai batch baru.';
            this.renderActiveBatches([]);
        }
    },

    renderProductOptions(products) {
        const list = document.getElementById('productPickerList');
        if (!list) return;
        if (!products.length) {
            list.innerHTML = '<div class="simple-qc-message product-empty-state">Produk tidak ditemukan. Gunakan input manual jika perlu.</div>';
            return;
        }
        list.innerHTML = '';
        products.forEach(product => {
            const button = document.createElement('button');
            button.type = 'button';
            button.className = 'product-picker-option';
            button.innerHTML = `
                <strong>${this.escapeHtml(product.product_code || '-')}</strong>
                <span>${this.escapeHtml(product.product_name || '-')}</span>
            `;
            button.addEventListener('click', () => this.selectProduct(product));
            list.appendChild(button);
        });
    },

    renderProductPrompt(text) {
        const list = document.getElementById('productPickerList');
        if (!list) return;
        list.innerHTML = text ? `<div class="simple-qc-message product-empty-state">${this.escapeHtml(text)}</div>` : '';
    },

    selectProduct(product) {
        this.selectedProduct = product;
        this.manualMode = false;
        this.selectedBatch = null;
        this.forceNewBatch = false;
        const manualWrap = document.getElementById('manualSkuWrap');
        const manualButton = document.getElementById('manualSkuToggle');
        const search = document.getElementById('productSearch');
        const manualInput = document.getElementById('qcSku');
        if (manualWrap) manualWrap.hidden = true;
        if (manualButton) manualButton.textContent = 'Input Manual';
        if (search) search.value = `${product.product_code || ''} - ${product.product_name || ''}`.trim();
        if (manualInput) manualInput.value = '';
        this.updateSelectedProductCard();
        this.renderProductPrompt('');
        this.lookupActiveBatches(product.product_code);
        this.updateSubmitState();
        document.querySelectorAll('.product-picker-option').forEach(item => {
            item.classList.toggle('active', item.textContent.includes(product.product_code || '__none__'));
        });
    },

    updateSelectedProductCard() {
        const card = document.getElementById('selectedProductCard');
        if (!card) return;
        if (!this.selectedProduct) {
            card.hidden = true;
            card.innerHTML = '';
            return;
        }
        card.hidden = false;
        card.innerHTML = `
            <div>
                <small>Produk Terpilih</small>
                <strong>${this.escapeHtml(this.selectedProduct.product_code || '-')}</strong>
                <span>${this.escapeHtml(this.selectedProduct.product_name || '-')}</span>
            </div>
            <button class="btn-secondary change-product-btn" type="button">Ganti Produk</button>
        `;
        card.querySelector('.change-product-btn')?.addEventListener('click', () => {
            this.selectedProduct = null;
            this.selectedBatch = null;
            this.forceNewBatch = false;
            document.getElementById('productSearch')?.focus();
            this.updateSelectedProductCard();
            this.renderActiveBatches([]);
            this.renderProductPrompt('Ketik minimal 2 huruf.');
            this.updateSubmitState();
        });
    },

    renderActiveBatches(batches) {
        const panel = document.getElementById('activeBatchPanel');
        const list = document.getElementById('activeBatchList');
        const empty = document.getElementById('activeBatchEmpty');
        if (!panel || !list) return;
        const hasContext = Boolean(this.selectedProduct || this.manualMode);
        panel.hidden = !hasContext;
        if (empty) empty.hidden = Boolean(batches.length);
        list.innerHTML = '';
        batches.forEach(batch => {
            const button = document.createElement('button');
            button.type = 'button';
            button.className = 'batch-choice';
            button.innerHTML = `
                <strong>${this.escapeHtml(batch.batch_code || '-')}</strong>
                <small>Tahap Terakhir: ${this.stageLabel(batch.last_stage)} | Status: ${this.escapeHtml(String(batch.last_status || '-').toUpperCase())}</small>
                <span>Lanjutkan Batch</span>
            `;
            button.addEventListener('click', () => {
                this.selectedBatch = batch;
                this.forceNewBatch = false;
                document.querySelectorAll('.batch-choice').forEach(item => item.classList.toggle('active', item === button));
                const newBtn = document.getElementById('createNewBatchBtn');
                if (newBtn) newBtn.textContent = 'Buat Batch Baru';
            });
            list.appendChild(button);
        });
    },

    renderPhotoPreview(inputId, file) {
        const preview = document.getElementById(`${inputId}Preview`);
        if (!preview) return;
        const url = URL.createObjectURL(file);
        preview.hidden = false;
        preview.innerHTML = `
            <img src="${url}" alt="">
            <span>${this.escapeHtml(file.name)}</span>
            <button type="button" aria-label="Hapus foto">Hapus</button>
        `;
        preview.querySelector('button')?.addEventListener('click', event => {
            event.stopPropagation();
            const input = document.getElementById(inputId);
            if (input) input.value = '';
            this.clearPhotoPreview(inputId);
            const zone = input?.closest('.upload-zone');
            if (zone) zone.querySelector('span').textContent = 'Opsional, maksimal 10MB.';
        });
    },

    clearPhotoPreview(inputId) {
        const preview = document.getElementById(`${inputId}Preview`);
        if (!preview) return;
        preview.hidden = true;
        preview.innerHTML = '';
    },

    stageLabel(value) {
        if (value === 'cooking_check') return 'Cek Masakan';
        if (value === 'final_check') return 'Cek Label Akhir';
        return this.escapeHtml(value || '-');
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
