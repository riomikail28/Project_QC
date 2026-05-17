from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_qc_check_product_picker_is_compact_search_first():
    html = (ROOT / "frontend" / "staff" / "inspection.html").read_text(encoding="utf-8")
    js = (ROOT / "frontend" / "js" / "inspection.js").read_text(encoding="utf-8")

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
    assert "Input SKU manual" in html


def test_qc_check_mobile_upload_notes_and_submit_spacing_contract():
    html = (ROOT / "frontend" / "staff" / "inspection.html").read_text(encoding="utf-8")
    css = (ROOT / "frontend" / "styles" / "qc.css").read_text(encoding="utf-8")
    js = (ROOT / "frontend" / "js" / "inspection.js").read_text(encoding="utf-8")

    assert "inspection-page" in html
    assert "padding-bottom: 120px" in css
    assert "bottom: 94px" in css
    assert "photo-preview" in html
    assert "renderPhotoPreview" in js
    assert "+ Tambah catatan opsional" in html
    assert "notesWrap" in html
