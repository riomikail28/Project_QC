from unittest.mock import patch

from tests.conftest import FakeSupabase


def _daily_db():
    return FakeSupabase({
        "facility_logs": [{
            "id": "temp-1",
            "staff_id": "staff-1",
            "room_id": "room-1",
            "device_id": "device-1",
            "temperature_c": 4.2,
            "is_normal": True,
            "photo_url": "https://example.com/temp.jpg",
            "notes": "Pagi",
            "recorded_at": "2026-05-16T01:00:00Z",
            "facility_rooms": {"name": "Chiller Room"},
            "facility_devices": {"name": "Chiller 1", "type": "chiller"},
        }],
        "qc_reports": [{
            "id": "report-1",
            "staff_id": "staff-1",
            "batch_code": "QC-20260516-010203",
            "barcode": "SKU-1",
            "product_name": "Produk A",
            "status": "pass",
            "approval_status": "pending",
            "notes": "OK",
            "photo_url": "https://example.com/qc.jpg",
            "created_at": "2026-05-16T02:00:00Z",
        }],
        "qc_findings": [{
            "id": "finding-1",
            "staff_id": "staff-2",
            "reason": "Kemasan rusak",
            "photo_url": "https://example.com/finding.jpg",
            "created_at": "2026-05-16T03:00:00Z",
        }],
        "qc_evidence": [{
            "id": "evidence-1",
            "related_type": "qc_finding",
            "related_id": "finding-1",
            "public_url": "https://example.com/finding.jpg",
            "storage_path": "staff/staff-2/findings/finding.jpg",
            "uploaded_by": "staff-2",
            "created_at": "2026-05-16T03:00:00Z",
        }],
    })


def test_admin_daily_report_combines_staff_inputs(client, admin_headers):
    with patch("backend.services.admin_service.get_client", return_value=_daily_db()):
        response = client.get("/api/admin/reports/daily?date=2026-05-16", headers=admin_headers)

    assert response.status_code == 200
    data = response.get_json()["data"]
    assert data["summary"] == {"temperature": 1, "inspection": 1, "findings": 1, "evidence": 1}
    assert {row["type"] for row in data["rows"]} == {"temperature", "inspection", "finding"}


def test_admin_daily_export_csv(client, admin_headers):
    with patch("backend.services.admin_service.get_client", return_value=_daily_db()):
        response = client.get("/api/admin/export/daily-report?date=2026-05-16&type=csv", headers=admin_headers)

    assert response.status_code == 200
    assert response.mimetype == "text/csv"
    assert "qc_daily_report_2026-05-16.csv" in response.headers["Content-Disposition"]
    body = response.get_data(as_text=True)
    assert "Date,Report Type,Staff,Room,Device,SKU/Barcode,Product,Temperature,QC Status,Notes,Photo URL,Created At" in body
    assert "temperature" in body
    assert "inspection" in body
    assert "finding" in body
