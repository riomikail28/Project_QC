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
