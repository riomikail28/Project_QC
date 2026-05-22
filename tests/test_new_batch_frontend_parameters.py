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
