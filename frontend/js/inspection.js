/**
 * Simple mobile QC check.
 * One SKU/barcode submission creates one qc_report.
 *
 * Product Picker is the primary mode.
 * Manual SKU entry is only a fallback when a product is not registered.
 * Form fields appear progressively to minimize scroll on mobile.
 */

const Inspection = {
    selectedStatus: null,
    selectedStage: null,
    selectedBatch: null,
    products: [],
    selectedProduct: null,
    skuCards: [],
    skuBatchMap: {},
    manualMode: false,
    forceNewBatch: false,
    activeInspection: null,
    lastInspection: null,
    recheckParentInspection: null,

    async init() {
        await this.loadProducts();
        this.bindSkuWorkspace();
        this.bindProductSearch();
        this.bindManualSku();
        this.bindNotesToggle();
        this.bindStatus();
        this.bindStage();
        this.bindSkuLookup();
        this.bindBatchNew();
        this.bindQcHistoryActions();
        this.bindCompletionState();
        this.bindPhotoValidation();
        this.bindSubmit();
        this.updateStageFields();
        this.updateSubmitState();
        this.updateProgressiveFields();
        this.loadRecentSubmissions();
        this.renderSkuCards();
    },

    bindSkuWorkspace() {
        document.getElementById('addSkuBtn')?.addEventListener('click', () => this.openSkuSearch());
        document.getElementById('qcSheetCloseBtn')?.addEventListener('click', () => this.closeQcSheet());
        document.getElementById('qcCancelBtn')?.addEventListener('click', () => this.closeQcSheet());
        document.getElementById('qcFormBackdrop')?.addEventListener('click', () => this.closeQcSheet());
        document.addEventListener('keydown', event => {
            if (event.key === 'Escape' && !document.getElementById('qcFormSheet')?.hidden) {
                this.closeQcSheet();
            }
        });
    },

    openSkuSearch() {
        const panel = document.getElementById('skuSearchPanel');
        if (panel) panel.hidden = false;
        const helpEl = document.getElementById('productSearchHelp');
        if (helpEl) {
            helpEl.textContent = 'Ketik minimal 2 huruf untuk mencari produk.';
            helpEl.hidden = false;
        }
        document.getElementById('productSearch')?.focus();
    },

    closeSkuSearch() {
        const panel = document.getElementById('skuSearchPanel');
        if (panel) panel.hidden = true;
        this.clearProductList();
    },

    /* ═══════════════════════════════════════════════
       Data Loading
       ═══════════════════════════════════════════════ */

    async loadProducts() {
        try {
            const response = await API.get('/inspection/products');
            this.products = response?.data || [];
        } catch (error) {
            this.products = [];
            this.message('Gagal memuat produk. Gunakan input manual jika perlu.', true);
        }
    },

    /* ═══════════════════════════════════════════════
       Product Search Binding
       ═══════════════════════════════════════════════ */

    bindProductSearch() {
        const input = document.getElementById('productSearch');
        if (!input) return;
        let debounce = null;
        input.addEventListener('input', () => {
            clearTimeout(debounce);
            debounce = setTimeout(() => {
                this.selectedProduct = null;
                this.updateSelectedProductCard();
                this.updateProgressiveFields();
                const query = input.value.trim().toLowerCase();
                const helpEl = document.getElementById('productSearchHelp');
                if (query.length < 2) {
                    this.clearProductList();
                    if (helpEl) {
                        helpEl.textContent = 'Ketik minimal 2 huruf untuk mencari produk.';
                        helpEl.hidden = false;
                    }
                    this.updateSubmitState();
                    return;
                }
                if (helpEl) helpEl.hidden = true;
                const matches = this.products.filter(item => {
                    const code = String(item.product_code || '').toLowerCase();
                    const name = String(item.product_name || '').toLowerCase();
                    const barcode = String(item.barcode || '').toLowerCase();
                    return code.includes(query) || name.includes(query) || barcode.includes(query);
                });
                this.renderProductOptions(matches.slice(0, 5));
                this.updateSubmitState();
            }, 150);
        });
    },

    /* ═══════════════════════════════════════════════
       Manual SKU Fallback
       ═══════════════════════════════════════════════ */

    bindManualSku() {
        // Manual SKU toggle is now rendered dynamically inside product list
        // when no search results are found, or via the fallback button.
    },

    toggleManualMode() {
        this.manualMode = !this.manualMode;
        this.selectedProduct = null;
        this.selectedBatch = null;
        this.forceNewBatch = false;
        const wrap = document.getElementById('manualSkuWrap');
        const searchInput = document.getElementById('productSearch');
        const helpEl = document.getElementById('productSearchHelp');
        if (wrap) wrap.hidden = !this.manualMode;
        if (this.manualMode) {
            if (searchInput) searchInput.value = '';
            this.clearProductList();
            if (helpEl) helpEl.hidden = true;
            document.getElementById('qcSku')?.focus();
        } else {
            if (helpEl) {
                helpEl.textContent = 'Ketik minimal 2 huruf untuk mencari produk.';
                helpEl.hidden = false;
            }
            if (searchInput) searchInput.focus();
        }
        this.updateSelectedProductCard();
        this.renderActiveBatches([]);
        const productMessage = document.getElementById('productDetected');
        if (productMessage) productMessage.textContent = this.manualMode
            ? 'Mode input SKU manual aktif.'
            : 'Pilih produk terlebih dahulu.';
        this.updateProgressiveFields();
        this.updateSubmitState();
    },

    /* ═══════════════════════════════════════════════
       Notes Toggle
       ═══════════════════════════════════════════════ */

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

    /* ═══════════════════════════════════════════════
       Status / Stage Bindings
       ═══════════════════════════════════════════════ */

    bindStatus() {
        document.querySelectorAll('.qc-status-option').forEach(button => {
            button.addEventListener('click', () => {
                this.selectedStatus = button.dataset.status || 'pass';
                document.querySelectorAll('.qc-status-option').forEach(item => {
                    item.classList.toggle('active', item === button);
                });
                this.updateSubmitState();
                this.updateSummary();
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
                this.updateProgressiveFields();
                this.updateSubmitState();
                this.updateSummary();
            });
        });
    },

    /* ═══════════════════════════════════════════════
       SKU Lookup (manual mode)
       ═══════════════════════════════════════════════ */

    bindSkuLookup() {
        const input = document.getElementById('qcSku');
        if (!input) return;
        let timer = null;
        input.addEventListener('input', () => {
            clearTimeout(timer);
            this.updateSubmitState();
            this.updateProgressiveFields();
            timer = setTimeout(() => {
                if (this.manualMode) this.lookupActiveBatches(input.value.trim());
            }, 400);
        });
    },

    /* ═══════════════════════════════════════════════
       Batch New
       ═══════════════════════════════════════════════ */

    bindBatchNew() {
        const button = document.getElementById('createNewBatchBtn');
        if (!button) return;
        button.addEventListener('click', () => {
            this.selectedBatch = null;
            this.forceNewBatch = true;
            this.activeInspection = null;
            this.lastInspection = null;
            this.recheckParentInspection = null;
            document.querySelectorAll('.batch-choice').forEach(item => item.classList.remove('active'));
            button.textContent = 'Batch baru akan dibuat';
            this.renderQcConcurrency(null, null);
            this.updateSummary();
            this.updateSubmitState();
        });
    },

    bindQcHistoryActions() {
        document.getElementById('qcDetailBtn')?.addEventListener('click', () => {
            const item = this.activeInspection || this.lastInspection;
            if (!item) return;
            const detail = [
                `Batch: ${item.batch_code || item.batch || '-'}`,
                `Jenis: ${this.stageLabel(item.qc_stage || item.qc_type)}`,
                `Status: ${String(item.status || '-').toUpperCase()}`,
                `Staff: ${item.staff || '-'}`,
                `Waktu: ${this.formatDateTime(item.completed_at || item.created_at || item.start_time)}`,
                item.temperature ? `Suhu: ${item.temperature}` : null,
                item.notes ? `Catatan: ${item.notes}` : null,
            ].filter(Boolean).join('\n');
            window.alert(detail);
        });
        document.getElementById('qcRecheckBtn')?.addEventListener('click', () => {
            if (!this.lastInspection?.id) return;
            this.recheckParentInspection = this.lastInspection.id;
            this.activeInspection = null;
            this.message('Mode re-check aktif. Submit berikutnya akan menjadi ronde lanjutan.', false);
            this.updateSummary();
            this.updateSubmitState();
        });
    },

    /* ═══════════════════════════════════════════════
       Completion State
       ═══════════════════════════════════════════════ */

    bindCompletionState() {
        ['productSearch', 'qcSku', 'qcTemp', 'qcNotes'].forEach(id => {
            const input = document.getElementById(id);
            if (input) input.addEventListener('input', () => {
                this.updateSubmitState();
                this.updateSummary();
            });
        });
    },

    /* ═══════════════════════════════════════════════
       Stage Fields Visibility
       ═══════════════════════════════════════════════ */

    updateStageFields(hasContext = this.hasProductContext()) {
        const cooking = document.getElementById('cookingFields');
        const final = document.getElementById('finalFields');
        if (cooking) cooking.hidden = !(hasContext && this.selectedStage === 'cooking_check');
        if (final) final.hidden = !(hasContext && this.selectedStage === 'final_check');
    },

    /* ═══════════════════════════════════════════════
       Progressive Disclosure
       ═══════════════════════════════════════════════ */

    updateProgressiveFields() {
        const hasProduct = Boolean(this.selectedProduct);
        const hasContext = this.hasProductContext();

        // Show/hide stage, status, notes, and submit fields
        const stageField = document.getElementById('stageField');
        const statusField = document.getElementById('statusField');
        const notesField = document.getElementById('notesField');
        const submitBtn = document.getElementById('submitQcBtn');
        const batchPanel = document.getElementById('activeBatchPanel');

        // Search input visibility when product is selected
        const pickerField = document.getElementById('productPickerField');
        if (pickerField) pickerField.hidden = hasProduct;
        if (batchPanel && !hasContext) batchPanel.hidden = true;

        // Stage appears after product is selected
        if (stageField) stageField.hidden = !hasContext;

        // Stage-specific fields, status, notes appear after stage is selected
        const hasStage = Boolean(this.selectedStage);
        if (statusField) statusField.hidden = !(hasContext && hasStage);
        if (notesField) notesField.hidden = !(hasContext && hasStage);
        if (submitBtn) submitBtn.style.display = (hasContext && hasStage) ? '' : 'none';

        // Update stage fields visibility
        this.updateStageFields(hasContext);
    },

    /* ═══════════════════════════════════════════════
       Photo Validation & Preview
       ═══════════════════════════════════════════════ */

    bindPhotoValidation() {
        ['cookingPhoto', 'barcodePhoto', 'labelPhoto'].forEach(id => {
            const input = document.getElementById(id);
            if (!input) return;
            input.addEventListener('change', event => {
                const file = (event.target.files || [])[0];
                if (!file) return;
                try {
                    API.validatePhoto(file);
                    this.renderPhotoPreview(id, file);
                    this.updateSummary();
                } catch (err) {
                    this.message(err.message || 'Upload gagal', true);
                    input.value = '';
                    this.clearPhotoPreview(id);
                    this.updateSummary();
                }
            });
        });
    },

    /* ═══════════════════════════════════════════════
       Submit
       ═══════════════════════════════════════════════ */

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
        const ph = document.getElementById('qcPh')?.value;
        const brix = document.getElementById('qcBrix')?.value;
        const tds = document.getElementById('qcTds')?.value;
        const cookingPhoto = (document.getElementById('cookingPhoto')?.files || [])[0];
        const barcodePhoto = (document.getElementById('barcodePhoto')?.files || [])[0];
        const labelPhoto = (document.getElementById('labelPhoto')?.files || [])[0];
        if (!this.selectedProduct && !manualSku) {
            this.message('Pilih produk terlebih dahulu.', true);
            return;
        }
        if (!this.selectedStage) {
            this.message('Pilih jenis pengecekan terlebih dahulu.', true);
            return;
        }
        if (!this.selectedStatus) {
            this.message('Pilih status QC terlebih dahulu.', true);
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
        if (ph) formData.append('ph_value', ph);
        if (brix) formData.append('brix_value', brix);
        if (tds) formData.append('tds_value', tds);
        if (this.selectedBatch?.id) formData.append('batch_id', this.selectedBatch.id);
        if (this.selectedBatch?.batch_code) formData.append('batch_code', this.selectedBatch.batch_code);
        if (this.forceNewBatch) formData.append('force_new_batch', '1');
        if (this.recheckParentInspection) formData.append('parent_inspection', this.recheckParentInspection);
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
            this.rememberRecentSubmission({
                product_name: this.selectedProduct?.product_name || 'Manual SKU',
                sku_code: sku,
                batch_code: this.selectedBatch?.batch_code || 'Batch baru',
                qc_stage: this.selectedStage,
                status: this.selectedStatus,
                created_at: new Date().toISOString()
            });
            const submittedProduct = this.selectedProduct;
            ['productSearch', 'qcSku', 'qcTemp', 'qcPh', 'qcBrix', 'qcTds', 'qcNotes'].forEach(id => {
                localStorage.removeItem(id);
                const el = document.getElementById(id);
                if (el) el.value = '';
            });
            ['cookingPhoto', 'barcodePhoto', 'labelPhoto'].forEach(id => {
                const input = document.getElementById(id);
                if (input) input.value = '';
                this.clearPhotoPreview(id);
            });
            this.selectedBatch = null;
            this.selectedProduct = null;
            this.selectedStage = null;
            this.selectedStatus = null;
            this.manualMode = false;
            this.forceNewBatch = false;
            this.activeInspection = null;
            this.lastInspection = null;
            this.recheckParentInspection = null;
            // Reset stage option buttons
            document.querySelectorAll('.qc-stage-option').forEach(item => item.classList.remove('active'));
            document.querySelectorAll('.qc-status-option').forEach(item => item.classList.remove('active'));
            const manualWrap = document.getElementById('manualSkuWrap');
            if (manualWrap) manualWrap.hidden = true;
            this.updateSelectedProductCard();
            this.renderActiveBatches([]);
            this.renderQcConcurrency(null, null);
            this.clearProductList();
            const helpEl = document.getElementById('productSearchHelp');
            if (helpEl) {
                helpEl.textContent = 'Ketik minimal 2 huruf untuk mencari produk.';
                helpEl.hidden = false;
            }
            this.updateProgressiveFields();
            this.updateSubmitState();
            this.updateSummary();
            this.message('QC berhasil disimpan', false);
            this.loadRecentSubmissions();
            this.closeQcSheet();
            if (submittedProduct) await this.addSkuCard(submittedProduct);
        } catch (error) {
            this.message(`Gagal menyimpan QC: ${error.message || 'server tidak merespons'}`, true);
        } finally {
            button.innerHTML = original;
            this.updateSubmitState();
        }
    },

    /* ═══════════════════════════════════════════════
       Submit Button State
       ═══════════════════════════════════════════════ */

    updateSubmitState() {
        const button = document.getElementById('submitQcBtn');
        if (!button) return;
        const temperature = document.getElementById('qcTemp')?.value;
        const hasProduct = this.hasProductContext();
        const hasStage = Boolean(this.selectedStage);
        const hasStatus = Boolean(this.selectedStatus);
        const hasStageData = this.selectedStage !== 'cooking_check' || Boolean(temperature);
        const isLocked = Boolean(this.activeInspection);
        button.disabled = isLocked || !(hasProduct && hasStage && hasStatus && hasStageData);
        this.updateStepState();
        this.updateSummary();
    },

    /* ═══════════════════════════════════════════════
       Messages
       ═══════════════════════════════════════════════ */

    updateStepState() {
        const hasProduct = this.hasProductContext();
        const hasStage = Boolean(this.selectedStage);
        const hasStatus = Boolean(this.selectedStatus);
        const canSubmit = Boolean(hasProduct && hasStage && hasStatus && !document.getElementById('submitQcBtn')?.disabled);
        const steps = { product: hasProduct, stage: hasProduct && hasStage, result: hasProduct && hasStage && hasStatus, submit: canSubmit };
        document.querySelectorAll('.field-qc-step').forEach(step => {
            const isActive = Boolean(steps[step.dataset.step]);
            step.classList.toggle('active', isActive);
            step.classList.toggle('done', isActive && step.dataset.step !== 'submit');
        });
    },

    updateSummary() {
        const panel = document.getElementById('qcSubmitSummary');
        if (!panel) return;
        const hasContext = this.hasProductContext();
        const hasStage = Boolean(this.selectedStage);
        panel.hidden = !(hasContext && hasStage);
        if (!hasContext) return;
        const manualSku = document.getElementById('qcSku')?.value?.trim();
        const productName = this.selectedProduct?.product_name || 'Manual SKU';
        const sku = this.selectedProduct?.product_code || manualSku || '-';
        const photos = ['cookingPhoto', 'barcodePhoto', 'labelPhoto']
            .reduce((total, id) => total + (document.getElementById(id)?.files?.length || 0), 0);
        this.setText('summaryProduct', `${productName} (${sku})`);
        this.setText('summaryBatch', this.selectedBatch?.batch_code || (this.forceNewBatch ? 'Batch baru' : 'Batch baru otomatis'));
        this.setText('summaryStage', this.selectedStage ? this.stageLabel(this.selectedStage) : '-');
        const statusText = this.recheckParentInspection && this.selectedStatus
            ? `${this.selectedStatus.toUpperCase()} (Re-check)`
            : (this.selectedStatus ? this.selectedStatus.toUpperCase() : '-');
        this.setText('summaryStatus', statusText);
        this.setText('summaryEvidence', photos ? `${photos} foto terlampir` : 'Belum ada foto');
    },

    setText(id, value) {
        const el = document.getElementById(id);
        if (el) el.textContent = value;
    },

    message(text, isError = false) {
        const el = document.getElementById('qcSubmitMessage');
        if (!el) return;
        el.textContent = text;
        el.classList.toggle('error', isError);
    },

    /* ═══════════════════════════════════════════════
       Active Batches Lookup
       ═══════════════════════════════════════════════ */

    async lookupActiveBatches(sku) {
        const productEl = document.getElementById('productDetected');
        if (!sku) {
            if (productEl) productEl.textContent = 'Isi SKU untuk mencari batch.';
            this.renderActiveBatches([]);
            this.renderQcConcurrency(null, null);
            this.renderContextBatches([]);
            return;
        }
        try {
            const response = await API.get(`/inspection/batches/active?sku=${encodeURIComponent(sku)}`);
            const batches = response?.data?.active_batches || [];
            if (productEl) {
                productEl.textContent = batches.length
                    ? `Ditemukan ${batches.length} batch.`
                    : 'Belum ada batch aktif. Batch baru akan dibuat saat submit.';
            }
            this.renderActiveBatches(batches);
        } catch (error) {
            if (productEl) productEl.textContent = 'Gagal mengecek batch. Tetap bisa submit sebagai batch baru.';
            this.renderActiveBatches([]);
        }
    },

    /* ═══════════════════════════════════════════════
       Render: Product Options
       ═══════════════════════════════════════════════ */

    renderProductOptions(products) {
        const list = document.getElementById('productPickerList');
        if (!list) return;
        if (!products.length) {
            list.innerHTML = `
                <div class="product-empty-state">
                    <p class="simple-qc-message">Produk tidak ditemukan.</p>
                    <button class="btn-secondary manual-sku-toggle" type="button" onclick="Inspection.toggleManualMode()">Input SKU manual</button>
                </div>`;
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

    clearProductList() {
        const list = document.getElementById('productPickerList');
        if (list) list.innerHTML = '';
    },

    async addSkuCard(product) {
        const productKey = this.productKey(product);
        if (!this.skuCards.some(item => this.productKey(item) === productKey)) {
            this.skuCards.unshift(product);
        }
        this.skuBatchMap[productKey] = { loading: true, batches: [] };
        this.renderSkuCards();
        try {
            const response = await API.get(`/batch/by-product/${encodeURIComponent(product.id || product.product_code || productKey)}`);
            this.skuBatchMap[productKey] = {
                loading: false,
                product: response?.data?.product || product,
                batches: response?.data?.batches || [],
            };
        } catch (error) {
            const fallback = await this.fetchBatchesBySku(product.product_code || product.sku_code || product.barcode);
            this.skuBatchMap[productKey] = { loading: false, product, batches: fallback };
        }
        this.renderSkuCards();
    },

    async fetchBatchesBySku(sku) {
        if (!sku) return [];
        try {
            const response = await API.get(`/inspection/batches/active?sku=${encodeURIComponent(sku)}`);
            return response?.data?.active_batches || [];
        } catch (error) {
            return [];
        }
    },

    renderSkuCards() {
        const grid = document.getElementById('skuCardGrid');
        const empty = document.getElementById('skuEmptyState');
        if (!grid) return;
        if (empty) empty.hidden = Boolean(this.skuCards.length);
        if (!this.skuCards.length) {
            grid.innerHTML = '';
            return;
        }
        grid.innerHTML = this.skuCards.map(product => this.skuCardTemplate(product)).join('');
        grid.querySelectorAll('[data-qc-batch]').forEach(button => {
            button.addEventListener('click', () => {
                const product = this.findCardProduct(button.dataset.productKey);
                const batch = this.findCardBatch(button.dataset.productKey, button.dataset.qcBatch);
                this.openQcForm(product, batch, { recheck: false });
            });
        });
        grid.querySelectorAll('[data-recheck-batch]').forEach(button => {
            button.addEventListener('click', () => {
                const product = this.findCardProduct(button.dataset.productKey);
                const batch = this.findCardBatch(button.dataset.productKey, button.dataset.recheckBatch);
                this.openQcForm(product, batch, { recheck: true });
            });
        });
        grid.querySelectorAll('[data-detail-batch]').forEach(button => {
            button.addEventListener('click', () => {
                const batch = this.findCardBatch(button.dataset.productKey, button.dataset.detailBatch);
                this.showBatchDetail(batch);
            });
        });
    },

    skuCardTemplate(product) {
        const key = this.productKey(product);
        const data = this.skuBatchMap[key] || { loading: false, batches: [] };
        const batches = data.batches || [];
        const summary = this.batchStatusSummary(batches);
        return `
            <article class="sku-card" data-product-key="${this.escapeHtml(key)}">
                <div class="sku-card-head">
                    <div>
                        <span class="sku-code">${this.escapeHtml(product.product_code || product.sku_code || product.barcode || '-')}</span>
                        <h2>${this.escapeHtml(product.product_name || '-')}</h2>
                        <p>${this.escapeHtml(product.category || product.product_category || 'Kategori belum diisi')}</p>
                    </div>
                    <strong>${batches.length} batch</strong>
                </div>
                <div class="sku-status-strip">
                    ${this.statusChip('Pending', summary.pending)}
                    ${this.statusChip('PASS', summary.pass)}
                    ${this.statusChip('HOLD', summary.hold)}
                    ${this.statusChip('FAIL', summary.fail)}
                </div>
                <div class="sku-batch-list">
                    ${data.loading ? '<p class="simple-qc-message">Memuat batch...</p>' : this.batchListTemplate(key, batches)}
                </div>
            </article>
        `;
    },

    batchListTemplate(productKey, batches) {
        if (!batches.length) {
            return '<p class="simple-qc-message">Belum ada batch pemasakan untuk SKU ini.</p>';
        }
        return batches.map((batch, index) => {
            const status = this.normalizeStatus(batch.qc_status || batch.last_status || batch.final_qc_status || batch.status || 'pending');
            const hasQc = ['pass', 'hold', 'fail'].includes(status);
            return `
                <article class="batch-card">
                    <div class="batch-card-main">
                        <div>
                            <strong>Batch #${index + 1}</strong>
                            <span>${this.escapeHtml(batch.batch_code || '-')}</span>
                        </div>
                        <span class="status-badge status-${this.statusClass(status)}">${this.escapeHtml(status.toUpperCase())}</span>
                    </div>
                    <dl class="batch-meta">
                        <div><dt>Pemasakan</dt><dd>ke-${this.escapeHtml(batch.batch_sequence || index + 1)}</dd></div>
                        <div><dt>Cook</dt><dd>${this.escapeHtml(batch.cook_name || '-')}</dd></div>
                        <div><dt>Qty</dt><dd>${this.escapeHtml(batch.quantity || '-')}</dd></div>
                        <div><dt>Jam</dt><dd>${this.escapeHtml(this.batchTime(batch))}</dd></div>
                    </dl>
                    <div class="batch-actions">
                        ${hasQc
                            ? `<button class="btn-secondary" type="button" data-detail-batch="${this.escapeHtml(batch.id || batch.batch_code)}" data-product-key="${this.escapeHtml(productKey)}">Lihat Hasil</button>
                               <button class="btn-primary" type="button" data-recheck-batch="${this.escapeHtml(batch.id || batch.batch_code)}" data-product-key="${this.escapeHtml(productKey)}">Tambah Re-check</button>`
                            : `<button class="btn-primary" type="button" data-qc-batch="${this.escapeHtml(batch.id || batch.batch_code)}" data-product-key="${this.escapeHtml(productKey)}">QC Check</button>`}
                    </div>
                </article>
            `;
        }).join('');
    },

    statusChip(label, count) {
        return `<span class="sku-status-chip status-${this.statusClass(label)}"><strong>${count}</strong>${this.escapeHtml(label)}</span>`;
    },

    batchStatusSummary(batches) {
        return batches.reduce((summary, batch) => {
            const status = this.normalizeStatus(batch.qc_status || batch.last_status || batch.final_qc_status || batch.status || 'pending');
            if (status === 'pass') summary.pass += 1;
            else if (status === 'hold') summary.hold += 1;
            else if (status === 'fail') summary.fail += 1;
            else summary.pending += 1;
            return summary;
        }, { pending: 0, pass: 0, hold: 0, fail: 0 });
    },

    productKey(product) {
        return String(product?.id || product?.product_code || product?.sku_code || product?.barcode || '').trim();
    },

    findCardProduct(productKey) {
        return this.skuCards.find(product => this.productKey(product) === productKey) || null;
    },

    findCardBatch(productKey, batchKey) {
        const batches = this.skuBatchMap[productKey]?.batches || [];
        return batches.find(batch => String(batch.id || batch.batch_code) === String(batchKey)) || null;
    },

    /* ═══════════════════════════════════════════════
       Select Product
       ═══════════════════════════════════════════════ */

    async selectProduct(product) {
        this.selectedProduct = product;
        this.manualMode = false;
        this.selectedBatch = null;
        this.forceNewBatch = false;
        this.activeInspection = null;
        this.lastInspection = null;
        this.recheckParentInspection = null;
        const manualWrap = document.getElementById('manualSkuWrap');
        const search = document.getElementById('productSearch');
        const manualInput = document.getElementById('qcSku');
        if (manualWrap) manualWrap.hidden = true;
        if (search) search.value = '';
        if (manualInput) manualInput.value = '';
        this.updateSelectedProductCard();
        this.clearProductList();
        const helpEl = document.getElementById('productSearchHelp');
        if (helpEl) helpEl.hidden = true;
        const productMsg = document.getElementById('productDetected');
        if (productMsg) productMsg.textContent = 'Memuat batch produk...';
        await this.addSkuCard(product);
        this.closeSkuSearch();
        if (productMsg) productMsg.textContent = '';
    },

    /* ═══════════════════════════════════════════════
       Selected Product Card
       ═══════════════════════════════════════════════ */

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
            <div class="selected-product-main">
                <small>Produk dipilih</small>
                <strong>${this.escapeHtml(this.selectedProduct.product_code || '-')}</strong>
                <span>${this.escapeHtml(this.selectedProduct.product_name || '-')}</span>
            </div>
            <div class="selected-product-meta">
                <span>Barcode: ${this.escapeHtml(this.selectedProduct.barcode || this.selectedProduct.product_code || '-')}</span>
                <span>Kategori: ${this.escapeHtml(this.selectedProduct.category || this.selectedProduct.product_category || '-')}</span>
            </div>
            <button class="btn-secondary change-product-btn" type="button">Ganti Produk</button>
        `;
        card.querySelector('.change-product-btn')?.addEventListener('click', () => {
            this.selectedProduct = null;
            this.selectedBatch = null;
            this.selectedStage = null;
            this.selectedStatus = null;
            this.forceNewBatch = false;
            document.querySelectorAll('.qc-stage-option').forEach(item => item.classList.remove('active'));
            document.querySelectorAll('.qc-status-option').forEach(item => item.classList.remove('active'));
            this.updateSelectedProductCard();
            this.renderActiveBatches([]);
            this.renderQcConcurrency(null, null);
            this.clearProductList();
            const helpEl = document.getElementById('productSearchHelp');
            if (helpEl) {
                helpEl.textContent = 'Ketik minimal 2 huruf untuk mencari produk.';
                helpEl.hidden = false;
            }
            const productMsg = document.getElementById('productDetected');
            if (productMsg) productMsg.textContent = 'Pilih produk terlebih dahulu.';
            this.updateProgressiveFields();
            this.updateSubmitState();
            this.updateSummary();
            document.getElementById('productSearch')?.focus();
        });
    },

    /* ═══════════════════════════════════════════════
       Render: Active Batches
       ═══════════════════════════════════════════════ */

    renderActiveBatches(batches) {
        const panel = document.getElementById('activeBatchPanel');
        const list = document.getElementById('activeBatchList');
        const empty = document.getElementById('activeBatchEmpty');
        if (!panel || !list) return;
        const hasContext = this.hasProductContext();
        panel.hidden = !hasContext;
        if (empty) empty.hidden = Boolean(batches.length);
        list.innerHTML = '';
        this.renderContextBatches(batches);
        const createBtn = document.getElementById('createNewBatchBtn');
        if (createBtn) createBtn.textContent = 'Buat Batch Baru';
        batches.forEach(batch => {
            const button = document.createElement('button');
            button.type = 'button';
            button.className = 'batch-choice';
            button.innerHTML = `
                <strong>${this.escapeHtml(batch.batch_code || '-')}</strong>
                <small>Pemasakan ke-${this.escapeHtml(batch.batch_sequence || '-')}</small>
                <small>Jam produksi: ${this.escapeHtml(this.formatDateTime(batch.production_time || batch.created_at))}</small>
                <small>Cook: ${this.escapeHtml(batch.cook_name || '-')} · Qty: ${this.escapeHtml(batch.quantity || '-')}</small>
                <small>Status QC: ${this.escapeHtml(String(batch.last_status || batch.final_qc_status || batch.status || '-').toUpperCase())}</small>
                <span>Lanjutkan Batch Ini</span>
            `;
            button.addEventListener('click', () => {
                this.selectedBatch = batch;
                this.forceNewBatch = false;
                this.recheckParentInspection = null;
                document.querySelectorAll('.batch-choice').forEach(item => item.classList.toggle('active', item === button));
                const newBtn = document.getElementById('createNewBatchBtn');
                if (newBtn) newBtn.textContent = 'Buat Batch Baru';
                this.loadQcConcurrency(batch);
                this.updateSummary();
                this.updateSubmitState();
            });
            list.appendChild(button);
        });
    },

    async loadQcConcurrency(batch) {
        const key = batch?.id || batch?.batch_code;
        if (!key) {
            this.renderQcConcurrency(null, null);
            return;
        }
        try {
            const [activeResponse, historyResponse] = await Promise.all([
                API.get(`/qc/active?batch=${encodeURIComponent(key)}`),
                API.get(`/qc/history/${encodeURIComponent(key)}`)
            ]);
            const active = activeResponse?.data?.active || historyResponse?.data?.active || null;
            const latest = historyResponse?.data?.latest || null;
            this.activeInspection = active;
            this.lastInspection = latest;
            this.renderQcConcurrency(active, latest);
        } catch (error) {
            this.activeInspection = null;
            this.lastInspection = null;
            this.renderQcConcurrency(null, null);
        } finally {
            this.updateSubmitState();
        }
    },

    renderQcConcurrency(active, latest) {
        const panel = document.getElementById('qcConcurrencyPanel');
        const badge = document.getElementById('qcConcurrencyBadge');
        const title = document.getElementById('qcConcurrencyTitle');
        const meta = document.getElementById('qcConcurrencyMeta');
        const photo = document.getElementById('qcConcurrencyPhoto');
        const detailBtn = document.getElementById('qcDetailBtn');
        const recheckBtn = document.getElementById('qcRecheckBtn');
        if (!panel || !badge || !title || !meta) return;
        const item = active || latest;
        panel.hidden = !item;
        if (!item) {
            meta.innerHTML = '';
            if (photo) {
                photo.hidden = true;
                photo.innerHTML = '';
            }
            if (detailBtn) detailBtn.disabled = true;
            if (recheckBtn) recheckBtn.disabled = true;
            return;
        }
        const isHold = String(item.status || '').toLowerCase() === 'hold';
        const isRecheck = Number(item.inspection_round || 1) > 1 || Boolean(item.parent_inspection);
        badge.textContent = active ? '🟢 Sedang diperiksa' : (isHold ? '🔴 HOLD' : (isRecheck ? '🟠 Re-check' : '🔵 Selesai'));
        title.textContent = active
            ? `Sedang diperiksa oleh ${item.staff || '-'}`
            : 'QC terakhir';
        const rows = active ? [
            ['Staff', item.staff],
            ['Mulai', this.formatDateTime(item.start_time || item.created_at)],
            ['Jenis QC', this.stageLabel(item.qc_stage || item.qc_type)],
            ['Batch', item.batch_code || item.batch],
        ] : [
            ['Suhu', item.temperature || '-'],
            ['Status', String(item.status || '-').toUpperCase()],
            ['Staff', item.staff],
            ['Waktu', this.formatDateTime(item.completed_at || item.created_at)],
        ];
        meta.innerHTML = rows.map(([label, value]) => `
            <div>
                <span>${this.escapeHtml(label)}</span>
                <strong>${this.escapeHtml(value || '-')}</strong>
            </div>
        `).join('');
        if (photo) {
            photo.hidden = !(!active && item.photo_url);
            photo.innerHTML = (!active && item.photo_url)
                ? `<img src="${this.escapeHtml(item.photo_url)}" alt="Foto QC terakhir">`
                : '';
        }
        if (detailBtn) detailBtn.disabled = false;
        if (recheckBtn) recheckBtn.disabled = Boolean(active || !latest?.id);
    },

    openQcForm(product, batch, options = {}) {
        if (!product || !batch) return;
        this.selectedProduct = product;
        this.selectedBatch = batch;
        this.forceNewBatch = false;
        this.activeInspection = null;
        this.lastInspection = batch.last_qc || null;
        this.recheckParentInspection = options.recheck && batch.last_qc?.id ? batch.last_qc.id : null;
        this.selectedStage = null;
        this.selectedStatus = null;
        ['qcTemp', 'qcPh', 'qcBrix', 'qcTds', 'qcNotes'].forEach(id => {
            const el = document.getElementById(id);
            if (el) el.value = '';
        });
        ['cookingPhoto', 'barcodePhoto', 'labelPhoto'].forEach(id => {
            const input = document.getElementById(id);
            if (input) input.value = '';
            this.clearPhotoPreview(id);
        });
        document.querySelectorAll('.qc-stage-option, .qc-status-option').forEach(item => item.classList.remove('active'));
        this.renderBatchSummary(product, batch);
        this.renderQcConcurrency(null, batch.last_qc || null);
        const sheet = document.getElementById('qcFormSheet');
        const backdrop = document.getElementById('qcFormBackdrop');
        if (sheet) {
            sheet.hidden = false;
            sheet.setAttribute('aria-hidden', 'false');
            sheet.classList.add('open', 'active');
        }
        if (backdrop) {
            backdrop.hidden = false;
            backdrop.setAttribute('aria-hidden', 'false');
            backdrop.classList.add('open', 'active');
        }
        document.body.classList.add('qc-sheet-open', 'modal-open');
        this.updateProgressiveFields();
        this.updateSubmitState();
    },

    closeQcSheet() {
        const sheet = document.getElementById('qcFormSheet');
        const backdrop = document.getElementById('qcFormBackdrop');
        if (sheet) {
            sheet.classList.remove('open', 'active');
            sheet.setAttribute('aria-hidden', 'true');
            sheet.hidden = true;
        }
        if (backdrop) {
            backdrop.classList.remove('open', 'active');
            backdrop.setAttribute('aria-hidden', 'true');
            backdrop.hidden = true;
        }
        document.body.classList.remove('qc-sheet-open', 'modal-open');
    },

    renderBatchSummary(product, batch) {
        const summary = document.getElementById('qcBatchSummary');
        if (!summary) return;
        summary.innerHTML = `
            <div>
                <span>Produk</span>
                <strong>${this.escapeHtml(product.product_name || '-')}</strong>
                <small>${this.escapeHtml(product.product_code || product.sku_code || product.barcode || '-')}</small>
            </div>
            <div>
                <span>Batch code</span>
                <strong>${this.escapeHtml(batch.batch_code || '-')}</strong>
                <small>Pemasakan ke-${this.escapeHtml(batch.batch_sequence || '-')}</small>
            </div>
            <div>
                <span>Cook</span>
                <strong>${this.escapeHtml(batch.cook_name || '-')}</strong>
                <small>Qty ${this.escapeHtml(batch.quantity || '-')}</small>
            </div>
        `;
    },

    showBatchDetail(batch) {
        if (!batch) return;
        const latest = batch.last_qc || {};
        const detail = [
            `Batch: ${batch.batch_code || '-'}`,
            `Pemasakan ke: ${batch.batch_sequence || '-'}`,
            `Cook: ${batch.cook_name || '-'}`,
            `Qty: ${batch.quantity || '-'}`,
            `Status QC: ${String(batch.qc_status || batch.last_status || batch.final_qc_status || batch.status || '-').toUpperCase()}`,
            latest.qc_stage ? `Jenis: ${this.stageLabel(latest.qc_stage)}` : null,
            latest.inspection_round ? `Round: ${latest.inspection_round}` : null,
            latest.notes ? `Catatan: ${latest.notes}` : null,
        ].filter(Boolean).join('\n');
        window.alert(detail);
    },

    /* ═══════════════════════════════════════════════
       Render: Photo Preview
       ═══════════════════════════════════════════════ */

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
        });
    },

    clearPhotoPreview(inputId) {
        const preview = document.getElementById(`${inputId}Preview`);
        if (!preview) return;
        preview.hidden = true;
        preview.innerHTML = '';
        this.updateSummary();
    },

    renderContextBatches(batches) {
        const count = document.getElementById('contextBatchCount');
        const list = document.getElementById('contextBatchList');
        if (!count || !list) return;
        if (!this.hasProductContext()) {
            count.textContent = 'Belum ada produk';
            list.textContent = 'Pilih produk untuk melihat batch aktif.';
            return;
        }
        count.textContent = batches.length ? `${batches.length} batch ditemukan` : 'Batch baru otomatis';
        if (!batches.length) {
            list.textContent = 'Belum ada batch aktif. Sistem akan membuat batch baru saat submit.';
            return;
        }
        list.innerHTML = batches.slice(0, 3).map(batch => `
            <article class="context-row">
                <strong>${this.escapeHtml(batch.batch_code || '-')}</strong>
                <span>Pemasakan ke-${this.escapeHtml(batch.batch_sequence || '-')} - ${this.escapeHtml(String(batch.last_status || batch.status || '-').toUpperCase())}</span>
                <span>${this.escapeHtml(batch.cook_name || '-')} · Qty ${this.escapeHtml(batch.quantity || '-')}</span>
            </article>
        `).join('');
    },

    rememberRecentSubmission(item) {
        const key = 'qc_recent_submissions';
        const current = JSON.parse(localStorage.getItem(key) || '[]');
        localStorage.setItem(key, JSON.stringify([item, ...current].slice(0, 5)));
    },

    loadRecentSubmissions() {
        const list = document.getElementById('recentQcList');
        if (!list) return;
        const items = JSON.parse(localStorage.getItem('qc_recent_submissions') || '[]');
        if (!items.length) {
            list.textContent = 'Belum ada riwayat QC dari perangkat ini.';
            return;
        }
        list.innerHTML = items.map(item => `
            <article class="context-row">
                <strong>${this.escapeHtml(item.product_name || item.sku_code || '-')}</strong>
                <span>${this.stageLabel(item.qc_stage)} - ${this.escapeHtml(String(item.status || '-').toUpperCase())}</span>
            </article>
        `).join('');
    },

    /* ═══════════════════════════════════════════════
       Helpers
       ═══════════════════════════════════════════════ */

    hasProductContext() {
        const manualSku = document.getElementById('qcSku')?.value?.trim();
        return Boolean(this.selectedProduct || (this.manualMode && manualSku));
    },

    normalizeStatus(value) {
        const status = String(value || '').toLowerCase();
        if (['pass', 'passed', 'completed'].includes(status)) return 'pass';
        if (['hold', 'on_hold'].includes(status)) return 'hold';
        if (['warning', 'pending', 'in_progress', 'open', ''].includes(status)) return 'pending';
        if (['fail', 'failed'].includes(status)) return 'fail';
        return status || 'pending';
    },

    statusClass(value) {
        const status = this.normalizeStatus(value);
        if (status === 'pass') return 'pass';
        if (status === 'fail') return 'fail';
        if (status === 'hold') return 'hold';
        return 'pending';
    },

    batchTime(batch) {
        const value = batch?.production_time || batch?.created_at || batch?.production_date;
        if (!value) return '-';
        const date = new Date(value);
        if (Number.isNaN(date.getTime())) return String(value);
        return date.toLocaleTimeString('id-ID', { hour: '2-digit', minute: '2-digit' });
    },

    stageLabel(value) {
        if (value === 'cooking_check') return 'Cek Masakan';
        if (value === 'final_check') return 'Cek Label Akhir';
        return this.escapeHtml(value || '-');
    },

    formatDateTime(value) {
        if (!value) return '-';
        const date = new Date(value);
        if (Number.isNaN(date.getTime())) return String(value);
        return date.toLocaleString('id-ID', {
            day: '2-digit',
            month: 'short',
            year: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
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
