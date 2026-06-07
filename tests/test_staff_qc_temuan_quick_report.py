from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read(path):
    return (ROOT / path).read_text(encoding="utf-8")


def test_qc_temuan_has_quick_category_chips():
    html = read("frontend/staff/dashboard.html")

    assert "findingCategoryChips" in html
    for category in [
        "Suhu tidak sesuai",
        "Area kotor",
        "Benda asing",
        "Label salah",
        "Kemasan rusak",
        "Alat rusak",
        "Lainnya",
    ]:
        assert f'data-category="{category}"' in html


def test_qc_temuan_chip_selection_marks_category_and_updates_note_prompt():
    html = read("frontend/staff/dashboard.html")

    assert "function selectFindingCategory(category)" in html
    assert "selectedFindingCategory = category" in html
    assert "button.classList.toggle('active', active)" in html
    assert "button.setAttribute('aria-checked', active ? 'true' : 'false')" in html
    assert "Kategori dipilih:" in html


def test_qc_temuan_lainnya_requires_manual_note():
    html = read("frontend/staff/dashboard.html")

    assert "category === 'Lainnya' && !reason" in html
    assert "Catatan tambahan wajib untuk kategori Lainnya." in html
    assert "Tulis detail temuan secara manual." in html


def test_qc_temuan_drawer_has_no_qc_check_cta():
    drawer = read("frontend/staff/dashboard.html").split('id="findingDrawer"', 1)[1].split('id="alertDrawer"', 1)[0]

    assert "Buka QC Check" not in drawer
    assert "inspection.html" not in drawer


def test_qc_temuan_does_not_use_blocking_alerts():
    drawer_script = read("frontend/staff/dashboard.html").split("function openQcFinding", 1)[1].split("async function resolveAlertInDrawer", 1)[0]

    assert "alert(" not in drawer_script
    assert "staffToast(" in drawer_script


def test_toast_utility_available_for_staff_pages():
    js = read("frontend/js/ui-mobile.js")
    dashboard = read("frontend/staff/dashboard.html")
    monitoring = read("frontend/staff/monitoring.html")

    assert "window.showToast = function showToast" in js
    assert "../js/ui-mobile.js" in dashboard
    assert "../js/ui-mobile.js" in monitoring


def test_qc_temuan_success_and_failure_use_toast():
    html = read("frontend/staff/dashboard.html")

    assert "Temuan berhasil dikirim" in html
    assert "Temuan gagal dikirim" in html
    assert "Upload foto gagal" in html
    assert "Foto evidence disarankan untuk QC Temuan." in html


def test_qc_temuan_payload_includes_category_status_and_prefixed_finding():
    html = read("frontend/staff/dashboard.html")

    assert "composeFindingReason(category, reason)" in html
    assert "return `[${cleanCategory}] ${cleanCategory}`" in html
    assert "return `[${cleanCategory}] ${cleanNote}`" in html
    assert "formData.append('reason', findingText)" in html
    assert "formData.append('finding', findingText)" in html
    assert "formData.append('temuan', findingText)" in html
    assert "formData.append('category', category || 'Lainnya')" in html
    assert "formData.append('status', 'open')" in html


def test_monitoring_toast_cleanup_has_no_alert_fallback():
    js = read("frontend/js/monitoring.js")

    assert "showMonitoringToast(err.message || \"Upload foto gagal\", true)" in js
    assert "alert(message)" not in js
