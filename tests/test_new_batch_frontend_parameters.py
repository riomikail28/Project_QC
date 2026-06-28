from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_new_batch_frontend_includes_optional_ph_brix_tds_fields():
    html = (ROOT / "frontend" / "staff" / "new_batch.html").read_text(encoding="utf-8")

    assert "Parameter Opsional" in html
    assert 'id="phValue"' in html
    assert 'id="brixValue"' in html
    assert 'id="tdsValue"' in html
    assert "Standar pH" in html
    assert "Standar Brix" in html
    assert "Standar TDS" in html
    assert "ph_value" in html
    assert "brix_value" in html
    assert "tds_value" in html


def test_new_batch_frontend_uses_inline_error_not_alert():
    html = (ROOT / "frontend" / "staff" / "new_batch.html").read_text(encoding="utf-8")

    assert 'id="newBatchMessage"' in html
    assert "showBatchMessage" in html
    assert "alert(" not in html


def test_new_batch_batch_code_is_optional_with_auto_helper():
    html = (ROOT / "frontend" / "staff" / "new_batch.html").read_text(encoding="utf-8")

    assert 'placeholder="Batch code otomatis"' in html
    assert "Format otomatis: SKU-YYYYMMDD-urutan pemasakan." in html
    assert "/batch/next-code" in html
    assert "payload.batch_code" not in html


def test_staff_pages_include_quick_action_menu():
    for page in ("dashboard.html", "inspection.html", "monitoring.html", "new_batch.html"):
        html = (ROOT / "frontend" / "staff" / page).read_text(encoding="utf-8")

        assert "data-quick-actions" in html
        assert "data-quick-actions-trigger" in html
        assert "QC Temuan" in html
        if page != "dashboard.html":
            assert "Buat Batch" in html
        assert "QC Check" in html
        assert "Monitoring" in html
        assert "../js/quick-actions.js" in html
