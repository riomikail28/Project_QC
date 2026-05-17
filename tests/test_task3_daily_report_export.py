from unittest.mock import patch

from tests.conftest import FakeSupabase


def test_task3_daily_report_summary_includes_approval_status_counts(client, admin_headers):
    db = FakeSupabase({
        "facility_logs": [],
        "qc_reports": [
            {"id": "r1", "staff_id": "staff-1", "status": "pass", "approval_status": "approved", "created_at": "2026-05-16T01:00:00Z"},
            {"id": "r2", "staff_id": "staff-1", "status": "hold", "approval_status": "rejected", "created_at": "2026-05-16T02:00:00Z"},
        ],
        "qc_findings": [],
        "qc_evidence": [],
        "approvals": [
            {"id": "a1", "status": "approved", "created_at": "2026-05-16T01:00:00Z"},
            {"id": "a2", "status": "rejected", "created_at": "2026-05-16T02:00:00Z"},
        ],
    })

    with patch("backend.services.admin_service.get_client", return_value=db):
        response = client.get("/api/admin/reports/daily?date=2026-05-16", headers=admin_headers)

    summary = response.get_json()["data"]["summary"]
    assert response.status_code == 200
    assert summary["inspection_reports"] == 2
    assert summary["approvals_approved"] == 1
    assert summary["approvals_rejected"] == 1


def test_task3_daily_export_uses_production_csv_columns(client, admin_headers):
    db = FakeSupabase({
        "facility_logs": [{
            "id": "temp-1",
            "staff_id": "staff-1",
            "temperature_c": 4,
            "is_normal": True,
            "recorded_at": "2026-05-16T01:00:00Z",
        }],
        "qc_reports": [],
        "qc_findings": [],
        "qc_evidence": [],
        "approvals": [],
    })

    with patch("backend.services.admin_service.get_client", return_value=db), patch("backend.services.audit_service.write_audit"):
        response = client.get("/api/admin/export/daily-report?date=2026-05-16&type=csv", headers=admin_headers)

    body = response.get_data(as_text=True)
    assert response.status_code == 200
    assert "Date,Time,Report Type,Staff,Room,Device,SKU/Barcode,Product,Temperature,QC Status,Approval Status,Notes,Photo URL" in body
