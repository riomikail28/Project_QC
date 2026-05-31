from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_qc_check_product_picker_is_compact_search_first():
    html = (ROOT / "frontend" / "staff" / "inspection.html").read_text(encoding="utf-8")
    js = (ROOT / "frontend" / "js" / "inspection.js").read_text(encoding="utf-8")

    # Helper text present exactly once in HTML
    assert html.count("Ketik minimal 2 huruf") == 1
    assert "Ketik minimal 2 huruf untuk mencari produk." in html
    assert "query.length < 2" in js
    assert "matches.slice(0, 5)" in js
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
    assert "+ Tambah Catatan" in html
    assert "notesWrap" in html
    assert "capture=\"environment\"" in html


def test_qc_check_helper_text_not_duplicated():
    """Helper text 'Ketik minimal 2 huruf' must appear exactly once in HTML."""
    html = (ROOT / "frontend" / "staff" / "inspection.html").read_text(encoding="utf-8")
    assert html.count("Ketik minimal 2 huruf") == 1


def test_qc_check_progressive_disclosure_fields_hidden_initially():
    """Stage, status, and notes fields should be hidden until product is selected."""
    html = (ROOT / "frontend" / "staff" / "inspection.html").read_text(encoding="utf-8")
    js = (ROOT / "frontend" / "js" / "inspection.js").read_text(encoding="utf-8")

    assert 'id="stageField" hidden' in html
    assert 'id="statusField" hidden' in html
    assert 'id="notesField" hidden' in html
    assert "updateProgressiveFields" in js


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


def test_qc_check_sku_card_workflow_contract():
    html = (ROOT / "frontend" / "staff" / "inspection.html").read_text(encoding="utf-8")
    js = (ROOT / "frontend" / "js" / "inspection.js").read_text(encoding="utf-8")

    assert "Pilih atau tambahkan SKU untuk mulai pengecekan." in html
    assert "skuEmptyState" in html
    assert "openSkuSearch" in js
    assert "addSkuCard" in js
    assert "batchListTemplate" in js
    assert "data-qc-batch" in js
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

    assert "skuEmptyState" in html
    assert "empty.hidden = Boolean(this.skuCards.length)" in js


def test_qc_check_manual_add_sku_dedupes_existing_card():
    js = (ROOT / "frontend" / "js" / "inspection.js").read_text(encoding="utf-8")

    assert "!this.skuCards.some(item => this.productKey(item) === productKey)" in js


def test_qc_check_manual_sku_only_fallback():
    """Manual SKU input should not be visible from the start."""
    html = (ROOT / "frontend" / "staff" / "inspection.html").read_text(encoding="utf-8")
    js = (ROOT / "frontend" / "js" / "inspection.js").read_text(encoding="utf-8")

    assert 'id="manualSkuWrap" hidden' in html
    assert "toggleManualMode" in js
    assert "Input SKU manual" in js
