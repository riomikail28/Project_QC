from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read(path):
    return (ROOT / path).read_text(encoding="utf-8")


def test_monitoring_management_uses_grouped_room_row_list_layout():
    html = read("frontend/admin/admin_panel.html")
    js = read("frontend/js/admin_app.js")
    css = read("frontend/css/admin_enterprise.css")

    assert "monitoring-room-group-list" in js
    assert "renderMonitoringRoomCard" in js
    assert "renderMonitoringDeviceRow" in js
    assert "monitoring-device-list-head" in js
    assert "monitoring-device-row" in js
    assert ".monitoring-room-group" in css
    assert ".monitoring-device-row" in css
    assert "grid-template-columns: minmax(180px, 2fr) minmax(110px, 1fr) minmax(150px, 1.5fr) minmax(92px, auto) minmax(180px, auto);" in css
    assert 'id="monitoring-management-list"' in html


def test_monitoring_management_room_children_contract_mentions_expected_devices():
    js = read("frontend/js/admin_app.js")

    assert "room.devices || []" in js
    assert "room_name: room.name" in js
    assert "<span>Device</span>" in js
    assert "<span>Type</span>" in js
    assert "<span>Threshold</span>" in js
    assert "Chiller" in read("frontend/admin/admin_panel.html") or "chiller" in js
    assert "freezer" in js
    assert "room_temp" in js


def test_monitoring_device_row_prevents_overlap_and_keeps_actions_aligned():
    css = read("frontend/css/admin_enterprise.css")

    assert ".monitoring-device-threshold" in css
    assert "white-space: nowrap;" in css
    assert ".monitoring-device-actions" in css
    assert "justify-content: flex-end;" in css
    assert "flex-wrap: nowrap;" in css
    assert ".monitoring-device-status" in css
    assert "min-width: 760px;" in css


def test_add_monitoring_unit_uses_internal_panel_not_modal_behind_management():
    html = read("frontend/admin/admin_panel.html")
    js = read("frontend/js/admin_app.js")

    assert 'id="monitoring-unit-form-panel"' in html
    assert 'id="monitoring-unit-form"' in html
    open_fn = js.split("openMonitoringUnitModal(device = null, room = null)", 1)[1].split("defaultTargetForType", 1)[0]
    assert "openCrudModal" not in open_fn
    assert "panel.hidden = false" in open_fn
    assert "monitoring-unit-fields" in open_fn


def test_add_device_to_room_prefills_room_name():
    js = read("frontend/js/admin_app.js")

    assert "Tambah Device" in js
    assert "openMonitoringUnitModal(null," in js
    assert "roomContext.name" in js
    assert 'id="monitoring-unit-room-name"' in js


def test_edit_monitoring_device_and_soft_deactivate_still_use_admin_endpoints():
    js = read("frontend/js/admin_app.js")

    assert "editMonitoringUnit" in js
    assert "API.patch(`/admin/facility/devices/${this.crudId}`, payload)" in js
    assert "deactivateMonitoringDevice" in js
    assert "API.patch(`/admin/facility/devices/${id}`, { is_active: false })" in js
    assert "API.delete(`/admin/facility/devices/${id}`" not in js


def test_existing_monitoring_grid_contract_is_unchanged():
    html = read("frontend/admin/admin_panel.html")
    js = read("frontend/js/admin_app.js")

    assert 'id="monitoring-grid"' in html
    assert "async loadMonitoring()" in js
    assert "const grid = document.getElementById('monitoring-grid');" in js
    assert "grid.appendChild(card);" in js


def test_monitoring_room_groups_are_full_width_not_two_column_cards():
    css = read("frontend/css/admin_enterprise.css")

    assert ".monitoring-room-group-list" in css
    assert "grid-template-columns: 1fr;" in css
    assert ".monitoring-room-group {" in css
    assert "width: 100%;" in css
