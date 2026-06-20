from unittest.mock import patch

from tests.conftest import FakeSupabase


def test_task3_admin_audit_logs_can_filter_by_date_action_and_user(client, admin_headers):
    db = FakeSupabase(
        {
            "audit_logs": [
                {
                    "id": "audit-1",
                    "action": "submit_temperature",
                    "actor_id": "staff-1",
                    "entity_type": "facility_log",
                    "created_at": "2026-05-16T01:00:00Z",
                },
                {
                    "id": "audit-2",
                    "action": "approve_qc",
                    "actor_id": "admin-1",
                    "entity_type": "qc_report",
                    "created_at": "2026-05-17T01:00:00Z",
                },
            ]
        }
    )

    with patch("backend.services.admin_service.get_client", return_value=db):
        response = client.get(
            "/api/admin/audit-logs?date=2026-05-16&action=submit_temperature&user=staff-1",
            headers=admin_headers,
        )

    rows = response.get_json()
    assert response.status_code == 200
    assert len(rows) == 1
    assert rows[0]["action"] == "submit_temperature"
