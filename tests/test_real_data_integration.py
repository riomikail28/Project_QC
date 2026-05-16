from unittest.mock import patch

from tests.conftest import FakeSupabase


def test_admin_reports_empty_data_uses_empty_state_payload(client, admin_headers):
    with patch("backend.services.admin_service.get_client", return_value=FakeSupabase({})):
        response = client.get("/api/v1/admin/reports/evidence", headers=admin_headers)

    body = response.get_json()
    assert response.status_code == 200
    assert body == {"success": True, "data": [], "message": "OK"}


def test_dashboard_summary_empty_data_does_not_fake_numbers(client, staff_headers):
    with patch("backend.services.dashboard_service.get_client", return_value=FakeSupabase({})):
        response = client.get("/api/dashboard/summary", headers=staff_headers)

    data = response.get_json()["data"]
    assert data["total_batches_today"] == 0
    assert data["pending_approval"] == 0
    assert data["qc_success_rate"] is None
    assert data["has_data"] is False
