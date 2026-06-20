from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_task4_frontend_config_does_not_expose_backend_secrets(client, monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://public-ref.supabase.co")
    monkeypatch.setenv("SUPABASE_ANON_KEY", "public-anon-key")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "service-role-secret-must-not-leak")
    monkeypatch.setenv("JWT_SECRET_KEY", "jwt-secret-must-not-leak")

    response = client.get("/js/config.js")
    body = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "public-anon-key" in body
    assert "service-role-secret-must-not-leak" not in body
    assert "jwt-secret-must-not-leak" not in body


def test_task4_admin_release_routes_are_role_protected(client, staff_headers):
    protected_routes = [
        "/api/admin/reports/temperature",
        "/api/admin/reports/inspection",
        "/api/admin/approvals",
        "/api/admin/audit-logs",
        "/api/admin/export/daily-report?date=2026-05-16&type=csv",
    ]

    for route in protected_routes:
        response = client.get(route, headers=staff_headers)
        assert response.status_code in {401, 403}, route


def test_task4_admin_mobile_tables_have_card_list_contract():
    css = (ROOT / "frontend" / "css" / "admin_enterprise.css").read_text(encoding="utf-8")
    admin_js = (ROOT / "frontend" / "js" / "admin_app.js").read_text(encoding="utf-8")

    assert "@media (max-width: 860px)" in css
    assert ".enterprise-table td::before" in css
    assert "content: attr(data-label)" in css
    for label in ["Tanggal", "Foto Evidence", "Action", "Waktu", "Barcode"]:
        assert f'data-label="{label}"' in admin_js


def test_task4_file_upload_limits_are_configured():
    api_js = (ROOT / "frontend" / "js" / "api.js").read_text(encoding="utf-8")
    camera_js = (ROOT / "frontend" / "js" / "camera-module.js").read_text(encoding="utf-8")

    assert "image/jpeg" in api_js
    assert "image/png" in api_js
    assert "image/webp" in api_js
    assert "10 * 1024 * 1024" in api_js
    assert "maxUploadBytes" in camera_js
