from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read(path):
    return (ROOT / path).read_text(encoding="utf-8")


def test_monitoring_management_uses_grouped_room_tree_layout():
    html = read("frontend/admin/admin_panel.html")
    js = read("frontend/js/admin_app.js")
    css = read("frontend/css/admin_enterprise.css")

    assert "monitoring-room-card-grid" in js
    assert "renderMonitoringRoomCard" in js
    assert "renderMonitoringDeviceChild" in js
    assert "monitoring-device-tree" in js
    assert "monitoring-device-child" in js
    assert ".monitoring-room-card" in css
    assert ".monitoring-device-child" in css
    assert ".monitoring-device-tree" in css
    assert 'id="monitoring-management-list"' in html


def test_monitoring_management_room_children_contract_mentions_expected_devices():
    js = read("frontend/js/admin_app.js")

    assert "room.devices || []" in js
    assert "room_name: room.name" in js
    assert "Type:" in js
    assert "Threshold:" in js
    assert "Chiller" in read("frontend/admin/admin_panel.html") or "chiller" in js
    assert "freezer" in js
    assert "room_temp" in js


def test_monitoring_device_item_has_indentation_child_classes():
    css = read("frontend/css/admin_enterprise.css")

    assert ".monitoring-device-tree" in css
    assert "padding-left: 18px;" in css
    assert "border-left: 2px solid" in css
    assert ".monitoring-device-branch" in css
    assert ".monitoring-device-item" in css


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

    assert "Tambah Device ke Room Ini" in js
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
