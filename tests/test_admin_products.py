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
    assert "case 'reports': this.loadQCReports(); break;" in js
    assert "renderEvidenceCell" in js
    assert "storage_path" in js
    assert "admin-evidence-path" in css
