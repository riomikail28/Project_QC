from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PHOTO_PAGES = [
    ROOT / "frontend" / "staff" / "dashboard.html",
    ROOT / "frontend" / "staff" / "monitoring.html",
    ROOT / "frontend" / "staff" / "inspection.html",
    ROOT / "frontend" / "staff" / "ccp_stage.html",
]


def test_frontend_config_exposes_only_public_supabase_values(client, monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://public-ref.supabase.co")
    monkeypatch.setenv("SUPABASE_ANON_KEY", "public-anon-key")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "must-not-leak")
    monkeypatch.setenv("SUPABASE_STORAGE_BUCKET", "qc-evidence")
    monkeypatch.setenv("GOOGLE_APPS_SCRIPT_WEBHOOK_URL", "https://script.google.com/macros/s/private/exec")

    response = client.get("/js/config.js")
    body = response.get_data(as_text=True)

    assert response.status_code == 200
    assert response.mimetype == "application/javascript"
    assert "https://public-ref.supabase.co" in body
    assert "public-anon-key" in body
    assert "qc-evidence" in body
    assert "must-not-leak" not in body
    assert "script.google.com" not in body
    assert '"googleAppsScriptConnected":true' in body
    assert "service_role" not in body.lower()


def test_photo_pages_load_config_before_camera_module():
    for page in PHOTO_PAGES:
        html = page.read_text(encoding="utf-8")
        config_index = html.index("../js/config.js")
        camera_index = html.index("../js/camera-module.js")
        assert config_index < camera_index, page.name


def test_dashboard_qc_finding_uploads_through_backend_submit():
    html = (ROOT / "frontend" / "staff" / "dashboard.html").read_text(encoding="utf-8")

    assert "API.upload('/qc/findings', formData)" in html
    assert "formData.append('photo'," in html
    assert "formData.append('photo_url'" not in html
    assert "formData.append('storage_path'" not in html


def test_csp_allows_blob_image_previews(client):
    response = client.get("/")
    csp = response.headers["Content-Security-Policy"]

    assert "img-src 'self' data: blob: https:" in csp


def test_staff_profile_hides_staff_action_menu_items():
    html = (ROOT / "frontend" / "staff" / "profile.html").read_text(encoding="utf-8")

    assert "My QC Activity" not in html
    assert "My Upload Evidence" not in html
    assert "My Temperature Logs" not in html
    assert "Open Admin Panel" not in html
    assert "hidden" in html


def test_staff_pages_mark_admin_links_as_role_based():
    for page_name in ["dashboard.html", "monitoring.html", "inspection.html", "profile.html"]:
        html = (ROOT / "frontend" / "staff" / page_name).read_text(encoding="utf-8")
        assert 'href="/admin/admin_panel.html"' in html
        admin_index = html.index('href="/admin/admin_panel.html"')
        tag_start = html.rfind("<", 0, admin_index)
        tag_end = html.find(">", admin_index)
        admin_tag = html[tag_start:tag_end]
        assert "data-admin-only" in admin_tag, page_name
        assert "hidden" in admin_tag, page_name


def test_auth_supports_super_admin_and_role_visibility():
    auth_js = (ROOT / "frontend" / "js" / "auth.js").read_text(encoding="utf-8")

    assert "role()" in auth_js
    assert "'staff'" in auth_js
    assert "super_admin" in auth_js
    assert "applyRoleVisibility" in auth_js
    assert "refreshSessionRole" in auth_js
    assert "API.get('/profile/me')" in auth_js
    assert "element.hidden = !canAccessAdmin" in auth_js
    assert "element.style.display = canAccessAdmin ? '' : 'none'" in auth_js
    assert "homeForRole" in auth_js
    assert "requireRole" in auth_js


def test_staff_pages_refresh_role_from_session():
    for page_name in ["dashboard.html", "monitoring.html", "inspection.html"]:
        html = (ROOT / "frontend" / "staff" / page_name).read_text(encoding="utf-8")
        assert "Auth.refreshSessionRole()" in html


def test_profile_applies_profile_role_not_stale_local_storage():
    profile_js = (ROOT / "frontend" / "js" / "profile.js").read_text(encoding="utf-8")

    assert "Auth.persistUser(user)" in profile_js
    assert "Auth.applyRoleVisibility(role)" in profile_js
    assert "Auth.canAccessAdmin(role)" in profile_js


def test_admin_app_confirms_delete_for_default_facility_devices():
    admin_js = (ROOT / "frontend" / "js" / "admin_app.js").read_text(encoding="utf-8")

    assert "isDefaultDevice" in admin_js
    assert "Unit default akan dihapus" in admin_js
    assert "renderDeviceDeleteButton(device)" in admin_js
    assert "startsWith('default-')" in admin_js


def test_csp_allows_cdn_source_map_connections(client):
    response = client.get("/")
    csp = response.headers["Content-Security-Policy"]

    assert "https://cdn.jsdelivr.net" in csp
    assert "https://unpkg.com" in csp
