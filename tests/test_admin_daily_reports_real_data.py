from unittest.mock import patch

from tests.conftest import FakeSupabase


def _daily_report_db():
    return FakeSupabase(
        {
            "staff_accounts": [
                {"id": "staff-1", "full_name": "Rio Mikail", "email": "rio@example.com"},
                {"id": "staff-2", "full_name": "Dina QC", "email": "dina@example.com"},
            ],
            "users": [],
            "facility_logs": [
                {
                    "id": "temp-1",
                    "staff_id": "staff-1",
                    "room_id": "PPIC",
                    "device_id": "Chiller",
                    "temperature_c": 4.1,
                    "status": "PASS",
                    "photo_url": "https://example.com/temp.jpg",
                    "notes": "Pagi",
                    "recorded_at": "2026-05-31T00:14:00Z",
                    "monitoring_date": "2026-05-31",
                },
                {
                    "id": "temp-old",
                    "staff_id": "staff-1",
                    "room_id": "PPIC",
                    "device_id": "Freezer",
                    "temperature_c": -18,
                    "status": "PASS",
                    "recorded_at": "2026-05-30T00:14:00Z",
                    "monitoring_date": "2026-05-30",
                },
            ],
            "temperature_logs": [
                {
                    "id": "fallback-temp-1",
                    "staff_id": "staff-1",
                    "room_id": "Fallback",
                    "device_id": "Fallback Device",
                    "temperature": 5.1,
                    "status": "PASS",
                    "recorded_at": "2026-05-31T00:20:00Z",
                    "monitoring_date": "2026-05-31",
                }
            ],
            "qc_reports": [
                {
                    "id": "qc-1",
                    "staff_id": "staff-1",
                    "batch_code": "SKU-20260531-001",
                    "product_name": "Sauce",
                    "status": "HOLD",
                    "notes": "Need re-check",
                    "photo_url": "https://example.com/qc.jpg",
                    "created_at": "2026-05-31T01:00:00Z",
                },
                {
                    "id": "qc-2",
                    "staff_id": "staff-2",
                    "batch_code": "SKU-20260531-002",
                    "product_name": "Rice",
                    "status": "PASS",
                    "created_at": "2026-05-31T02:00:00Z",
                },
            ],
            "qc_findings": [
                {
                    "id": "finding-1",
                    "staff_id": "staff-2",
                    "batch_code": "SKU-20260531-002",
                    "status": "WARNING",
                    "reason": "Label kurang jelas",
                    "evidence_url": "https://example.com/finding.jpg",
                    "created_at": "2026-05-31T03:00:00Z",
                }
            ],
            "approvals": [],
        }
    )


def test_daily_reports_reads_facility_logs(client, admin_headers):
    with patch("backend.services.admin_service.get_client", return_value=_daily_report_db()):
        response = client.get("/api/admin/daily-reports?date=2026-05-31", headers=admin_headers)

    assert response.status_code == 200
    data = response.get_json()["data"]
    assert data["summary"]["temperature_logs"] == 1
    assert any(row["type"] == "Temperature Log" for row in data["rows"])


def test_daily_reports_reads_qc_reports_and_findings(client, admin_headers):
    with patch("backend.services.admin_service.get_client", return_value=_daily_report_db()):
        response = client.get("/api/admin/daily-reports?date=2026-05-31", headers=admin_headers)

    data = response.get_json()["data"]
    assert data["summary"]["inspections"] == 2
    assert data["summary"]["findings"] == 1
    assert any(row["type"] == "Inspection" for row in data["rows"])
    assert any(row["type"] == "Finding" for row in data["rows"])


def test_daily_reports_summary_count_is_correct(client, admin_headers):
    with patch("backend.services.admin_service.get_client", return_value=_daily_report_db()):
        response = client.get("/api/admin/daily-reports?date=2026-05-31", headers=admin_headers)

    summary = response.get_json()["data"]["summary"]
    assert summary == {
        "temperature_logs": 1,
        "inspections": 2,
        "inspection_reports": 2,
        "findings": 1,
        "evidence": 3,
        "approvals_pending": 0,
        "approvals_approved": 0,
        "approvals_rejected": 0,
        "temperature": 1,
        "inspection": 2,
    }


def test_daily_reports_date_filter_works(client, admin_headers):
    with patch("backend.services.admin_service.get_client", return_value=_daily_report_db()):
        response = client.get("/api/admin/daily-reports?date=2026-05-30", headers=admin_headers)

    data = response.get_json()["data"]
    assert data["summary"]["temperature_logs"] == 1
    assert data["summary"]["inspections"] == 0
    assert all(str(row["created_at"]).startswith("2026-05-30") for row in data["rows"])


def test_daily_reports_staff_filter_works_for_name_and_email(client, admin_headers):
    with patch("backend.services.admin_service.get_client", return_value=_daily_report_db()):
        by_name = client.get("/api/admin/daily-reports?date=2026-05-31&staff=Rio", headers=admin_headers)
        by_email = client.get("/api/admin/daily-reports?date=2026-05-31&staff=dina@example.com", headers=admin_headers)

    assert by_name.get_json()["data"]["summary"]["temperature_logs"] == 1
    assert by_name.get_json()["data"]["summary"]["inspections"] == 1
    assert by_name.get_json()["data"]["summary"]["findings"] == 0
    assert by_email.get_json()["data"]["summary"]["temperature_logs"] == 0
    assert by_email.get_json()["data"]["summary"]["inspections"] == 1
    assert by_email.get_json()["data"]["summary"]["findings"] == 1


def test_daily_reports_status_filter_works(client, admin_headers):
    with patch("backend.services.admin_service.get_client", return_value=_daily_report_db()):
        hold = client.get("/api/admin/daily-reports?date=2026-05-31&status=HOLD", headers=admin_headers)
        warning = client.get("/api/admin/daily-reports?date=2026-05-31&status=WARNING", headers=admin_headers)

    assert hold.get_json()["data"]["summary"]["inspections"] == 1
    assert hold.get_json()["data"]["summary"]["temperature_logs"] == 0
    assert warning.get_json()["data"]["summary"]["findings"] == 1
    assert warning.get_json()["data"]["summary"]["inspections"] == 0


def test_frontend_daily_reports_not_hardcoded_zero():
    script = open("frontend/js/admin_app.js", encoding="utf-8").read()
    assert "/daily-reports?" in script
    assert "summary.temperature_logs" in script
    assert "summary.inspections" in script
    assert "summary.temperature || 0" not in script


def test_frontend_daily_export_csv_button_exists():
    html = open("frontend/admin/admin_panel.html", encoding="utf-8").read()
    assert "adminApp.exportDailyCsv()" in html
    assert "Export CSV" in html
