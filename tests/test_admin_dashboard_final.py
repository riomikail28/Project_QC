from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(path):
    return (ROOT / path).read_text(encoding="utf-8")


def test_dashboard_final_sections_exist():
    html = read("frontend/admin/admin_panel.html")

    overview = html.split('id="section-overview"', 1)[1].split('id="section-monitoring"', 1)[0]
    for text in (
        "QC Enterprise Command Center",
        "Ringkasan operasional QC Central Kitchen hari ini.",
        "Need Attention",
        "Staff Aktif Hari Ini",
        "Today QC Summary",
        "Monitoring Slot Completion",
        "Production QC Snapshot",
        "Recent Activity",
    ):
        assert text in overview


def test_dashboard_final_js_renders_command_center_widgets():
    js = read("frontend/js/admin_app.js")

    for symbol in (
        "renderNeedAttention",
        "renderActiveStaff",
        "renderQcSummary",
        "renderMonitoringSlotCompletion",
        "renderProductionSnapshot",
        "renderRecentActivity",
        "Semua aman",
        "Belum ada staff aktif hari ini.",
    ):
        assert symbol in js


def test_admin_header_is_clean_without_global_search_theme_or_bell():
    html = read("frontend/admin/admin_panel.html")

    topbar = html.split('<header class="admin-topbar">', 1)[1].split("</header>", 1)[0]
    assert "admin-search" not in topbar
    assert "theme-toggle" not in topbar
    assert 'data-lucide="bell"' not in topbar
    assert "alert-badge" not in topbar
    assert "user-profile" in topbar


def test_photo_preview_has_higher_z_index_than_regular_admin_modal():
    html = read("frontend/admin/admin_panel.html")
    css = read("frontend/css/admin_enterprise.css")

    assert "admin-photo-preview-overlay" in html
    assert "admin-photo-preview-modal" in html
    assert ".enterprise-modal" in css and "z-index: 100;" in css
    assert ".admin-photo-preview-overlay" in css and "z-index: 3000;" in css
    assert ".admin-photo-preview-modal" in css and "z-index: 3001;" in css


def test_production_board_hidden_status_filter_supports_dashboard_ctas():
    html = read("frontend/admin/admin_panel.html")
    js = read("frontend/js/admin_app.js")

    assert 'id="batch-production-status" hidden' in html
    assert "openProductionBoardFiltered('pending approval')" in js
    assert "openProductionBoardFiltered('hold')" in js
    assert "openProductionBoardFiltered(status = '')" in js
