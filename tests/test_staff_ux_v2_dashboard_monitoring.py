from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read(path):
    return (ROOT / path).read_text(encoding="utf-8")


def test_staff_dashboard_task_first_sections_before_analytics():
    html = read("frontend/staff/dashboard.html")

    task_index = html.index("Tugas Saya Sekarang")
    quick_index = html.index("Quick Action")
    summary_index = html.index("Ringkasan Hari Ini")
    health_index = html.index("dashboard-hero")
    chart_index = html.index("productionTrendChart")

    assert task_index < quick_index < summary_index < health_index < chart_index
    assert "Monitoring Slot Aktif" in html
    assert "Batch Menunggu QC" in html
    assert "Re-check Pending" in html
    assert "QC Temuan Open" in html


def test_staff_dashboard_compact_actions_and_kpis_exist():
    html = read("frontend/staff/dashboard.html")
    js = read("frontend/js/dashboard.js")

    assert "staff-quick-grid" in html
    assert "Monitoring selesai" in html
    assert "Batch selesai QC" in html
    assert "Temuan hari ini" in html
    assert "PASS Rate" in html
    assert "renderTaskNow" in js
    assert "renderCompactToday" in js
    assert "/facility/monitoring/schedule/today" in js


def test_smart_monitoring_next_device_and_room_progress_sections_exist():
    html = read("frontend/staff/monitoring.html")

    schedule_index = html.index("scheduleSlotGrid")
    next_index = html.index("Device Berikutnya Untuk Dicek")
    progress_index = html.index("Progress Area")
    filters_index = html.index("Filter")

    assert schedule_index < next_index < progress_index < filters_index
    assert "nextDeviceAction" in html
    assert "roomProgressList" in html


def test_smart_monitoring_groups_devices_by_collapsible_room():
    js = read("frontend/js/monitoring.js")
    css = read("frontend/styles/monitoring.css")

    assert "renderMonitoringRoomGroup" in js
    assert "toggleRoomGroup" in js
    assert "monitor-room-group" in js
    assert "monitor-device-list" in js
    assert ".monitor-room-group" in css
    assert ".monitor-device-list.is-collapsed" in css


def test_smart_monitoring_sort_priority_and_device_metadata():
    js = read("frontend/js/monitoring.js")

    assert "function sortMonitoringDevices" in js
    assert 'scheduleStatus === "pending") return 1' in js
    assert 'scheduleStatus === "missed" || scheduleStatus === "late") return 2' in js
    assert "isDeviceAlert(device)) return 3" in js
    assert 'scheduleStatus === "completed") return 4' in js
    assert "lastInputMeta(device)" in js
    assert "Foto wajib jika abnormal" in js
    assert "Foto opsional" in js


def test_monitoring_submit_flow_and_bottom_navigation_unchanged():
    html = read("frontend/staff/monitoring.html")
    js = read("frontend/js/monitoring.js")

    assert 'class="bottom-nav"' in html
    assert 'id="monitoring-form"' in html
    assert 'id="selected-slot-time"' in html
    assert 'API.upload("/facility/monitoring/submit", formData)' in js
    assert 'formData.append("slot_time"' in js
