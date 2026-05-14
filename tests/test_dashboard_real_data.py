from unittest.mock import patch

from tests.conftest import FakeSupabase


def test_dashboard_summary_uses_real_tables(client, staff_headers):
    fake_db = FakeSupabase({
        "production_batches": [{"id": "batch-1", "production_date": "2026-05-14", "created_at": "2026-05-14T01:00:00Z"}],
        "qc_reports": [
            {"id": "qc-1", "status": "pass", "approval_status": "approved", "created_at": "2026-05-14T02:00:00Z"},
            {"id": "qc-2", "status": "warning", "approval_status": "pending", "created_at": "2026-05-14T03:00:00Z"},
        ],
        "temperature_logs": [
            {"id": "temp-1", "device_type": "freezer", "temperature_c": -18, "is_abnormal": False, "recorded_at": "2026-05-14T04:00:00Z"},
            {"id": "temp-2", "device_type": "freezer", "temperature_c": -16, "is_abnormal": True, "recorded_at": "2026-05-14T05:00:00Z"},
        ],
        "facility_alerts": [],
        "approvals": [],
    })

    with patch("backend.services.dashboard_service.get_client", return_value=fake_db):
        response = client.get("/api/dashboard/summary", headers=staff_headers)

    assert response.status_code == 200
    body = response.get_json()
    assert body["success"] is True
    assert body["data"]["total_batches_today"] == 1
    assert body["data"]["total_alerts"] == 1
    assert body["data"]["qc_success_rate"] == 50.0
    assert body["data"]["pending_approval"] == 1
    assert body["data"]["avg_freezer_temperature"] == -17.0


def test_dashboard_empty_state_is_not_dummy(client, staff_headers):
    fake_db = FakeSupabase({})

    with patch("backend.services.dashboard_service.get_client", return_value=fake_db):
        response = client.get("/api/dashboard/qc-status", headers=staff_headers)

    assert response.status_code == 200
    body = response.get_json()
    assert body["success"] is True
    assert body["data"]["total"] == 0
    assert all(item["count"] == 0 for item in body["data"]["items"])
