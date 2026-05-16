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

    response = client.get("/js/config.js")
    body = response.get_data(as_text=True)

    assert response.status_code == 200
    assert response.mimetype == "application/javascript"
    assert "https://public-ref.supabase.co" in body
    assert "public-anon-key" in body
    assert "qc-evidence" in body
    assert "must-not-leak" not in body
    assert "service_role" not in body.lower()


def test_photo_pages_load_config_before_camera_module():
    for page in PHOTO_PAGES:
        html = page.read_text(encoding="utf-8")
        config_index = html.index("../js/config.js")
        camera_index = html.index("../js/camera-module.js")
        assert config_index < camera_index, page.name


def test_dashboard_qc_finding_uploads_to_supabase_before_backend_submit():
    html = (ROOT / "frontend" / "staff" / "dashboard.html").read_text(encoding="utf-8")

    assert "API.uploadPhotoToSupabase" in html
    assert "formData.append('photo'," not in html
    assert "formData.append('photo_url'" in html
    assert "formData.append('storage_path'" in html


def test_csp_allows_blob_image_previews(client):
    response = client.get("/")
    csp = response.headers["Content-Security-Policy"]

    assert "img-src 'self' data: blob: https:" in csp


def test_staff_profile_hides_staff_action_menu_items():
    html = (ROOT / "frontend" / "staff" / "profile.html").read_text(encoding="utf-8")

    assert "My QC Activity" not in html
    assert "My Upload Evidence" not in html
    assert "My Temperature Logs" not in html
    assert "Open Admin Panel" in html
    assert "hidden" in html
