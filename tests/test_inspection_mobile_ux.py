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


def test_qc_check_manual_sku_only_fallback():
    """Manual SKU input should not be visible from the start."""
    html = (ROOT / "frontend" / "staff" / "inspection.html").read_text(encoding="utf-8")
    js = (ROOT / "frontend" / "js" / "inspection.js").read_text(encoding="utf-8")

    assert 'id="manualSkuWrap" hidden' in html
    assert "toggleManualMode" in js
    assert "Input SKU manual" in js
