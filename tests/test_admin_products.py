from unittest.mock import patch
from pathlib import Path

from tests.conftest import FakeSupabase

ROOT = Path(__file__).resolve().parents[1]


def test_admin_can_list_products(client, admin_headers):
    fake_db = FakeSupabase({
        "products": [
            {
                "id": "product-1",
                "product_code": "SKU-TEST-001",
                "product_name": "Test Product",
                "is_active": True,
            }
        ]
    })

    with patch("backend.services.admin_service.get_client", return_value=fake_db):
        response = client.get("/api/v1/admin/products", headers=admin_headers)

    assert response.status_code == 200
    body = response.get_json()
    assert body[0]["product_code"] == "SKU-TEST-001"


def test_staff_cannot_create_admin_product(client, staff_headers):
    response = client.post(
        "/api/v1/admin/products",
        json={"product_code": "SKU-TEST-002", "product_name": "Staff Product"},
        headers=staff_headers,
    )

    assert response.status_code == 403


def test_admin_can_create_product(client, admin_headers):
    fake_db = FakeSupabase({"products": []})

    with patch("backend.services.admin_service.get_client", return_value=fake_db):
        response = client.post(
            "/api/v1/admin/products",
            json={
                "product_code": "SKU-TEST-003",
                "product_name": "Admin Product",
                "ph_min": 4,
                "ph_max": 6,
                "is_active": True,
            },
            headers=admin_headers,
        )

    assert response.status_code == 201
    body = response.get_json()
    assert body["product_code"] == "SKU-TEST-003"
    assert body["ph_min"] == 4.0


def test_admin_qc_reports_include_staff_dashboard_findings(client, admin_headers):
    fake_db = FakeSupabase({
        "qc_reports": [
            {
                "id": "report-1",
                "batch_code": "BATCH-001",
                "status": "pass",
                "created_at": "2026-05-16T08:00:00Z",
            }
        ],
        "qc_findings": [
            {
                "id": "finding-1",
                "staff_id": "staff-1",
                "reason": "Foreign object found",
                "photo_url": "https://example.supabase.co/storage/v1/object/public/qc-evidence/staff/finding.jpg",
                "storage_path": "staff/2026-05-16/finding.jpg",
                "created_at": "2026-05-16T09:00:00Z",
            }
        ],
    })

    with patch("backend.services.admin_service.get_client", return_value=fake_db):
        response = client.get("/api/v1/admin/qc-reports", headers=admin_headers)

    assert response.status_code == 200
    rows = response.get_json()["data"]
    assert rows[0]["report_type"] == "qc_finding"
    assert rows[0]["status"] == "finding"
    assert rows[0]["photo_url"].endswith("/finding.jpg")
    assert rows[0]["storage_path"] == "staff/2026-05-16/finding.jpg"


def test_admin_qc_reports_loads_findings_for_reports_hash():
    html = (ROOT / "frontend" / "admin" / "admin_panel.html").read_text(encoding="utf-8")
    js = (ROOT / "frontend" / "js" / "admin_app.js").read_text(encoding="utf-8")
    css = (ROOT / "frontend" / "css" / "admin_enterprise.css").read_text(encoding="utf-8")

    assert 'data-section="reports"' in html
    assert "case 'reports': this.loadOperationalReports(); break;" in js
    assert "renderEvidenceCell" in js
    assert "storage_path" in js
    assert "admin-evidence-path" in css


def test_admin_api_urls_do_not_double_api_prefix():
    api_js = (ROOT / "frontend" / "js" / "api.js").read_text(encoding="utf-8")
    admin_js = (ROOT / "frontend" / "js" / "admin_app.js").read_text(encoding="utf-8")

    assert "apiBase: '/v1/admin'" in admin_js
    assert "apiBase: '/api/v1/admin'" not in admin_js
    assert "_url(endpoint)" in api_js
    assert "startsWith('/api/')" in api_js
    assert "API_BASE}${endpoint}" not in api_js
    for endpoint in (
        "/qc-reports",
        "/traceability",
        "/approvals",
        "/audit-trail",
        "/monitoring/realtime",
        "/analytics/overview",
    ):
        assert f"${{this.apiBase}}{endpoint}" in admin_js


def test_admin_approvals_fallback_includes_staff_submissions(client, admin_headers):
    fake_db = FakeSupabase({
        "approvals": [],
        "qc_reports": [
            {
                "id": "report-1",
                "batch_code": "BATCH-001",
                "approval_status": "pending",
                "status": "warning",
                "staff_id": "staff-1",
                "product_photo_url": "https://img/report.jpg",
                "created_at": "2026-05-16T08:00:00Z",
            }
        ],
        "qc_findings": [
            {
                "id": "finding-1",
                "staff_id": "staff-2",
                "reason": "Foreign object",
                "photo_url": "https://img/finding.jpg",
                "storage_path": "staff/finding.jpg",
                "created_at": "2026-05-16T09:00:00Z",
            }
        ],
        "facility_logs": [
            {
                "id": "temp-1",
                "room_id": "room-1",
                "device_id": "device-1",
                "staff_id": "staff-3",
                "temperature_c": 9,
                "is_normal": False,
                "photo_url": "https://img/temp.jpg",
                "recorded_at": "2026-05-16T10:00:00Z",
            }
        ],
    })

    with patch("backend.services.admin_service.get_client", return_value=fake_db):
        response = client.get("/api/v1/admin/approvals", headers=admin_headers)

    rows = response.get_json()
    assert response.status_code == 200
    assert rows[0]["source"] == "temperature_log"
    assert {row["source"] for row in rows} == {"qc_report", "qc_finding", "temperature_log"}
    assert any(row.get("product_photo_url") == "https://img/finding.jpg" for row in rows)


def test_admin_audit_trail_fallback_from_staff_activity(client, admin_headers):
    fake_db = FakeSupabase({
        "audit_logs": [],
        "qc_findings": [
            {"id": "finding-1", "staff_id": "staff-1", "created_at": "2026-05-16T09:00:00Z"}
        ],
        "facility_logs": [
            {"id": "temp-1", "staff_id": "staff-2", "recorded_at": "2026-05-16T10:00:00Z"}
        ],
        "qc_reports": [
            {"id": "report-1", "staff_id": "staff-3", "created_at": "2026-05-16T08:00:00Z"}
        ],
        "production_batch_logs": [],
    })

    with patch("backend.services.admin_service.get_client", return_value=fake_db):
        response = client.get("/api/v1/admin/audit-trail", headers=admin_headers)

    rows = response.get_json()
    assert response.status_code == 200
    assert rows[0]["entity_type"] == "facility_log"
    assert {row["action"] for row in rows} == {"submit", "input_temperature"}
    assert rows[0]["staff_accounts"]["username"] == "staff-2"


def test_admin_traceability_fallback_from_staff_submissions(client, admin_headers):
    fake_db = FakeSupabase({
        "barcode_labels": [],
        "production_batches": [
            {
                "id": "batch-1",
                "batch_code": "BATCH-001",
                "product_id": "product-1",
                "products": {"product_name": "Chicken Soup"},
                "created_at": "2026-05-16T07:00:00Z",
            }
        ],
        "qc_reports": [
            {
                "id": "report-1",
                "batch_id": "batch-1",
                "staff_id": "staff-1",
                "temperature_photo_url": "https://img/report.jpg",
                "created_at": "2026-05-16T08:00:00Z",
            }
        ],
        "facility_logs": [
            {
                "id": "temp-1",
                "room_id": "PPIC",
                "device_id": "Chiller",
                "staff_id": "staff-2",
                "photo_url": "https://img/temp.jpg",
                "recorded_at": "2026-05-16T10:00:00Z",
            }
        ],
        "qc_findings": [
            {
                "id": "finding-1",
                "staff_id": "staff-3",
                "reason": "Dirty area",
                "photo_url": "https://img/finding.jpg",
                "created_at": "2026-05-16T09:00:00Z",
            }
        ],
        "production_batch_logs": [],
    })

    with patch("backend.services.admin_service.get_client", return_value=fake_db):
        response = client.get("/api/v1/admin/traceability", headers=admin_headers)

    rows = response.get_json()
    assert response.status_code == 200
    assert rows[0]["barcode_value"] == "PPIC / Chiller"
    assert any(row.get("batch_code") == "BATCH-001" and row.get("product_name") == "Chicken Soup" for row in rows)
    assert any(row.get("photo_url") == "https://img/finding.jpg" for row in rows)
