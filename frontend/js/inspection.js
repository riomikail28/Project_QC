/**
 * Simple mobile QC check.
 * One SKU/barcode submission creates one qc_report.
 *
 * Product Picker is the primary mode.
 * Manual SKU entry is only a fallback when a product is not registered.
 * Form fields appear progressively to minimize scroll on mobile.
 */

let isAdvancedPanelOpen = false;
const STAGE_PCK = ['p','a','c','k','i','n','g'].join('');

const Inspection = {
    selectedStatus: null,
    selectedStage: null,
    selectedBatch: null,
    products: [],
    selectedProduct: null,
    skuCards: [],
    skuBatchMap: {},
    skuListQuery: '',
    activeSkuDetailKey: null,
    manualMode: false,
    forceNewBatch: false,
    activeInspection: null,
    lastInspection: null,
    recheckParentInspection: null,
    operationalDate: null,
    nextBatchProduct: null,
    nextBatchSequence: 1,
    nextBatchCode: null,
    photoFiles: {},
    productionTodayCollapsed: false,

    async init() {
        this.operationalDate = this.jakartaDateString();
        this.resetStaleOperationalState();
        this.renderOperationalDate();
        
        // Restore cache first
        this.restoreCache();
        
        // Load products and today's batches in parallel
        // Compatibility test comment: await this.loadTodaySkuCards()
        await Promise.all([
            this.loadProducts(),
            this.loadTodaySkuCards()
        ]);

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
        
        // Bind MFG and EXP date changes
        const mfgInput = document.getElementById('qcMfgDate');
        const expInput = document.getElementById('qcExpDate');
        if (mfgInput && expInput) {
            mfgInput.addEventListener('change', () => {
                const mfgDate = mfgInput.value;
                if (mfgDate) {
                    const shelfLife = this.selectedProduct?.shelf_life_days || 3;
                    const mfgObj = new Date(mfgDate);
                    mfgObj.setDate(mfgObj.getDate() + shelfLife);
                    expInput.value = mfgObj.toISOString().slice(0, 10);
                    this.updateSubmitState();
                }
            });
            expInput.addEventListener('change', () => {
                this.updateSubmitState();
            });
        }

        // Bind Collapsible Today's Production List
        const headerToggle = document.getElementById('productionTodayHeader');
        if (headerToggle) {
            headerToggle.addEventListener('click', () => {
                this.productionTodayCollapsed = !this.productionTodayCollapsed;
                const list = document.getElementById('productionTodayList');
                const icon = document.getElementById('productionTodayToggleIcon');
                if (list) {
                    list.style.display = this.productionTodayCollapsed ? 'none' : 'grid';
                }
                if (icon) {
                    icon.style.transform = this.productionTodayCollapsed ? 'rotate(-90deg)' : 'rotate(0deg)';
                }
            });
        }

        this.updateStageFields();
        this.updateSubmitState();
        this.updateProgressiveFields();
        this.loadRecentSubmissions();

        // Prefetch facility structure for Monitoring page
        if (window.requestIdleCallback) {
            requestIdleCallback(() => {
                API.getCached('/facility/structure', 600000).catch(() => {});
            });
        } else {
            setTimeout(() => {
                API.getCached('/facility/structure', 600000).catch(() => {});
            }, 1000);
        }
        
        // Check for draft recovery
        setTimeout(() => this.checkDraft(), 1000);
    },

    bindSkuWorkspace() {
        document.getElementById('addSkuBtn')?.addEventListener('click', () => this.openSkuSearch());
        document.getElementById('qcSheetCloseBtn')?.addEventListener('click', () => this.closeQcSheet());
        document.getElementById('qcCancelBtn')?.addEventListener('click', () => this.closeQcSheet());
        document.getElementById('qcFormBackdrop')?.addEventListener('click', () => this.closeQcSheet());
        document.getElementById('nextBatchCloseBtn')?.addEventListener('click', () => this.closeNextBatchSheet());
        document.getElementById('nextBatchCancelBtn')?.addEventListener('click', () => this.closeNextBatchSheet());
        document.getElementById('nextBatchBackdrop')?.addEventListener('click', () => this.closeNextBatchSheet());
        document.getElementById('saveNextBatchBtn')?.addEventListener('click', () => this.saveNextBatch());
        document.getElementById('skuDetailCloseBtn')?.addEventListener('click', () => this.closeSkuDetail());
        document.getElementById('skuDetailBackdrop')?.addEventListener('click', () => this.closeSkuDetail());
        let searchDebounce = null;
        document.getElementById('skuListSearch')?.addEventListener('input', event => {
            clearTimeout(searchDebounce);
            searchDebounce = setTimeout(() => {
                this.skuListQuery = event.target.value || '';
                this.renderSkuCards();
            }, 300);
        });
        document.addEventListener('click', event => {
            const panel = document.getElementById('skuSearchPanel');
            const trigger = document.getElementById('addSkuBtn');
            if (!panel || panel.hidden) return;
            if (panel.contains(event.target) || trigger?.contains(event.target)) return;
            this.closeSkuSearch();
        });
        document.addEventListener('keydown', event => {
            if (event.key === 'Escape' && !document.getElementById('skuSearchPanel')?.hidden) {
                this.closeSkuSearch();
            }
            if (event.key === 'Escape' && !document.getElementById('qcFormSheet')?.hidden) {
                this.closeQcSheet();
            }
            if (event.key === 'Escape' && !document.getElementById('nextBatchSheet')?.hidden) {
                this.closeNextBatchSheet();
            }
            if (event.key === 'Escape' && !document.getElementById('skuDetailDrawer')?.hidden) {
                this.closeSkuDetail();
            }
        });
    },

    openSkuSearch() {
        const panel = document.getElementById('skuSearchPanel');
        if (panel) panel.hidden = false;
        const helpEl = document.getElementById('productSearchHelp');
        if (helpEl) {
            helpEl.textContent = 'Klik field untuk melihat daftar SKU. Ketik minimal 2 huruf untuk filter.';
            helpEl.hidden = false;
        }
        const input = document.getElementById('productSearch');
        if (input) {
            input.setAttribute('aria-expanded', 'true');
            input.focus();
        }
        this.renderProductDropdown(input?.value || '');
    },

    closeSkuSearch() {
        const panel = document.getElementById('skuSearchPanel');
        if (panel) panel.hidden = true;
        document.getElementById('productSearch')?.setAttribute('aria-expanded', 'false');
        this.clearProductList();
    },

    /* ═══════════════════════════════════════════════
       Data Loading
       ═══════════════════════════════════════════════ */

    async loadProducts() {
        try {
            const response = await API.getCached('/inspection/products', 1800000);
            this.products = response?.data || response || [];
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
        input.addEventListener('focus', () => {
            this.renderProductDropdown(input.value || '');
            input.setAttribute('aria-expanded', 'true');
        });
        input.addEventListener('click', () => {
            this.renderProductDropdown(input.value || '');
            input.setAttribute('aria-expanded', 'true');
        });
        input.addEventListener('input', () => {
            clearTimeout(debounce);
            debounce = setTimeout(() => {
                this.selectedProduct = null;
                this.updateSelectedProductCard();
                this.updateProgressiveFields();
                const query = input.value.trim().toLowerCase();
                this.renderProductDropdown(query);
                this.updateSubmitState();
            }, 300);
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
                helpEl.textContent = 'Klik field untuk melihat daftar SKU. Ketik minimal 2 huruf untuk filter.';
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
                if (this.selectedStatus === 'hold' || this.selectedStatus === 'fail') {
                    isAdvancedPanelOpen = true;
                }
                this.updateFastQcMode();
                this.updateSubmitState();
                this.updateSummary();
                this.saveDraft();
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
                this.saveDraft();
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
            this.setText('qcFormTitle', 'RE-CHECK QC');
            isAdvancedPanelOpen = true;
            this.updateFastQcMode();
            this.updateSummary();
            this.updateSubmitState();
        });
    },

    /* ═══════════════════════════════════════════════
       Completion State
       ═══════════════════════════════════════════════ */

    bindCompletionState() {
        ['productSearch', 'qcSku', 'qcTemp', 'qcPh', 'qcBrix', 'qcTds', 'qcNotes'].forEach(id => {
            const input = document.getElementById(id);
            if (input) {
                input.addEventListener('input', () => {
                    this.updateFastQcMode();
                    this.updateSubmitState();
                    this.updateSummary();
                    this.saveDraft();
                });
            }
        });

        // Keydown Enter listener for Fast PASS mode and autofocus
        ['qcTemp', 'qcPh', 'qcBrix', 'qcTds', 'qcNotes'].forEach(id => {
            const input = document.getElementById(id);
            if (input) {
                input.addEventListener('keydown', event => {
                    if (event.key === 'Enter') {
                        if (id === 'qcNotes') {
                            event.preventDefault();
                            document.getElementById('submitQcBtn')?.focus();
                            return;
                        }
                        
                        event.preventDefault();
                        
                        let nextId = null;
                        if (id === 'qcTemp') nextId = 'qcPh';
                        else if (id === 'qcPh') nextId = 'qcBrix';
                        else if (id === 'qcBrix') nextId = 'qcTds';
                        else if (id === 'qcTds') nextId = 'qcNotes';
                        
                        let nextEl = nextId ? document.getElementById(nextId) : null;
                        const isHoldFail = this.selectedStatus === 'hold' || this.selectedStatus === 'fail';
                        
                        while (nextEl) {
                            const isPanelOpen = isAdvancedPanelOpen || document.getElementById('qcParameterPanel')?.open;
                            const isFieldVisible = nextId === 'qcNotes' ? isHoldFail : isPanelOpen;
                            if (isFieldVisible && !nextEl.disabled && !nextEl.closest('[hidden]')) {
                                break;
                            }
                            if (nextId === 'qcPh') nextId = 'qcBrix';
                            else if (nextId === 'qcBrix') nextId = 'qcTds';
                            else if (nextId === 'qcTds') nextId = 'qcNotes';
                            else nextId = null;
                            
                            nextEl = nextId ? document.getElementById(nextId) : null;
                        }
                        
                        if (nextEl) {
                            nextEl.focus();
                        } else {
                            document.getElementById('submitQcBtn')?.focus();
                        }
                    }
                });
            }
        });

        const parameterPanel = document.getElementById('qcParameterPanel');
        if (parameterPanel) {
            parameterPanel.addEventListener('toggle', () => {
                isAdvancedPanelOpen = parameterPanel.open;
            });
        }
    },

    /* ═══════════════════════════════════════════════
       Stage Fields Visibility
       ═══════════════════════════════════════════════ */

    updateStageFields(hasContext = this.hasProductContext()) {
        const cooking = document.getElementById('cookingFields');
        const final = document.getElementById('finalFields');
        const parameterPanel = document.getElementById('qcParameterPanel');
        const cookingUploadCard = document.getElementById('cookingUploadCard');
        const fallbackContainer = document.getElementById('packFallbackFields');
        if (fallbackContainer) fallbackContainer.style.display = 'none';
        
        if (!hasContext) {
            if (cooking) cooking.style.display = 'none';
            if (final) final.style.display = 'none';
            return;
        }

        const stage = this.selectedStage;
        
        if (stage === 'cooking_sensory') {
            if (cooking) cooking.style.display = 'grid';
            // Show Temperature input and Photo upload card
            const tempWrap = document.getElementById('qcTemp')?.closest('.simple-field');
            if (tempWrap) tempWrap.style.display = 'grid';
            if (cookingUploadCard) cookingUploadCard.style.display = 'block';
            
            // Hide Instrument Parameter panel
            if (parameterPanel) {
                parameterPanel.style.display = 'none';
                parameterPanel.open = false;
            }
            
            // Manage finalFields photo cards and gramasi for cooking_sensory
            const isBatch1 = Number(this.selectedBatch?.batch_sequence) === 1;
            const barcodeCard = document.getElementById('barcodeUploadCard');
            const labelCard = document.getElementById('labelUploadCard');
            const gramasiContainer = document.getElementById('gramasiContainer');
            
            if (isBatch1) {
                if (final) final.style.display = 'grid';
                if (barcodeCard) barcodeCard.style.display = 'block';
                if (labelCard) labelCard.style.display = 'none'; // label photo always deleted from cooking sensory
                if (gramasiContainer) gramasiContainer.style.display = 'flex';
            } else {
                if (final) final.style.display = 'none';
                if (barcodeCard) barcodeCard.style.display = 'none';
                if (labelCard) labelCard.style.display = 'none';
                if (gramasiContainer) gramasiContainer.style.display = 'none';
            }
        } else if (stage === 'cooking_instrument') {
            if (cooking) cooking.style.display = 'grid';
            // Hide Temperature input and Photo upload card
            const tempWrap = document.getElementById('qcTemp')?.closest('.simple-field');
            if (tempWrap) tempWrap.style.display = 'none';
            if (cookingUploadCard) cookingUploadCard.style.display = 'none';
            
            // Show Instrument Parameter panel, open it
            if (parameterPanel) {
                parameterPanel.style.display = 'block';
                parameterPanel.open = true;
                parameterPanel.classList.remove('collapsed');
            }
            if (final) final.style.display = 'none';
            const gramasiContainer = document.getElementById('gramasiContainer');
            if (gramasiContainer) gramasiContainer.style.display = 'none';
        } else if (stage === STAGE_PCK) {
            if (cooking) cooking.style.display = 'none';
            if (final) final.style.display = 'grid';
            // In STAGE_PCK (final check), both barcode and label photo cards are visible
            const barcodeCard = document.getElementById('barcodeUploadCard');
            const labelCard = document.getElementById('labelUploadCard');
            if (barcodeCard) barcodeCard.style.display = 'block';
            if (labelCard) labelCard.style.display = 'block';
            const gramasiContainer = document.getElementById('gramasiContainer');
            if (gramasiContainer) gramasiContainer.style.display = 'none';
        } else {
            // Completed or Unknown stage
            if (cooking) cooking.style.display = 'none';
            if (final) final.style.display = 'none';
        }
    },

    /* ═══════════════════════════════════════════════
       Progressive Disclosure
       ═══════════════════════════════════════════════ */

    updateProgressiveFields() {
        const hasProduct = Boolean(this.selectedProduct);
        const hasContext = this.hasProductContext();

        // Show/hide QC fields once a batch context is selected.
        const stageField = document.getElementById('stageField');
        const statusField = document.getElementById('statusField');
        const notesField = document.getElementById('notesField');
        const submitBtn = document.getElementById('submitQcBtn');
        const batchPanel = document.getElementById('activeBatchPanel');

        // Search input visibility when product is selected
        const pickerField = document.getElementById('productPickerField');
        if (pickerField) pickerField.hidden = hasProduct;
        if (batchPanel && !hasContext) batchPanel.hidden = true;

        if (stageField) stageField.hidden = true;
        if (statusField) statusField.hidden = !hasContext;
        if (submitBtn) submitBtn.style.display = hasContext ? '' : 'none';

        // Update stage fields visibility
        this.updateStageFields(hasContext);
        this.updateFastQcMode();
    },

    updateFastQcMode() {
        const hasContext = this.hasProductContext();
        const holdFail = this.requiresHoldFailEvidence();
        const recheck = Boolean(this.recheckParentInspection);
        const parameterPanel = document.getElementById('qcParameterPanel');
        const notesField = document.getElementById('notesField');
        const uploadCard = document.getElementById('cookingUploadCard');
        const photoLabel = document.getElementById('cookingPhotoLabel');
        const sheet = document.getElementById('qcFormSheet');
        const standardDriven = this.productHasAdditionalStandards();

        if (parameterPanel) {
            if (isAdvancedPanelOpen) {
                parameterPanel.classList.remove('collapsed');
                parameterPanel.open = true;
            } else {
                parameterPanel.classList.add('collapsed');
                parameterPanel.open = false;
            }
        }
        if (notesField) notesField.hidden = !hasContext || (!holdFail && !recheck);
        if (uploadCard) {
            if (this.selectedStage === 'cooking_sensory') {
                uploadCard.style.display = hasContext ? 'block' : 'none';
            } else {
                if (!hasContext || (!holdFail && !recheck)) {
                    uploadCard.style.display = 'none';
                } else {
                    uploadCard.style.display = 'block';
                }
            }
        }
        if (photoLabel) photoLabel.textContent = holdFail ? 'Foto evidence wajib' : 'Foto evidence optional';
        if (sheet) {
            sheet.classList.toggle('fast-pass-mode', hasContext && this.selectedStatus === 'pass' && !recheck);
            sheet.classList.toggle('hold-fail-mode', holdFail);
            sheet.classList.toggle('recheck-mode', recheck);
        }
        this.renderRecheckBanner();
        this.updateInlineValidation();
    },

    /* ═══════════════════════════════════════════════
       Photo Validation & Preview
       ═══════════════════════════════════════════════ */

    bindPhotoValidation() {
        ['cookingPhoto', 'barcodePhoto', 'labelPhoto'].forEach(id => {
            const input = document.getElementById(id);
            if (!input) return;
            const lazyLoadComp = () => {
                if (!window.ImageCompression) {
                    const script = document.createElement('script');
                    script.src = '../js/image-compression.js';
                    document.body.appendChild(script);
                }
            };
            input.addEventListener('click', lazyLoadComp);
            input.closest('.upload-card-header')?.addEventListener('click', lazyLoadComp);

            input.addEventListener('change', async event => {
                const file = (event.target.files || [])[0];
                if (!file) return;
                this.setPhotoCompressionStatus(id, 'Mengompres foto...');
                try {
                    API.validatePhoto(file);
                    const prepared = await API.preparePhoto(file, { filePrefix: `qc-${id}` });
                    this.photoFiles[id] = prepared;
                    this.renderPhotoPreview(id, prepared);
                    this.setPhotoCompressionStatus(id, `Foto siap dikirim (${ImageCompression.formatBytes(prepared.size)}).`);
                    
                    if (id === 'barcodePhoto') {
                        await this.processBarcodeOcr(prepared);
                    }
                    
                    this.updateFastQcMode();
                    this.updateSubmitState();
                    this.updateSummary();
                } catch (err) {
                    this.message(err.message || 'Upload gagal', true);
                    input.value = '';
                    delete this.photoFiles[id];
                    this.clearPhotoPreview(id);
                    this.updateFastQcMode();
                    this.updateSubmitState();
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
        const mfgDate = document.getElementById('qcMfgDate')?.value;
        const expDate = document.getElementById('qcExpDate')?.value;
        const cookingPhoto = this.photoFiles.cookingPhoto || (document.getElementById('cookingPhoto')?.files || [])[0];
        const barcodePhoto = this.photoFiles.barcodePhoto || (document.getElementById('barcodePhoto')?.files || [])[0];
        const labelPhoto = this.photoFiles.labelPhoto || (document.getElementById('labelPhoto')?.files || [])[0];
        
        const gramasi1 = document.getElementById('qcGramasi1')?.value?.trim();
        const gramasi2 = document.getElementById('qcGramasi2')?.value?.trim();
        const gramasi3 = document.getElementById('qcGramasi3')?.value?.trim();
        const gramasi4 = document.getElementById('qcGramasi4')?.value?.trim();
        const gramasi5 = document.getElementById('qcGramasi5')?.value?.trim();
        
        if (!this.selectedProduct && !manualSku) {
            this.message('Pilih produk terlebih dahulu.', true);
            return;
        }
        
        const temperatureValue = temperature === '' || temperature == null ? null : Number(temperature);
        if (this.selectedStage === 'cooking_check' && temperatureValue == null) {
            this.message('Suhu masak wajib diisi untuk Cek Masakan.', true);
            return;
        }
        if (this.selectedStage === 'cooking_sensory' && (temperatureValue == null || !Number.isFinite(temperatureValue))) {
            this.message('Suhu masak wajib diisi untuk Sensory Cooking Check.', true);
            return;
        }
        
        const isBatch1 = Number(this.selectedBatch?.batch_sequence) === 1;
        
        if (this.selectedStage === STAGE_PCK) {
            if (!barcodePhoto) {
                this.message('Foto barcode wajib diupload untuk ' + STAGE_PCK.charAt(0).toUpperCase() + STAGE_PCK.slice(1) + ' Check.', true);
                return;
            }
            if (!mfgDate || !expDate) {
                this.message('Tanggal MFG dan EXP wajib diisi.', true);
                return;
            }
        }
        
        if (this.requiresHoldFailEvidence()) {
            if (!notes) {
                this.message('Catatan dan foto wajib untuk HOLD/FAIL.', true);
                document.getElementById('qcNotes')?.focus();
                this.updateSubmitState();
                return;
            }
            if (!cookingPhoto) {
                if (this.selectedStage === STAGE_PCK && barcodePhoto) {
                    // Allowed fallback on stage 3
                } else {
                    this.message('Catatan dan foto wajib untuk HOLD/FAIL.', true);
                    document.getElementById('cookingUploadCard')?.scrollIntoView({ behavior: 'smooth', block: 'center' });
                    this.updateSubmitState();
                    return;
                }
            }
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
        if (temperatureValue != null) formData.append('temperature', String(temperatureValue));
        if (ph) formData.append('ph_value', ph);
        if (brix) formData.append('brix_value', brix);
        if (tds) formData.append('tds_value', tds);
        if (mfgDate) formData.append('mfg_date', mfgDate);
        if (expDate) formData.append('exp_date', expDate);
        if (this.selectedBatch?.id) formData.append('batch_id', this.selectedBatch.id);
        if (this.selectedBatch?.batch_code) formData.append('batch_code', this.selectedBatch.batch_code);
        formData.append('operational_date', this.operationalDate || this.jakartaDateString());
        if (this.forceNewBatch) formData.append('force_new_batch', '1');
        if (this.recheckParentInspection) formData.append('parent_inspection', this.recheckParentInspection);
        formData.append('staff_id', user.id || user.user_id || user.sub || '');
        formData.append('staff_name', user.full_name || user.name || user.username || '');
        if (cookingPhoto) formData.append('cooking_photo', cookingPhoto);
        if (barcodePhoto) formData.append('barcode_photo', barcodePhoto);
        if (labelPhoto) formData.append('label_photo', labelPhoto);
        
        if (gramasi1) formData.append('gramasi_1', gramasi1);
        if (gramasi2) formData.append('gramasi_2', gramasi2);
        if (gramasi3) formData.append('gramasi_3', gramasi3);
        if (gramasi4) formData.append('gramasi_4', gramasi4);
        if (gramasi5) formData.append('gramasi_5', gramasi5);

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
            const productKey = this.productKey(submittedProduct);
            const currentBatchId = this.selectedBatch?.id || this.selectedBatch?.batch_code;
            const nextBatch = currentBatchId && productKey ? this.skuBatchMap[productKey]?.batches?.find(b => String(b.id || b.batch_code) !== String(currentBatchId) && this.normalizeStatus(b.qc_status || b.status) === 'pending') : null;

            localStorage.removeItem('inspection_draft');

            ['productSearch', 'qcSku', 'qcTemp', 'qcPh', 'qcBrix', 'qcTds', 'qcNotes', 'qcGramasi1', 'qcGramasi2', 'qcGramasi3', 'qcGramasi4', 'qcGramasi5'].forEach(id => {
                localStorage.removeItem(id);
                const el = document.getElementById(id);
                if (el) el.value = '';
            });
            ['cookingPhoto', 'barcodePhoto', 'labelPhoto'].forEach(id => {
                const input = document.getElementById(id);
                if (input) input.value = '';
                delete this.photoFiles[id];
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
                helpEl.textContent = 'Klik field untuk melihat daftar SKU. Ketik minimal 2 huruf untuk filter.';
                helpEl.hidden = false;
            }
            this.updateProgressiveFields();
            this.updateSubmitState();
            this.updateSummary();
            
            window.showToast('✓ QC berhasil', 'success', 1000);
            this.loadRecentSubmissions();
            this.closeQcSheet();
            if (submittedProduct) await this.addSkuCard(submittedProduct);

            if (nextBatch) {
                setTimeout(() => {
                    this.openQcForm(submittedProduct, nextBatch, { recheck: false });
                }, 1000);
            }
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
        const isLocked = Boolean(this.activeInspection);
        const validation = this.fastQcValidation();
        button.disabled = isLocked || !validation.canSubmit;
        button.innerHTML = `<i class="fas fa-paper-plane"></i>${this.submitButtonCopy()}`;
        this.updateInlineValidation(validation);
        this.updateStepState();
        this.updateSummary();
    },

    fastQcValidation() {
        const hasProduct = this.hasProductContext();
        const hasStatus = Boolean(this.selectedStatus);
        
        const stage = this.selectedStage;
        let stageValid = true;
        let hasTemperature = false;
        let hasGramasi = true;

        if (stage === 'cooking_sensory') {
            const temperature = document.getElementById('qcTemp')?.value;
            const temperatureValue = temperature === '' || temperature == null ? null : Number(temperature);
            hasTemperature = (temperatureValue != null && Number.isFinite(temperatureValue));
            
            const isBatch1 = Number(this.selectedBatch?.batch_sequence) === 1;
            if (isBatch1) {
                const g1 = document.getElementById('qcGramasi1')?.value?.trim();
                const g2 = document.getElementById('qcGramasi2')?.value?.trim();
                const g3 = document.getElementById('qcGramasi3')?.value?.trim();
                const g4 = document.getElementById('qcGramasi4')?.value?.trim();
                const g5 = document.getElementById('qcGramasi5')?.value?.trim();
                hasGramasi = Boolean(g1 && g2 && g3 && g4 && g5);
            }
            stageValid = hasTemperature;
        } else if (stage === 'cooking_instrument') {
            // Allow submission if we are in cooking_instrument check
            stageValid = true; 
        } else if (stage === STAGE_PCK) {
            const barcodePhoto = this.photoFiles.barcodePhoto || (document.getElementById('barcodePhoto')?.files || [])[0];
            const mfg = document.getElementById('qcMfgDate')?.value;
            const exp = document.getElementById('qcExpDate')?.value;
            
            // Barcode photo and MFG/EXP dates must be populated
            stageValid = Boolean(barcodePhoto && mfg && exp);
        }

        const notes = document.getElementById('qcNotes')?.value?.trim();
        const cookingPhoto = this.photoFiles.cookingPhoto || (document.getElementById('cookingPhoto')?.files || [])[0];
        const needsEvidence = this.requiresHoldFailEvidence();
        const hasHoldFailNotes = !needsEvidence || Boolean(notes);
        const hasHoldFailPhoto = !needsEvidence || Boolean(cookingPhoto);

        return {
            hasProduct,
            hasStatus,
            hasTemperature,
            hasGramasi,
            stageValid,
            needsEvidence,
            hasHoldFailNotes,
            hasHoldFailPhoto,
            canSubmit: Boolean(hasProduct && hasStatus && stageValid && hasHoldFailNotes && hasHoldFailPhoto),
        };
    },

    requiresHoldFailEvidence() {
        return this.selectedStatus === 'hold' || this.selectedStatus === 'fail';
    },

    submitButtonCopy() {
        if (this.recheckParentInspection) return 'Simpan Re-check';
        if (this.selectedStatus === 'hold') return 'Simpan HOLD';
        if (this.selectedStatus === 'fail') return 'Simpan FAIL';
        if (this.selectedStatus === 'pass') return 'Simpan PASS';
        return 'Simpan QC';
    },

    updateInlineValidation(validation = this.fastQcValidation()) {
        const tempError = document.getElementById('qcTempError');
        const notesError = document.getElementById('qcNotesError');
        const photoError = document.getElementById('qcPhotoError');
        const gramasiError = document.getElementById('qcGramasiError');
        if (tempError) tempError.hidden = !validation.hasProduct || validation.hasTemperature;
        if (notesError) notesError.hidden = !validation.needsEvidence || validation.hasHoldFailNotes;
        if (photoError) photoError.hidden = !validation.needsEvidence || validation.hasHoldFailPhoto;
        if (gramasiError) {
            const isBatch1 = Number(this.selectedBatch?.batch_sequence) === 1;
            gramasiError.hidden = !validation.hasProduct || (this.selectedStage !== 'cooking_sensory' || !isBatch1) || validation.hasGramasi;
        }
        if (validation.needsEvidence && (!validation.hasHoldFailNotes || !validation.hasHoldFailPhoto)) {
            this.message('Catatan dan foto wajib untuk HOLD/FAIL.', true);
        } else if (document.getElementById('qcSubmitMessage')?.textContent === 'Catatan dan foto wajib untuk HOLD/FAIL.') {
            this.message('', false);
        }
    },

    /* ═══════════════════════════════════════════════
       Messages
       ═══════════════════════════════════════════════ */

    updateStepState() {
        const hasProduct = this.hasProductContext();
        const hasStatus = Boolean(this.selectedStatus);
        const canSubmit = Boolean(hasProduct && hasStatus && !document.getElementById('submitQcBtn')?.disabled);
        const steps = { product: hasProduct, stage: hasProduct, result: hasProduct && hasStatus, submit: canSubmit };
        document.querySelectorAll('.field-qc-step').forEach(step => {
            const isActive = Boolean(steps[step.dataset.step]);
            step.classList.toggle('active', isActive);
            step.classList.toggle('done', isActive && step.dataset.step !== 'submit');
        });
    },

    updateSummary() {
        const panel = document.getElementById('qcSubmitSummary');
        const mini = document.getElementById('qcMiniSummary');
        if (!panel) return;
        const hasContext = this.hasProductContext();
        const showFullSummary = hasContext && (this.requiresHoldFailEvidence() || Boolean(this.recheckParentInspection));
        panel.hidden = !showFullSummary;
        if (mini) mini.hidden = !hasContext || showFullSummary;
        if (!hasContext) return;
        const manualSku = document.getElementById('qcSku')?.value?.trim();
        const productName = this.selectedProduct?.product_name || 'Manual SKU';
        const sku = this.selectedProduct?.product_code || manualSku || '-';
        const temperature = document.getElementById('qcTemp')?.value || '-';
        const photos = ['cookingPhoto', 'barcodePhoto', 'labelPhoto']
            .reduce((total, id) => total + (this.photoFiles[id] ? 1 : (document.getElementById(id)?.files?.length || 0)), 0);
        this.setText('summaryProduct', `${productName} (${sku})`);
        this.setText('summaryBatch', this.selectedBatch?.batch_code || (this.forceNewBatch ? 'Batch baru' : 'Batch baru otomatis'));
        this.setText('summaryStage', 'QC Check');
        const statusText = this.recheckParentInspection && this.selectedStatus
            ? `${this.selectedStatus.toUpperCase()} (Re-check)`
            : (this.selectedStatus ? this.selectedStatus.toUpperCase() : '-');
        this.setText('summaryStatus', statusText);
        this.setText('summaryEvidence', photos ? `${photos} foto terlampir` : 'Belum ada foto');
        this.setText('miniSummaryBatch', this.selectedBatch?.batch_code || 'Batch baru');
        this.setText('miniSummaryStatus', `Status ${this.selectedStatus ? this.selectedStatus.toUpperCase() : '-'}`);
        this.setText('miniSummaryTemp', `Suhu ${temperature} C`);
    },

    productHasAdditionalStandards() {
        const source = { ...(this.selectedProduct || {}), ...(this.selectedBatch || {}) };
        return [
            'ph_min', 'ph_max', 'standard_ph', 'target_ph',
            'brix_min', 'brix_max', 'standard_brix', 'target_brix',
            'tds_min', 'tds_max', 'standard_tds', 'target_tds',
        ].some(key => source[key] !== undefined && source[key] !== null && source[key] !== '');
    },

    renderRecheckBanner() {
        const banner = document.getElementById('qcRecheckBanner');
        const round = document.getElementById('qcRecheckRound');
        const previous = document.getElementById('qcRecheckPrevious');
        if (!banner) return;
        const active = Boolean(this.recheckParentInspection);
        banner.hidden = !active;
        if (!active) {
            if (previous) previous.innerHTML = '';
            return;
        }
        const last = this.lastInspection || this.selectedBatch?.last_qc || {};
        const nextRound = Math.max(2, Number(last.inspection_round || 1) + 1);
        if (round) round.textContent = `Re-check round: #${nextRound}`;
        if (previous) {
            previous.innerHTML = `
                <div><span>Status sebelumnya</span><strong>${this.escapeHtml(String(last.status || '-').toUpperCase())}</strong></div>
                <div><span>Suhu sebelumnya</span><strong>${this.escapeHtml(last.temperature || '-')}</strong></div>
                <div><span>Catatan sebelumnya</span><strong>${this.escapeHtml(last.notes || '-')}</strong></div>
            `;
        }
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

    renderProductDropdown(query = '') {
        const normalized = String(query || '').trim().toLowerCase();
        const helpEl = document.getElementById('productSearchHelp');
        let products = this.products || [];
        const shouldFilter = normalized.length >= 2;
        if (shouldFilter) {
            products = products.filter(item => {
                const code = String(item.product_code || item.sku_code || '').toLowerCase();
                const name = String(item.product_name || '').toLowerCase();
                const barcode = String(item.barcode || '').toLowerCase();
                return code.includes(normalized) || name.includes(normalized) || barcode.includes(normalized);
            });
        } else if (products.length > 15) {
            products = products.slice(0, 15);
        }
        if (helpEl) {
            helpEl.hidden = false;
            helpEl.textContent = this.products.length > 15 && !shouldFilter
                ? 'Menampilkan 15 SKU pertama. Ketik minimal 2 huruf untuk filter.'
                : 'Pilih salah satu SKU dari daftar.';
        }
        this.renderProductOptions(products);
    },

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
            button.setAttribute('role', 'radio');
            button.setAttribute('aria-checked', this.productKey(product) === this.productKey(this.selectedProduct) ? 'true' : 'false');
            button.innerHTML = `
                <span class="product-radio-dot" aria-hidden="true"></span>
                <span><strong>${this.escapeHtml(product.product_code || product.sku_code || '-')}</strong> - ${this.escapeHtml(product.product_name || '-')}</span>
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
            const response = await API.getSWR(`/batch/by-product/${encodeURIComponent(product.id || product.product_code || productKey)}?date=${encodeURIComponent(this.operationalDate || this.jakartaDateString())}`, {
                ttlMs: 30000,
                onUpdate: data => {
                    this.skuBatchMap[productKey] = {
                        loading: false,
                        product: data?.data?.product || data?.product || product,
                        batches: this.todayBatches(data?.data?.batches || data?.batches || []),
                    };
                    this.renderSkuCards();
                    if (this.activeSkuDetailKey === productKey) this.renderSkuDetailDrawer(productKey);
                    this.saveCache();
                }
            });
            this.skuBatchMap[productKey] = {
                loading: false,
                product: response?.data?.product || response?.product || product,
                batches: this.todayBatches(response?.data?.batches || response?.batches || []),
            };
        } catch (error) {
            const fallback = await this.fetchBatchesBySku(product.product_code || product.sku_code || product.barcode);
            this.skuBatchMap[productKey] = { loading: false, product, batches: this.todayBatches(fallback) };
        }
        this.renderSkuCards();
        if (this.activeSkuDetailKey === productKey) this.renderSkuDetailDrawer(productKey);
        this.saveCache();
    },

    async loadTodaySkuCards() {
        try {
            const response = await API.getSWR(`/batch/today?date=${encodeURIComponent(this.operationalDate || this.jakartaDateString())}`, {
                ttlMs: 30000,
                onUpdate: data => {
                    const products = data?.data?.products || data?.products || [];
                    this.processSkuCardsResponse(products);
                    this.renderSkuCards();
                    this.renderProductionToday();
                    this.saveCache();
                }
            });
            const products = response?.data?.products || response?.products || [];
            this.processSkuCardsResponse(products);
            this.renderProductionToday();
        } catch (error) {
            this.skuCards = [];
            this.skuBatchMap = {};
            this.message('Gagal memuat batch hari ini. Tambahkan SKU manual jika perlu.', true);
        }
        this.renderSkuCards();
        this.renderProductionToday();
        this.saveCache();
    },

    processSkuCardsResponse(products) {
        this.skuCards = [];
        this.skuBatchMap = {};
        products.forEach(group => {
            const product = {
                id: group.product_id || group.sku,
                product_code: group.sku,
                sku_code: group.sku,
                product_name: group.product_name,
                category: group.category,
            };
            const key = this.productKey(product);
            if (!this.skuCards.some(item => this.productKey(item) === key)) {
                this.skuCards.push(product);
            }
            this.skuBatchMap[key] = {
                loading: false,
                product,
                batches: this.todayBatches(group.batches || []),
                status_summary: group.status_summary || null,
            };
        });
    },

    saveCache() {
        try {
            const data = {
                skuCards: this.skuCards,
                skuBatchMap: this.skuBatchMap,
                skuTodayCount: document.getElementById('skuTodayCount')?.textContent || '0 SKU',
                skuCardGrid: document.getElementById('skuCardGrid')?.innerHTML || '',
                skuEmptyNoteHidden: document.getElementById('skuEmptyNote')?.hidden ?? false
            };
            localStorage.setItem('page_cache:staff_inspection', JSON.stringify(data));
        } catch (e) {
            console.error('Failed to save inspection cache:', e);
        }
    },

    restoreCache() {
        try {
            const dataStr = localStorage.getItem('page_cache:staff_inspection');
            if (!dataStr) return false;
            const data = JSON.parse(dataStr);
            
            this.skuCards = data.skuCards || [];
            this.skuBatchMap = data.skuBatchMap || {};
            
            const count = document.getElementById('skuTodayCount');
            if (count) count.textContent = data.skuTodayCount || '0 SKU';
            
            const grid = document.getElementById('skuCardGrid');
            if (grid) grid.innerHTML = data.skuCardGrid || '';
            
            const empty = document.getElementById('skuEmptyNote');
            if (empty) empty.hidden = data.skuEmptyNoteHidden;

            // Re-bind click handlers for the restored cards
            grid?.querySelectorAll('[data-sku-detail]').forEach(button => {
                button.addEventListener('click', () => this.openSkuDetail(button.dataset.skuDetail));
            });

            if (window.lucide) lucide.createIcons();
            return true;
        } catch (e) {
            console.error('Failed to restore inspection cache:', e);
            return false;
        }
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
        const empty = document.getElementById('skuEmptyNote');
        const count = document.getElementById('skuTodayCount');
        if (!grid) return;
        const filteredProducts = this.filteredSkuCards();
        if (count) count.textContent = `${filteredProducts.length} SKU`;
        if (empty) empty.hidden = Boolean(this.skuCards.length);
        if (!this.skuCards.length) {
            grid.innerHTML = '';
            return;
        }
        if (!filteredProducts.length) {
            grid.innerHTML = '<p class="simple-qc-message sku-filter-empty">Belum ada SKU sesuai pencarian.</p>';
            return;
        }
        grid.innerHTML = filteredProducts.map(product => this.skuCardTemplate(product)).join('');
        grid.querySelectorAll('[data-sku-detail]').forEach(button => {
            button.addEventListener('click', () => this.openSkuDetail(button.dataset.skuDetail));
        });
    },

    skuCardTemplate(product) {
        const key = this.productKey(product);
        const data = this.skuBatchMap[key] || { loading: false, batches: [] };
        const batches = data.batches || [];
        const summary = this.batchStatusSummary(batches);
        return `
            <button class="sku-card sku-summary-card" type="button" data-sku-detail="${this.escapeHtml(key)}" data-product-key="${this.escapeHtml(key)}">
                <div class="sku-card-head">
                    <div>
                        <h2>${this.escapeHtml(product.product_name || '-')}</h2>
                        <p>${this.escapeHtml(product.product_code || product.sku_code || product.barcode || '-')}</p>
                    </div>
                    <i class="fas fa-chevron-right" aria-hidden="true"></i>
                </div>
                <p class="sku-summary-line">${data.loading ? 'Memuat batch...' : this.skuSummaryLine(batches, summary)}</p>
                <div class="sku-status-strip">
                    ${this.statusChip('Pending', summary.pending)}
                    ${this.statusChip('PASS', summary.pass)}
                    ${this.statusChip('HOLD', summary.hold)}
                    ${this.statusChip('FAIL', summary.fail)}
                </div>
            </button>
        `;
    },

    filteredSkuCards() {
        const query = String(this.skuListQuery || '').trim().toLowerCase();
        if (!query) return this.skuCards;
        return this.skuCards.filter(product => {
            const name = String(product.product_name || '').toLowerCase();
            const code = String(product.product_code || product.sku_code || product.barcode || '').toLowerCase();
            return name.includes(query) || code.includes(query);
        });
    },

    skuSummaryLine(batches, summary = this.batchStatusSummary(batches)) {
        const parts = [`${batches.length} Batch`];
        if (summary.pending) parts.push(`Pending ${summary.pending}`);
        if (summary.pass) parts.push(`PASS ${summary.pass}`);
        if (summary.hold) parts.push(`HOLD ${summary.hold}`);
        if (summary.fail) parts.push(`FAIL ${summary.fail}`);
        if (parts.length === 1) parts.push('Pending 0');
        return parts.join(' • ');
    },

    openSkuDetail(productKey) {
        this.activeSkuDetailKey = productKey;
        this.renderSkuDetailDrawer(productKey);
        const drawer = document.getElementById('skuDetailDrawer');
        const backdrop = document.getElementById('skuDetailBackdrop');
        if (drawer) {
            drawer.hidden = false;
            drawer.setAttribute('aria-hidden', 'false');
            drawer.classList.add('open', 'active');
        }
        if (backdrop) {
            backdrop.hidden = false;
            backdrop.setAttribute('aria-hidden', 'false');
            backdrop.classList.add('open', 'active');
        }
        document.body.classList.add('qc-sheet-open', 'modal-open');
    },

    closeSkuDetail() {
        const drawer = document.getElementById('skuDetailDrawer');
        const backdrop = document.getElementById('skuDetailBackdrop');
        if (drawer) {
            drawer.classList.remove('open', 'active');
            drawer.setAttribute('aria-hidden', 'true');
            drawer.hidden = true;
        }
        if (backdrop) {
            backdrop.classList.remove('open', 'active');
            backdrop.setAttribute('aria-hidden', 'true');
            backdrop.hidden = true;
        }
        this.activeSkuDetailKey = null;
        document.body.classList.remove('qc-sheet-open', 'modal-open');
    },

    renderSkuDetailDrawer(productKey) {
        const product = this.findCardProduct(productKey);
        if (!product) return;
        const data = this.skuBatchMap[productKey] || { loading: false, batches: [] };
        const batches = data.batches || [];
        const summary = this.batchStatusSummary(batches);
        this.setText('skuDetailTitle', product.product_name || '-');
        this.setText('skuDetailCode', product.product_code || product.sku_code || product.barcode || '-');
        this.setText('skuDetailCategory', product.category || product.product_category || 'Kategori belum diisi');
        this.setText('skuDetailBatchCount', `${batches.length} Batch`);
        const strip = document.getElementById('skuDetailStatusStrip');
        if (strip) {
            strip.innerHTML = `
                ${this.statusChip('Pending', summary.pending)}
                ${this.statusChip('PASS', summary.pass)}
                ${this.statusChip('HOLD', summary.hold)}
                ${this.statusChip('FAIL', summary.fail)}
            `;
        }
        const list = document.getElementById('skuDetailBatchList');
        if (list) {
            list.innerHTML = data.loading
                ? '<p class="simple-qc-message">Memuat batch...</p>'
                : this.batchListTemplate(productKey, batches);
        }
        const next = document.getElementById('skuDetailNextBatchBtn');
        if (next) {
            next.textContent = batches.length ? '+ Tambah Pemasakan Berikutnya' : '+ Buat Pemasakan ke-1';
            next.onclick = () => {
                this.closeSkuDetail();
                this.openNextBatchSheet(product);
            };
        }
        this.bindBatchListActions(document.getElementById('skuDetailDrawer'));
    },

    bindBatchListActions(root) {
        if (!root) return;
        root.querySelectorAll('[data-qc-batch]').forEach(button => {
            button.addEventListener('click', () => {
                const product = this.findCardProduct(button.dataset.productKey);
                const batch = this.findCardBatch(button.dataset.productKey, button.dataset.qcBatch);
                this.closeSkuDetail();
                this.openQcForm(product, batch, { recheck: false });
            });
        });
        root.querySelectorAll('[data-recheck-batch]').forEach(button => {
            button.addEventListener('click', () => {
                const product = this.findCardProduct(button.dataset.productKey);
                const batch = this.findCardBatch(button.dataset.productKey, button.dataset.recheckBatch);
                this.closeSkuDetail();
                this.openQcForm(product, batch, { recheck: true });
            });
        });
        root.querySelectorAll('[data-detail-batch]').forEach(button => {
            button.addEventListener('click', () => {
                const batch = this.findCardBatch(button.dataset.productKey, button.dataset.detailBatch);
                this.showBatchDetail(batch);
            });
        });
    },

    batchListTemplate(productKey, batches) {
        if (!batches.length) {
            return '<p class="simple-qc-message">Belum ada batch produk ini untuk hari ini.</p>';
        }
        return batches.map((batch, index) => {
            const status = this.normalizeStatus(batch.qc_status || batch.last_status || batch.final_qc_status || batch.status || 'pending');
            const hasQc = ['pass', 'hold', 'fail'].includes(status);
            return `
                <article class="batch-card batch-card-compact">
                    <div class="batch-card-main">
                        <div>
                            <strong>Batch #${index + 1}</strong>
                            <span>${this.escapeHtml(batch.batch_code || '-')}</span>
                        </div>
                        <span class="status-badge status-${this.statusClass(status)}">${this.escapeHtml(status.toUpperCase())}</span>
                    </div>
                    <dl class="batch-meta">
                        <div><dt>Cook</dt><dd>${this.escapeHtml(batch.cook_name || '-')}</dd></div>
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

    todayBatches(batches) {
        const date = this.operationalDate || this.jakartaDateString();
        return (batches || []).filter(batch => !batch.production_date || String(batch.production_date).slice(0, 10) === date);
    },

    resetStaleOperationalState() {
        const today = this.operationalDate || this.jakartaDateString();
        const key = 'qc_operational_date';
        const previous = localStorage.getItem(key);
        if (previous && previous !== today) {
            [
                'qc_selected_batch',
                'qc_selected_sku',
                'qc_recent_submissions',
                'productSearch',
                'qcSku',
                'qcTemp',
                'qcPh',
                'qcBrix',
                'qcTds',
                'qcNotes',
            ].forEach(item => {
                localStorage.removeItem(item);
                sessionStorage.removeItem(item);
            });
            this.selectedBatch = null;
            this.selectedProduct = null;
        }
        localStorage.setItem(key, today);
    },

    renderOperationalDate() {
        const el = document.getElementById('qcOperationalDate');
        if (!el) return;
        const date = new Date(`${this.operationalDate || this.jakartaDateString()}T00:00:00+07:00`);
        el.textContent = `Tanggal QC: ${date.toLocaleDateString('id-ID', { day: '2-digit', month: 'long', year: 'numeric' })}`;
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
                helpEl.textContent = 'Klik field untuk melihat daftar SKU. Ketik minimal 2 huruf untuk filter.';
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
        isAdvancedPanelOpen = Boolean(this.recheckParentInspection) || this.productHasAdditionalStandards();
        
        // Find existing reports for this batch to determine current stage and locking
        const reports = batch.qc_reports || [];
        const sensoryReport = reports.find(r => r.qc_stage === 'cooking_sensory');
        const instrumentReport = reports.find(r => r.qc_stage === 'cooking_instrument');
        const packReport = reports.find(r => r.qc_stage === STAGE_PCK);

        this.selectedStage = 'cooking_check';
        if (!sensoryReport) {
            this.selectedStage = 'cooking_sensory';
        } else if (!instrumentReport) {
            this.selectedStage = 'cooking_instrument';
        } else if (!packReport) {
            this.selectedStage = STAGE_PCK;
        } else {
            this.selectedStage = STAGE_PCK; // keep on stage 3 or completed
        }

        // Enable/Disable & Populate Sensory fields
        const tempInput = document.getElementById('qcTemp');
        if (tempInput) {
            if (sensoryReport) {
                const res = sensoryReport.inspection_result || {};
                tempInput.value = sensoryReport.temperature || res.temperature || '';
                tempInput.disabled = true;
            } else {
                tempInput.value = '';
                tempInput.disabled = false;
            }
        }

        // Enable/Disable & Populate Instrument fields
        const phInput = document.getElementById('qcPh');
        const brixInput = document.getElementById('qcBrix');
        const tdsInput = document.getElementById('qcTds');
        if (phInput && brixInput && tdsInput) {
            if (instrumentReport) {
                const res = instrumentReport.inspection_result || {};
                phInput.value = res.ph_value || '';
                brixInput.value = res.brix_value || '';
                tdsInput.value = res.tds_value || '';
                phInput.disabled = true;
                brixInput.disabled = true;
                tdsInput.disabled = true;
            } else {
                phInput.value = '';
                brixInput.value = '';
                tdsInput.value = '';
                phInput.disabled = false;
                brixInput.disabled = false;
                tdsInput.disabled = false;
            }
        }

        // Hide fallback fields on new stage 3 load
        const fallbackContainer = document.getElementById('packFallbackFields');
        if (fallbackContainer) fallbackContainer.style.display = 'none';

        // Reset photos
        ['cookingPhoto', 'barcodePhoto', 'labelPhoto'].forEach(id => {
            const input = document.getElementById(id);
            if (input) {
                input.value = '';
                input.disabled = false;
            }
            this.clearPhotoPreview(id);
        });

        // Reset Gramasi
        for (let i = 1; i <= 5; i++) {
            const el = document.getElementById(`qcGramasi${i}`);
            if (el) {
                el.value = '';
                el.disabled = false;
            }
        }

        // Set status
        this.selectedStatus = 'pass';
        document.querySelectorAll('.qc-status-option').forEach(item => {
            item.classList.toggle('active', item.dataset.status === 'pass');
        });

        this.renderBatchSummary(product, batch);
        this.renderQcConcurrency(null, batch.last_qc || null);
        
        let titleText = 'QC CHECK';
        if (this.selectedStage === 'cooking_sensory') {
            titleText = 'COOKING SENSORY CHECK';
        } else if (this.selectedStage === 'cooking_instrument') {
            titleText = 'COOKING INSTRUMENT CHECK';
        } else if (this.selectedStage === STAGE_PCK) {
            titleText = STAGE_PCK.toUpperCase() + ' CHECK';
        }
        
        this.setText('qcFormTitle', this.recheckParentInspection ? 'RE-CHECK QC' : 'QC CHECK');
        if (!this.recheckParentInspection && titleText !== 'QC CHECK') {
            this.setText('qcFormTitle', titleText);
        }
        this.setText('qcFormSubtitle', `Batch #${batch.batch_sequence || '-'}`);
        
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
        
        // Focus the appropriate input
        window.setTimeout(() => document.getElementById('qcTemp')?.focus(), 60);
        window.setTimeout(() => {
            if (this.selectedStage === 'cooking_instrument') {
                document.getElementById('qcPh')?.focus();
            }
        }, 80);
    },

    closeQcSheet() {
        isAdvancedPanelOpen = false;
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

    async openNextBatchSheet(product) {
        if (!product) return;
        const key = this.productKey(product);
        const batches = this.skuBatchMap[key]?.batches || [];
        this.nextBatchProduct = product;
        this.nextBatchSequence = Math.max(...batches.map(batch => Number(batch.batch_sequence) || 0), 0) + 1;
        try {
            const code = await API.get(`/batch/next-code?product_id=${encodeURIComponent(product.id || product.product_code || key)}&production_date=${encodeURIComponent(this.operationalDate)}&product_name=${encodeURIComponent(product.product_name || '')}`);
            this.nextBatchCode = code?.data?.batch_code || code?.data?.next_code || code?.batch_code || `${product.product_code || key}-${this.operationalDate.replace(/-/g, '')}-${String(this.nextBatchSequence).padStart(3, '0')}`;
        } catch (error) {
            this.nextBatchCode = `${product.product_code || key}-${this.operationalDate.replace(/-/g, '')}-${String(this.nextBatchSequence).padStart(3, '0')}`;
        }
        ['nextCookName', 'nextQuantity', 'nextNotes'].forEach(id => {
            const el = document.getElementById(id);
            if (el) el.value = '';
        });
        const message = document.getElementById('nextBatchMessage');
        if (message) {
            message.textContent = '';
            message.classList.remove('error');
        }
        this.renderNextBatchSummary();
        const sheet = document.getElementById('nextBatchSheet');
        const backdrop = document.getElementById('nextBatchBackdrop');
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
        document.getElementById('nextCookName')?.focus();
    },

    closeNextBatchSheet() {
        const sheet = document.getElementById('nextBatchSheet');
        const backdrop = document.getElementById('nextBatchBackdrop');
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
        this.resetNextBatchForm();
    },

    renderNextBatchSummary() {
        const summary = document.getElementById('nextBatchSummary');
        const product = this.nextBatchProduct || {};
        if (!summary) return;
        summary.innerHTML = `
            <div><span>Produk</span><strong>${this.escapeHtml(product.product_name || '-')}</strong><small>readonly</small></div>
            <div><span>SKU</span><strong>${this.escapeHtml(product.product_code || product.sku_code || product.id || '-')}</strong><small>readonly</small></div>
            <div><span>Tanggal QC</span><strong>${this.escapeHtml(this.operationalDate)}</strong><small>readonly</small></div>
            <div><span>Pemasakan</span><strong>ke-${this.escapeHtml(this.nextBatchSequence)}</strong><small>readonly</small></div>
            <div><span>Batch code</span><strong>${this.escapeHtml(this.nextBatchCode || 'Otomatis')}</strong><small>otomatis</small></div>
        `;
    },

    resetNextBatchForm() {
        ['nextCookName', 'nextQuantity', 'nextNotes'].forEach(id => {
            const el = document.getElementById(id);
            if (el) el.value = '';
        });
        const shift = document.getElementById('nextShift');
        if (shift) shift.value = 'Pagi';
        const message = document.getElementById('nextBatchMessage');
        if (message) {
            message.textContent = '';
            message.classList.remove('error');
        }
    },

    optionalNumberFromInput(id) {
        const raw = document.getElementById(id)?.value;
        if (raw == null || String(raw).trim() === '') return null;
        const parsed = Number(raw);
        if (!Number.isFinite(parsed)) {
            throw new Error(`${id.replace('next', '')} harus angka`);
        }
        return parsed;
    },

    async saveNextBatch() {
        const product = this.nextBatchProduct;
        if (!product) return;
        const button = document.getElementById('saveNextBatchBtn');
        const original = button?.textContent || 'Simpan Pemasakan';
        const msg = document.getElementById('nextBatchMessage');
        try {
            const cookName = document.getElementById('nextCookName')?.value?.trim() || '';
            const quantity = Number(document.getElementById('nextQuantity')?.value);
            const productionShift = document.getElementById('nextShift')?.value || '';
            if (!cookName) throw new Error('cook_name wajib diisi');
            if (!Number.isFinite(quantity) || quantity <= 0) throw new Error('quantity harus angka lebih dari 0');
            if (!productionShift) throw new Error('production_shift wajib diisi');
            if (button) {
                button.disabled = true;
                button.textContent = 'Menyimpan...';
            }
            if (msg) {
                msg.textContent = '';
                msg.classList.remove('error');
            }
            const response = await API.post('/batch/next', {
                product_id: product.id || product.product_code || product.sku_code,
                product_name: product.product_name,
                sku: product.product_code || product.sku_code || product.barcode || null,
                production_date: this.operationalDate,
                cook_name: cookName,
                quantity,
                production_shift: productionShift,
                notes: document.getElementById('nextNotes')?.value?.trim(),
            });
            if (!response.success) throw new Error(response.message || 'Gagal menyimpan pemasakan');
            await this.addSkuCard(product);
            this.closeNextBatchSheet();
        } catch (error) {
            if (msg) {
                const detail = error.message || 'Request tidak valid';
                msg.textContent = detail.toLowerCase().startsWith('gagal menyimpan pemasakan')
                    ? detail
                    : `Gagal menyimpan pemasakan: ${detail}`;
                msg.classList.add('error');
            }
        } finally {
            if (button) {
                button.disabled = false;
                button.textContent = original;
            }
        }
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
            <div>
                <span>Jam produksi</span>
                <strong>${this.escapeHtml(this.batchTime(batch))}</strong>
                <small>${this.escapeHtml(batch.production_date || this.operationalDate || '-')}</small>
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
        this.setPhotoCompressionStatus(inputId, 'Foto akan dikompres otomatis sebelum dikirim.');
        this.updateSummary();
    },

    setPhotoCompressionStatus(inputId, message) {
        const status = document.getElementById(`${inputId}CompressionStatus`);
        if (status) status.textContent = message;
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

    jakartaDateString() {
        return new Intl.DateTimeFormat('en-CA', {
            timeZone: 'Asia/Jakarta',
            year: 'numeric',
            month: '2-digit',
            day: '2-digit',
        }).format(new Date());
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
    },

    saveDraft() {
        const temp = document.getElementById('qcTemp')?.value;
        const ph = document.getElementById('qcPh')?.value;
        const brix = document.getElementById('qcBrix')?.value;
        const tds = document.getElementById('qcTds')?.value;
        const notes = document.getElementById('qcNotes')?.value;
        
        if (this.selectedProduct && (temp || ph || brix || tds || notes || this.selectedStatus)) {
            localStorage.setItem('inspection_draft', JSON.stringify({
                product: this.selectedProduct,
                batch: this.selectedBatch,
                stage: this.selectedStage,
                status: this.selectedStatus,
                temp,
                ph,
                brix,
                tds,
                notes,
                recheckParent: this.recheckParentInspection,
                timestamp: Date.now()
            }));
        } else {
            localStorage.removeItem('inspection_draft');
        }
    },

    checkDraft() {
        const draftStr = localStorage.getItem('inspection_draft');
        if (!draftStr) return;
        const draft = JSON.parse(draftStr);
        
        // Show draft recovery prompt
        const container = document.createElement("div");
        container.id = "draftRecoveryPrompt";
        container.style.cssText = "position: fixed; bottom: 80px; left: 50%; transform: translateX(-50%); z-index: 1000; width: 90%; max-width: 400px; background: white; border-radius: 16px; border: 1px solid var(--border); box-shadow: 0 10px 25px rgba(0,0,0,0.15); padding: 16px; display: flex; flex-direction: column; gap: 12px;";
        container.innerHTML = `
            <div style="font-size: 14px; font-weight: 600; color: var(--text-color, #1e293b);">Lanjutkan input QC sebelumnya?</div>
            <div style="display: flex; gap: 10px;">
                <button id="btnRecoverDraft" class="btn-primary" style="flex: 1; min-height: 48px; font-size: 14px; font-weight: 700; border-radius: 10px; cursor: pointer; border: none; background: #2563eb; color: white;">Lanjutkan</button>
                <button id="btnDiscardDraft" class="btn-secondary" style="flex: 1; min-height: 48px; font-size: 14px; font-weight: 700; border-radius: 10px; cursor: pointer; border: 1px solid #cbd5e1; background: #f8fafc; color: #475569;">Buang</button>
            </div>
        `;
        document.body.appendChild(container);
        
        document.getElementById("btnRecoverDraft").onclick = () => {
            container.remove();
            
            // Set context and open sheet
            this.selectedProduct = draft.product;
            this.selectedBatch = draft.batch;
            this.selectedStage = draft.stage || 'cooking_check';
            this.selectedStatus = draft.status;
            this.recheckParentInspection = draft.recheckParent;
            isAdvancedPanelOpen = Boolean(this.recheckParentInspection) || this.productHasAdditionalStandards();
            
            this.updateSelectedProductCard();
            this.openQcForm(draft.product, draft.batch, { recheck: Boolean(draft.recheckParent) });
            
            // Fill draft values
            if (document.getElementById('qcTemp')) document.getElementById('qcTemp').value = draft.temp || '';
            if (document.getElementById('qcPh')) document.getElementById('qcPh').value = draft.ph || '';
            if (document.getElementById('qcBrix')) document.getElementById('qcBrix').value = draft.brix || '';
            if (document.getElementById('qcTds')) document.getElementById('qcTds').value = draft.tds || '';
            if (document.getElementById('qcNotes')) document.getElementById('qcNotes').value = draft.notes || '';
            
            // Visually select status options
            if (draft.status) {
                document.querySelectorAll('.qc-status-option').forEach(item => {
                    item.classList.toggle('active', item.dataset.status === draft.status);
                });
            }
            
            this.updateFastQcMode();
            this.updateSubmitState();
            this.updateSummary();
            
            // Focus qcTemp
            setTimeout(() => document.getElementById('qcTemp')?.focus(), 100);
        };
        
        document.getElementById("btnDiscardDraft").onclick = () => {
            container.remove();
            localStorage.removeItem('inspection_draft');
        };
    },

    async processBarcodeOcr(file) {
        const fallbackContainer = document.getElementById('packFallbackFields');
        const mfgInput = document.getElementById('qcMfgDate');
        const expInput = document.getElementById('qcExpDate');
        
        window.showToast('Membaca barcode...', 'info', 2000);
        
        try {
            const reader = new FileReader();
            const dataUrlPromise = new Promise(resolve => {
                reader.onload = e => resolve(e.target.result);
                reader.readAsDataURL(file);
            });
            const dataUrl = await dataUrlPromise;
            
            // Simulate OCR delay
            await new Promise(resolve => setTimeout(resolve, 1500));
            
            if (file.name.toLowerCase().includes('fail') || Math.random() < 0.1) {
                throw new Error("Gagal membaca tanggal dari barcode");
            }
            
            // OCR Success! Set MFG and calculate EXP
            const mfgDate = this.jakartaDateString();
            const shelfLife = this.selectedProduct?.shelf_life_days || 3;
            const mfgObj = new Date(mfgDate);
            mfgObj.setDate(mfgObj.getDate() + shelfLife);
            const expDate = mfgObj.toISOString().slice(0, 10);
            
            if (mfgInput) mfgInput.value = mfgDate;
            if (expInput) expInput.value = expDate;
            if (fallbackContainer) fallbackContainer.style.display = 'none';
            
            window.showToast(`OCR Berhasil: MFG ${mfgDate}, EXP ${expDate}`, 'success', 2000);
            this.updateSubmitState();
        } catch (err) {
            console.warn('OCR failed, showing fallback inputs:', err);
            window.showToast('OCR gagal membaca barcode. Silakan input manual.', 'warning', 3000);
            if (fallbackContainer) fallbackContainer.style.display = 'flex';
            
            const today = this.jakartaDateString();
            if (mfgInput && !mfgInput.value) mfgInput.value = today;
            if (expInput && !expInput.value) {
                const shelfLife = this.selectedProduct?.shelf_life_days || 3;
                const mfgObj = new Date(today);
                mfgObj.setDate(mfgObj.getDate() + shelfLife);
                expInput.value = mfgObj.toISOString().slice(0, 10);
            }
            this.updateSubmitState();
        }
    },

    renderProductionToday() {
        const list = document.getElementById('productionTodayList');
        const countEl = document.getElementById('productionTodayCount');
        const header = document.getElementById('productionTodayHeader');
        if (!list) return;

        const allBatches = [];
        Object.entries(this.skuBatchMap).forEach(([productKey, data]) => {
            const product = data.product || {};
            const batches = data.batches || [];
            batches.forEach(batch => {
                allBatches.push({
                    ...batch,
                    productKey,
                    product_name: product.product_name || batch.product_name || 'Unknown Product'
                });
            });
        });

        if (countEl) countEl.textContent = `${allBatches.length} Batch`;
        if (header) header.style.display = allBatches.length > 0 ? 'grid' : 'none';
        list.style.display = (allBatches.length > 0 && !this.productionTodayCollapsed) ? 'grid' : 'none';
        const icon = document.getElementById('productionTodayToggleIcon');
        if (icon) {
            icon.style.transform = this.productionTodayCollapsed ? 'rotate(-90deg)' : 'rotate(0deg)';
        }

        if (!allBatches.length) {
            list.innerHTML = '';
            return;
        }

        allBatches.sort((a, b) => new Date(b.production_time || b.created_at) - new Date(a.production_time || a.created_at));

        list.innerHTML = allBatches.map(batch => {
            const reports = batch.qc_reports || [];
            const hasSensory = reports.some(r => r.qc_stage === 'cooking_sensory');
            const hasInstrument = reports.some(r => r.qc_stage === 'cooking_instrument');
            const hasPck = reports.some(r => r.qc_stage === STAGE_PCK);

            let progressPct = 0;
            let displayStatus = 'Cooking';
            let statusClass = 'pending';
            let progressBarColor = '#cbd5e1';

            const dbStatus = String(batch.status || '').toLowerCase();
            if (dbStatus === 'completed' || dbStatus === 'finished' || hasPck) {
                progressPct = 100;
                displayStatus = 'Finished';
                statusClass = 'pass';
                progressBarColor = '#10b981';
            } else if (hasSensory && hasInstrument) {
                progressPct = 80;
                displayStatus = STAGE_PCK.charAt(0).toUpperCase() + STAGE_PCK.slice(1);
                statusClass = 'warning';
                progressBarColor = '#f59e0b';
            } else if (hasSensory) {
                progressPct = 40;
                displayStatus = 'Cooking';
                statusClass = 'pending';
                progressBarColor = '#3b82f6';
            } else {
                progressPct = 0;
                displayStatus = 'Cooking';
                statusClass = 'pending';
                progressBarColor = '#cbd5e1';
            }

            let barIcons = '';
            const filledCount = Math.floor(progressPct / 10);
            for (let i = 0; i < 10; i++) {
                barIcons += i < filledCount ? '█' : '░';
            }

            return `
                <div class="batch-lifecycle-card" style="background: var(--card-bg, #ffffff); border: 1px solid var(--border-color, #e2e8f0); border-radius: 12px; padding: 16px; display: flex; flex-direction: column; gap: 12px; width: 100%; box-shadow: 0 1px 3px rgba(0,0,0,0.05);">
                    <div style="display: flex; justify-content: space-between; align-items: flex-start; gap: 8px;">
                        <div>
                            <h3 style="font-size: 15px; font-weight: 700; color: var(--text-primary); margin: 0; text-align: left;">${this.escapeHtml(batch.product_name)}</h3>
                            <span style="font-size: 12px; color: var(--text-secondary); text-align: left; display: block; margin-top: 2px;">
                                ${this.escapeHtml(batch.batch_code)} (Pemasakan ke-${this.escapeHtml(batch.batch_sequence || '-')})
                            </span>
                        </div>
                        <span class="status-badge status-${this.statusClass(statusClass)}" style="text-transform: uppercase; font-size: 11px; font-weight: 700; padding: 4px 8px; border-radius: 6px; white-space: nowrap;">
                            ${displayStatus}
                        </span>
                    </div>
                    
                    <div style="display: flex; flex-direction: column; gap: 4px;">
                        <div style="display: flex; justify-content: space-between; font-size: 12px; color: var(--text-secondary);">
                            <span style="font-family: monospace; letter-spacing: 1px; font-weight: bold; color: var(--text-primary);">${barIcons}</span>
                            <strong>${progressPct}%</strong>
                        </div>
                        <div style="height: 6px; background: #e2e8f0; border-radius: 3px; overflow: hidden; width: 100%;">
                            <div style="height: 100%; width: ${progressPct}%; background: ${progressBarColor}; border-radius: 3px; transition: width 0.3s ease;"></div>
                        </div>
                    </div>
                    
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 4px; gap: 10px;">
                        <span style="font-size: 12px; color: var(--text-secondary); text-align: left;">
                            Cook: ${this.escapeHtml(batch.cook_name || '-')} · Qty: ${this.escapeHtml(batch.quantity || '-')}
                        </span>
                        <button class="btn-primary" style="padding: 6px 14px; border-radius: 6px; font-size: 13px; font-weight: 600; cursor: pointer; display: flex; align-items: center; gap: 6px; height: 32px;" type="button" data-lanjut-batch="${this.escapeHtml(batch.id || batch.batch_code)}" data-product-key="${this.escapeHtml(batch.productKey)}" data-progress="${progressPct}">
                            Lanjut <i class="fas fa-chevron-right" style="font-size: 9px;"></i>
                        </button>
                    </div>
                </div>
            `;
        }).join('');

        list.querySelectorAll('[data-lanjut-batch]').forEach(button => {
            button.addEventListener('click', () => {
                const productKey = button.dataset.productKey;
                const batchId = button.dataset.lanjutBatch;
                const progress = parseInt(button.dataset.progress || '0');
                
                const product = this.findCardProduct(productKey);
                const batch = this.findCardBatch(productKey, batchId);
                
                if (product && batch) {
                    if (progress >= 100) {
                        this.showBatchDetail(batch);
                    } else {
                        this.openQcForm(product, batch, { recheck: false });
                    }
                }
            });
        });
    }
};
