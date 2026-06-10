from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_qc_check_product_picker_is_compact_search_first():
    html = (ROOT / "frontend" / "staff" / "inspection.html").read_text(encoding="utf-8")
    js = (ROOT / "frontend" / "js" / "inspection.js").read_text(encoding="utf-8")

    # Helper text present exactly once in HTML
    assert html.count("Ketik minimal 2 huruf") == 1
    assert "Klik field untuk melihat daftar SKU. Ketik minimal 2 huruf untuk filter." in html
    assert 'role="combobox"' in html
    assert "normalized.length >= 2" in js
    assert "renderProductDropdown" in js
    assert "products.slice(0, 15)" in js
    assert "this.renderProductOptions(this.products.slice" not in js


def test_qc_check_selected_product_and_manual_fallback_are_separated():
    html = (ROOT / "frontend" / "staff" / "inspection.html").read_text(encoding="utf-8")
    js = (ROOT / "frontend" / "js" / "inspection.js").read_text(encoding="utf-8")

    assert "selectedProductCard" in html
    assert "Ganti Produk" in js
    assert "manualSkuWrap" in html
    # Manual SKU toggle rendered dynamically in JS when no results found
    assert "Input SKU manual" in js


def test_qc_check_mobile_upload_notes_and_submit_spacing_contract():
    html = (ROOT / "frontend" / "staff" / "inspection.html").read_text(encoding="utf-8")
    css = (ROOT / "frontend" / "styles" / "qc.css").read_text(encoding="utf-8")
    js = (ROOT / "frontend" / "js" / "inspection.js").read_text(encoding="utf-8")

    assert "inspection-page" in html
    assert "padding-bottom: 120px" in css
    assert "bottom: 94px" in css
    assert "photo-preview" in html
    assert "renderPhotoPreview" in js
    assert "Catatan" in html
    assert "capture=\"environment\"" in html
    assert "padding-bottom: max(128px" in css


def test_qc_check_helper_text_not_duplicated():
    """Helper text 'Ketik minimal 2 huruf' must appear exactly once in HTML."""
    html = (ROOT / "frontend" / "staff" / "inspection.html").read_text(encoding="utf-8")
    assert html.count("Ketik minimal 2 huruf") == 1


def test_qc_check_progressive_disclosure_fields_hidden_initially():
    """QC fields should be hidden until a batch context is selected."""
    html = (ROOT / "frontend" / "staff" / "inspection.html").read_text(encoding="utf-8")
    js = (ROOT / "frontend" / "js" / "inspection.js").read_text(encoding="utf-8")

    assert 'id="cookingFields" hidden' in html
    assert 'id="statusField" hidden' in html
    assert 'id="notesField" hidden' in html
    assert "updateProgressiveFields" in js
    assert "if (stageField) stageField.hidden = true" in js


def test_qc_check_compact_upload_cards():
    """Upload should use compact card layout, not tall upload-zone."""
    html = (ROOT / "frontend" / "staff" / "inspection.html").read_text(encoding="utf-8")
    css = (ROOT / "frontend" / "styles" / "qc.css").read_text(encoding="utf-8")

    assert "upload-card-compact" in html
    assert "upload-card-compact" in css
    assert "Ambil Foto" in html


def test_qc_check_field_mobile_ux_has_step_summary_and_context():
    html = (ROOT / "frontend" / "staff" / "inspection.html").read_text(encoding="utf-8")
    css = (ROOT / "frontend" / "styles" / "qc.css").read_text(encoding="utf-8")
    js = (ROOT / "frontend" / "js" / "inspection.js").read_text(encoding="utf-8")

    assert "Tambah Produk / SKU" in html
    assert "skuCardGrid" in html
    assert "sku-card-grid" in css
    assert "qcSubmitSummary" in html
    assert "qcFormSheet" in html
    assert "updateSummary" in js
    assert "renderSkuCards" in js
    assert "rememberRecentSubmission" in js
    assert ".qc-status-option" in css
    assert "min-height: 76px" in css
    assert "min-height: 58px" in css


def test_qc_check_sku_card_workflow_contract():
    html = (ROOT / "frontend" / "staff" / "inspection.html").read_text(encoding="utf-8")
    js = (ROOT / "frontend" / "js" / "inspection.js").read_text(encoding="utf-8")

    assert "Cari SKU, pilih produk, lalu pilih batch untuk QC Check." in html
    assert "skuEmptyNote" in html
    assert "openSkuSearch" in js
    assert "addSkuCard" in js
    assert "batchListTemplate" in js
    assert "data-sku-detail" in js
    assert "openSkuDetail" in js
    assert "renderSkuDetailDrawer" in js
    assert "Tambah Re-check" in js
    assert "Lihat Hasil" in js
    assert "openQcForm" in js


def test_qc_check_mobile_fab_and_bottom_nav_remain():
    html = (ROOT / "frontend" / "staff" / "inspection.html").read_text(encoding="utf-8")

    assert "fab-container" in html
    assert "bottom-nav" in html
    assert "data-quick-actions" in html


def test_qc_modal_has_scrollable_body_and_sticky_footer():
    html = (ROOT / "frontend" / "staff" / "inspection.html").read_text(encoding="utf-8")
    css = (ROOT / "frontend" / "styles" / "qc.css").read_text(encoding="utf-8")

    assert "qc-form-body" in html
    assert "qc-form-footer" in html
    assert "overflow-y: auto" in css
    assert "overflow-x: hidden" in css
    assert "position: sticky" in css
    assert "bottom: 0" in css
    assert "max-height: 90vh" in css
    assert "padding: 12px 14px max(96px" in css


def test_qc_check_mobile_cards_and_actions_are_compact():
    css = (ROOT / "frontend" / "styles" / "qc.css").read_text(encoding="utf-8")

    assert ".sku-card" in css and "padding: 12px;" in css
    assert ".sku-card-head h2" in css and "font-size: 17px;" in css
    assert ".batch-card" in css and "padding: 10px;" in css
    assert ".add-sku-btn" in css and "min-height: 44px;" in css
    assert ".qc-form-footer .btn-secondary" in css and "min-height: 44px;" in css


def test_qc_modal_close_cancel_and_escape_contract():
    html = (ROOT / "frontend" / "staff" / "inspection.html").read_text(encoding="utf-8")
    js = (ROOT / "frontend" / "js" / "inspection.js").read_text(encoding="utf-8")

    assert "qcSheetCloseBtn" in html
    assert "qcCancelBtn" in html
    assert "Cancel" in html
    assert "event.key === 'Escape'" in js
    assert "closeQcSheet" in js


def test_qc_modal_ph_brix_tds_responsive_and_no_horizontal_overflow():
    html = (ROOT / "frontend" / "staff" / "inspection.html").read_text(encoding="utf-8")
    css = (ROOT / "frontend" / "styles" / "qc.css").read_text(encoding="utf-8")

    assert "qcPh" in html
    assert "qcBrix" in html
    assert "qcTds" in html
    assert ".qc-optional-grid" in css
    assert "grid-template-columns: repeat(3, minmax(0, 1fr))" in css
    assert "grid-template-columns: 1fr" in css
    assert "overflow-x: hidden" in css


def test_qc_modal_existing_submit_button_still_exists():
    html = (ROOT / "frontend" / "staff" / "inspection.html").read_text(encoding="utf-8")
    js = (ROOT / "frontend" / "js" / "inspection.js").read_text(encoding="utf-8")

    assert 'id="submitQcBtn"' in html
    assert "Simpan QC" in html
    assert "bindSubmit" in js
    assert "submitQc(button)" in js


def test_qc_modal_hidden_by_default_and_not_active_initially():
    html = (ROOT / "frontend" / "staff" / "inspection.html").read_text(encoding="utf-8")
    css = (ROOT / "frontend" / "styles" / "qc.css").read_text(encoding="utf-8")

    assert 'id="qcFormSheet" hidden aria-hidden="true"' in html
    assert 'id="qcFormBackdrop" hidden aria-hidden="true"' in html
    assert 'qc-form-sheet open' not in html
    assert 'qc-form-sheet active' not in html
    assert 'qc-sheet-backdrop open' not in html
    assert ".qc-form-sheet[hidden]" in css
    assert "display: none !important" in css


def test_qc_modal_has_no_query_param_auto_open():
    js = (ROOT / "frontend" / "js" / "inspection.js").read_text(encoding="utf-8")

    assert "openQcModal" not in js
    assert "openBatchModal" not in js
    assert "URLSearchParams" not in js
    assert "location.search" not in js
    assert "batch_id" in js


def test_qc_batch_action_opens_modal_and_close_hides_it():
    js = (ROOT / "frontend" / "js" / "inspection.js").read_text(encoding="utf-8")

    assert "data-qc-batch" in js
    assert "data-recheck-batch" in js
    assert "this.openQcForm(product, batch" in js
    assert "sheet.hidden = false" in js
    assert "sheet.setAttribute('aria-hidden', 'false')" in js
    assert "sheet.classList.add('open', 'active')" in js
    assert "sheet.hidden = true" in js
    assert "sheet.setAttribute('aria-hidden', 'true')" in js
    assert "sheet.classList.remove('open', 'active')" in js


def test_qc_check_operational_date_contract():
    html = (ROOT / "frontend" / "staff" / "inspection.html").read_text(encoding="utf-8")
    js = (ROOT / "frontend" / "js" / "inspection.js").read_text(encoding="utf-8")

    assert "qcOperationalDate" in html
    assert "Tanggal QC:" in js
    assert "timeZone: 'Asia/Jakarta'" in js
    assert "operational_date" in js
    assert "?date=" in js
    assert "todayBatches" in js
    assert "loadTodaySkuCards" in js
    assert "/batch/today?date=" in js


def test_qc_check_clears_stale_selected_batch_when_date_changes():
    js = (ROOT / "frontend" / "js" / "inspection.js").read_text(encoding="utf-8")

    assert "resetStaleOperationalState" in js
    assert "qc_operational_date" in js
    assert "qc_selected_batch" in js
    assert "sessionStorage.removeItem" in js
    assert "location.search" not in js


def test_qc_check_auto_renders_today_sku_cards_before_manual_add():
    js = (ROOT / "frontend" / "js" / "inspection.js").read_text(encoding="utf-8")

    assert "await this.loadTodaySkuCards()" in js
    assert "response?.data?.products" in js
    assert "this.skuCards.push(product)" in js
    assert "this.skuBatchMap[key]" in js


def test_qc_check_empty_state_only_when_no_today_products():
    html = (ROOT / "frontend" / "staff" / "inspection.html").read_text(encoding="utf-8")
    js = (ROOT / "frontend" / "js" / "inspection.js").read_text(encoding="utf-8")

    assert "Belum ada SKU dipilih" not in html
    assert "empty-icon" not in html
    assert "skuEmptyNote" in html
    assert "Belum ada SKU hari ini." in html
    assert "empty.hidden = Boolean(this.skuCards.length)" in js


def test_qc_check_manual_add_sku_dedupes_existing_card():
    js = (ROOT / "frontend" / "js" / "inspection.js").read_text(encoding="utf-8")

    assert "!this.skuCards.some(item => this.productKey(item) === productKey)" in js


def test_qc_check_next_batch_action_is_inside_sku_card():
    html = (ROOT / "frontend" / "staff" / "inspection.html").read_text(encoding="utf-8")
    js = (ROOT / "frontend" / "js" / "inspection.js").read_text(encoding="utf-8")

    assert 'class="qc-form-sheet next-batch-sheet"' in html
    assert "qc-form-head" in html
    assert "qc-form-body" in html
    assert "qc-form-footer" in html
    assert "Simpan Pemasakan" in html
    assert "skuDetailNextBatchBtn" in html
    assert "document.getElementById('skuDetailNextBatchBtn')" in js
    assert "+ Tambah Pemasakan Berikutnya" in js
    assert "+ Buat Pemasakan ke-1" in js
    assert "saveNextBatch" in js
    assert "API.post('/batch/next'" in js


def test_qc_check_next_batch_payload_is_valid_batch_create_shape():
    js = (ROOT / "frontend" / "js" / "inspection.js").read_text(encoding="utf-8")
    html = (ROOT / "frontend" / "staff" / "inspection.html").read_text(encoding="utf-8")
    save_block = js[js.index("async saveNextBatch()"):js.index("renderBatchSummary", js.index("async saveNextBatch()"))]

    assert "quantity," in js
    assert "const quantity = Number(document.getElementById('nextQuantity')?.value)" in js
    assert "`Gagal menyimpan pemasakan: ${detail}`" in js
    assert "await this.addSkuCard(product)" in js
    assert "qc_status" not in save_block
    assert "ph:" not in save_block
    assert "brix:" not in save_block
    assert "tds:" not in save_block
    assert "nextPh" not in html
    assert "nextBrix" not in html
    assert "nextTds" not in html


def test_qc_check_search_dropdown_radio_list_contract():
    html = (ROOT / "frontend" / "staff" / "inspection.html").read_text(encoding="utf-8")
    js = (ROOT / "frontend" / "js" / "inspection.js").read_text(encoding="utf-8")
    css = (ROOT / "frontend" / "styles" / "qc.css").read_text(encoding="utf-8")

    assert "productPickerList" in html
    assert "role', 'radio'" in js
    assert "aria-checked" in js
    assert "product-radio-dot" in js
    assert "products.length > 15" in js
    assert "normalized.length >= 2" in js
    assert "document.addEventListener('click'" in js
    assert "event.key === 'Escape' && !document.getElementById('skuSearchPanel')?.hidden" in js
    assert ".product-radio-dot" in css


def test_qc_check_final_modal_form_contract_for_every_batch():
    html = (ROOT / "frontend" / "staff" / "inspection.html").read_text(encoding="utf-8")
    js = (ROOT / "frontend" / "js" / "inspection.js").read_text(encoding="utf-8")

    assert "QC CHECK" in html
    assert "Batch #${batch.batch_sequence || '-'}" in js
    assert "SUHU MASAK" in html
    assert 'id="qcTemp"' in html
    assert 'placeholder="Contoh: 82.0 C"' in html
    assert 'step="0.1"' in html
    assert 'id="qcPh"' in html
    assert 'id="qcBrix"' in html
    assert 'id="qcTds"' in html
    assert "PASS" in html and "HOLD" in html and "FAIL" in html
    assert "Foto evidence" in html
    assert 'id="qcNotes"' in html
    assert "this.selectedStage = 'cooking_check'" in js
    assert "this.openQcForm(product, batch, { recheck: false })" in js
    assert "this.openQcForm(product, batch, { recheck: true })" in js


def test_qc_check_cooking_temperature_validation_and_payload_contract():
    js = (ROOT / "frontend" / "js" / "inspection.js").read_text(encoding="utf-8")

    assert "Suhu masak wajib diisi untuk Cek Masakan." in js
    assert "const temperatureValue = temperature === '' || temperature == null ? null : Number(temperature)" in js
    assert "this.selectedStage === 'cooking_check' && temperatureValue == null" in js
    assert "formData.append('temperature', String(temperatureValue))" in js


def test_qc_check_next_batch_error_message_is_not_double_prefixed():
    js = (ROOT / "frontend" / "js" / "inspection.js").read_text(encoding="utf-8")

    assert "startsWith('gagal menyimpan pemasakan')" in js


def test_qc_check_next_batch_modal_has_required_summary_cards():
    html = (ROOT / "frontend" / "staff" / "inspection.html").read_text(encoding="utf-8")
    js = (ROOT / "frontend" / "js" / "inspection.js").read_text(encoding="utf-8")
    css = (ROOT / "frontend" / "styles" / "qc.css").read_text(encoding="utf-8")

    assert 'class="qc-batch-summary next-batch-summary"' in html
    assert "Produk</span>" in js
    assert "SKU</span>" in js
    assert "Tanggal QC</span>" in js
    assert "Pemasakan</span>" in js
    assert "Batch code</span>" in js
    assert ".next-batch-summary" in css
    assert ".qc-form-head" in css
    assert ".qc-form-footer" in css


def test_qc_check_legacy_selected_product_section_removed():
    html = (ROOT / "frontend" / "staff" / "inspection.html").read_text(encoding="utf-8")

    assert "Produk dipilih" not in html
    assert "selected-product-card" not in html


def test_qc_check_batch_one_and_two_render_in_single_sku_template():
    js = (ROOT / "frontend" / "js" / "inspection.js").read_text(encoding="utf-8")

    assert "Batch #${index + 1}" in js
    assert "this.batchListTemplate(productKey, batches)" in js
    assert "skuCardTemplate(product)" in js


def test_qc_check_mobile_v3_sku_list_is_compact_and_searchable():
    html = (ROOT / "frontend" / "staff" / "inspection.html").read_text(encoding="utf-8")
    js = (ROOT / "frontend" / "js" / "inspection.js").read_text(encoding="utf-8")

    assert "SKU HARI INI" in html
    assert "skuTodayCount" in html
    assert "skuListSearch" in html
    assert "Search SKU" in html
    assert "filteredSkuCards" in js
    assert "this.skuListQuery = event.target.value || ''" in js
    assert "name.includes(query) || code.includes(query)" in js
    assert "skuSummaryLine(batches, summary)" in js
    assert "Cook" not in js[js.index("skuCardTemplate(product)"):js.index("filteredSkuCards()", js.index("skuCardTemplate(product)"))]
    assert "Qty" not in js[js.index("skuCardTemplate(product)"):js.index("filteredSkuCards()", js.index("skuCardTemplate(product)"))]
    assert "pH" not in js[js.index("skuCardTemplate(product)"):js.index("filteredSkuCards()", js.index("skuCardTemplate(product)"))]


def test_qc_check_mobile_v3_sku_detail_drawer_and_batch_list():
    html = (ROOT / "frontend" / "staff" / "inspection.html").read_text(encoding="utf-8")
    js = (ROOT / "frontend" / "js" / "inspection.js").read_text(encoding="utf-8")
    css = (ROOT / "frontend" / "styles" / "qc.css").read_text(encoding="utf-8")

    assert "skuDetailDrawer" in html
    assert "skuDetailTitle" in html
    assert "skuDetailCode" in html
    assert "skuDetailCategory" in html
    assert "skuDetailBatchList" in html
    assert "Batch List" in html
    assert "openSkuDetail(productKey)" in js
    assert "closeSkuDetail()" in js
    assert "renderSkuDetailDrawer(productKey)" in js
    assert "batch-card-compact" in js
    assert "data-qc-batch" in js
    assert "data-recheck-batch" in js
    assert ".sku-detail-drawer" in css
    assert "max-height: 90vh" in css


def test_qc_check_mobile_v3_batch_click_opens_existing_qc_form():
    js = (ROOT / "frontend" / "js" / "inspection.js").read_text(encoding="utf-8")

    assert "this.openQcForm(product, batch, { recheck: false })" in js
    assert "this.openQcForm(product, batch, { recheck: true })" in js
    assert "async submitQc(button)" in js
    assert "await API.upload('/inspection/submit', formData)" in js
    assert "formData.append('parent_inspection', this.recheckParentInspection)" in js


def test_qc_check_manual_sku_only_fallback():
    """Manual SKU input should not be visible from the start."""
    html = (ROOT / "frontend" / "staff" / "inspection.html").read_text(encoding="utf-8")
    js = (ROOT / "frontend" / "js" / "inspection.js").read_text(encoding="utf-8")

    assert 'id="manualSkuWrap" hidden' in html
    assert "toggleManualMode" in js
    assert "Input SKU manual" in js
