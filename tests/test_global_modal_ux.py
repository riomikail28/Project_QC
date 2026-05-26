from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read(path):
    return (ROOT / path).read_text(encoding="utf-8")


def test_admin_modals_have_accessible_close_buttons_and_dialog_roles():
    html = read("frontend/admin/admin_panel.html")

    assert 'id="crud-modal" role="dialog" aria-modal="true"' in html
    assert 'id="image-modal" role="dialog" aria-modal="true"' in html
    assert 'aria-labelledby="crud-title"' in html
    assert 'aria-labelledby="image-modal-title"' in html
    assert html.count('aria-label="Close modal"') >= 2


def test_admin_modal_css_prevents_viewport_overflow_and_keeps_regions_visible():
    css = read("frontend/css/admin_enterprise.css")

    assert "width: min(900px, 95vw);" in css
    assert "max-height: 90vh;" in css
    assert "display: flex;" in css
    assert "flex-direction: column;" in css
    assert ".modal-content > form" in css
    assert "max-height: inherit;" in css
    assert ".modal-header" in css and "position: sticky;" in css and "top: 0;" in css
    assert ".modal-body" in css and "flex: 1;" in css and "overflow-y: auto;" in css
    assert ".modal-footer" in css and "bottom: 0;" in css and "flex-shrink: 0;" in css
    assert "width: 8px;" in css
    assert "width: 96vw;" in css
    assert "body.modal-open" in css


def test_admin_modal_form_layout_and_textarea_constraints():
    css = read("frontend/css/admin_enterprise.css")

    assert "grid-template-columns: repeat(2, minmax(0, 1fr));" in css
    assert "grid-template-columns: 1fr;" in css
    assert "min-height: 90px;" in css
    assert "max-height: 220px;" in css
    assert "resize: vertical;" in css
    assert "box-shadow: 0 0 0 4px rgba(37, 99, 235, .14);" in css


def test_admin_modal_escape_overlay_and_x_close_supported():
    js = read("frontend/js/admin_app.js")

    assert "setupModalBehavior" in js
    assert "event.key !== 'Escape'" in js
    assert "event.target !== modal" in js
    assert "closeCrudModal()" in js
    assert "closeImageModal()" in js
    assert "classList.add('active')" in js
    assert "setModalOpen(true)" in js


def test_staff_modals_and_drawers_have_sticky_scrollable_regions():
    alerts_css = read("frontend/styles/alerts.css")
    monitoring_css = read("frontend/styles/monitoring.css")
    dashboard_html = read("frontend/staff/dashboard.html")
    monitoring_html = read("frontend/staff/monitoring.html")
    monitoring_js = read("frontend/js/monitoring.js")

    assert 'role="dialog" aria-modal="true"' in dashboard_html
    assert 'role="dialog" aria-modal="true"' in monitoring_html
    assert dashboard_html.count('aria-label="Close modal"') >= 2
    assert 'aria-label="Close modal"' in monitoring_html
    assert ".alert-drawer-footer" in alerts_css and "position: sticky;" in alerts_css
    assert ".alert-drawer-body" in alerts_css and "flex: 1;" in alerts_css and "overflow-y: auto;" in alerts_css
    assert ".sheet-footer" in monitoring_css and "position: sticky;" in monitoring_css
    assert ".sheet-body" in monitoring_css and "flex: 1;" in monitoring_css and "overflow-y: auto;" in monitoring_css
    assert ".sheet-body::-webkit-scrollbar" in monitoring_css
    assert ".alert-drawer-body::-webkit-scrollbar" in alerts_css
    assert 'document.body.classList.add("modal-open")' in monitoring_js
    assert 'event.key === "Escape"' in monitoring_js


def test_existing_admin_crud_save_logic_still_references_same_endpoints():
    js = read("frontend/js/admin_app.js")

    assert "submitCrudForm" in js
    assert "API.post('/staff'" in js
    assert "API.patch(`/staff/${this.crudId}`" in js
    assert "API.post('/v1/admin/products'" in js
    assert "API.patch(`/v1/admin/products/${this.crudId}`" in js
    assert "API.post('/admin/learning/modules'" in js
    assert "API.patch(`/admin/learning/modules/${this.crudId}`" in js
