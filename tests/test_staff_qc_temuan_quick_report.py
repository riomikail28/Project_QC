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


def test_qc_temuan_upload_placeholder_and_preview_status_exist():
    html = read("frontend/staff/dashboard.html")

    drawer = html.split('id="findingDrawer"', 1)[1].split('id="alertDrawer"', 1)[0]
    assert "finding-upload-card" in drawer
    assert "Belum ada foto" in drawer
    assert "Tap untuk ambil foto evidence" in drawer
    assert "Upload Foto" in drawer
    assert "findingPhotoMeta" in drawer
    assert "findingPhotoReady" in drawer
    assert "Foto siap dikirim" in drawer
    assert "Foto akan dikompres otomatis sebelum dikirim." in drawer


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
    assert "await API.upload('/qc/findings', formData)" in html
    assert "selectedFindingPhotos.forEach(file => formData.append('photo', file))" in html


def test_qc_temuan_mobile_drawer_is_bounded_scrollable_and_sticky():
    css = read("frontend/styles/alerts.css")

    assert "#findingDrawer" in css and "max-height: 90vh;" in css
    assert "#findingDrawer .alert-drawer-body" in css
    assert "overflow-y: auto;" in css
    assert "padding-bottom: 120px;" in css
    assert ".alert-drawer-header" in css and "position: sticky;" in css and "top: 0;" in css
    assert ".alert-drawer-footer" in css and "position: sticky;" in css and "bottom: 0;" in css
    assert "#findingDrawer .finding-preview" in css and "min-height: 108px;" in css
    assert "#findingImg" in css and "object-fit: contain;" in css


def test_qc_temuan_mobile_header_chips_textarea_and_footer_are_compact():
    html = read("frontend/staff/dashboard.html")
    css = read("frontend/styles/alerts.css")

    assert "Laporkan temuan QC" in html
    assert "#findingDrawer .alert-drawer-title h3" in css and "font-size: 18px;" in css
    assert "#findingDrawer .alert-drawer-header" in css and "padding-bottom: 8px;" in css
    assert "#findingDrawer .finding-category-chip" in css
    assert "min-height: 28px;" in css
    assert "max-width: 46%;" in css
    assert 'id="findingReason" rows="3"' in html
    assert "Opsional kecuali kategori Lainnya" in html
    assert "function autoResizeFindingReason(textarea)" in html
    assert 'oninput="autoResizeFindingReason(this)"' in html
    assert "#findingDrawer .alert-drawer-footer .btn-primary" in css and "min-height: 40px;" in css


def test_qc_temuan_scroll_hint_hides_after_scroll():
    html = read("frontend/staff/dashboard.html")
    css = read("frontend/styles/alerts.css")

    assert "findingScrollHint" in html
    assert "Scroll untuk melihat form lainnya" in html
    assert "function resetFindingScrollHint()" in html
    assert "function dismissFindingScrollHint()" in html
    assert "body.addEventListener('scroll', dismissFindingScrollHint, { passive: true })" in html
    assert ".show-scroll-hint::after" in css


def test_qc_temuan_category_textarea_and_submit_still_work():
    html = read("frontend/staff/dashboard.html")

    assert "function selectFindingCategory(category)" in html
    assert "selectedFindingCategory = category" in html
    assert "category === 'Lainnya' && !reason" in html
    assert "function submitQcFinding()" in html
    assert "const findingText = composeFindingReason(category, reason)" in html
    assert "formData.append('reason', findingText)" in html
    assert "staffToast('Temuan berhasil dikirim', 'success')" in html


def test_monitoring_toast_cleanup_has_no_alert_fallback():
    js = read("frontend/js/monitoring.js")

    assert "showMonitoringToast(err.message || \"Upload foto gagal\", true)" in js
    assert "alert(message)" not in js
