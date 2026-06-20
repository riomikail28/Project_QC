from unittest.mock import patch

from tests.conftest import FakeSupabase


def test_admin_reports_read_staff_temperature_and_qc_data(client, admin_headers):
    db = FakeSupabase(
        {
            "facility_logs": [
                {
                    "id": "log-1",
                    "staff_id": "staff-1",
                    "zone": "PPIC",
                    "device_type": "chiller",
                    "temperature_c": 4.5,
                    "is_normal": True,
                    "photo_url": "https://img/temp.jpg",
                    "storage_path": "staff/staff-1/temperature/temp.jpg",
                    "recorded_at": "2026-05-16T00:00:00Z",
                }
            ],
            "qc_reports": [
                {
                    "id": "qc-1",
                    "batch_code": "BATCH-1",
                    "staff_id": "staff-1",
                    "status": "pass",
                    "product_photo_url": "https://img/qc.jpg",
                    "product_storage_path": "staff/staff-1/inspection/qc.jpg",
                    "created_at": "2026-05-16T00:10:00Z",
                }
            ],
        }
    )

    with patch("backend.services.admin_service.get_client", return_value=db):
        temp = client.get("/api/v1/admin/reports/temperature", headers=admin_headers).get_json()
        inspection = client.get("/api/v1/admin/reports/inspection", headers=admin_headers).get_json()

    assert temp["success"] is True
    assert temp["data"][0]["staff_id"] == "staff-1"
    assert inspection["success"] is True
    assert inspection["data"][0]["batch_code"] == "BATCH-1"
