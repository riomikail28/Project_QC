from unittest.mock import patch

from tests.conftest import FakeSupabase


def test_profile_me_uses_session_when_database_empty(client, staff_headers):
    with patch("backend.services.profile_service.get_client", return_value=FakeSupabase({})):
        response = client.get("/api/profile/me", headers=staff_headers)

    body = response.get_json()
    assert response.status_code == 200
    assert body["success"] is True
    assert body["data"]["id"] == "staff-1"
    assert body["data"]["username"] == "staff"
    assert body["data"]["role"] == "staff"


def test_profile_activity_summary_counts_real_rows(client, staff_headers):
    fake_db = FakeSupabase(
        {
            "qc_reports": [
                {"id": "qc-1", "staff_id": "staff-1", "status": "pass", "product_photo_url": "https://img/1.jpg"},
                {"id": "qc-2", "staff_id": "staff-1", "status": "failed"},
                {"id": "qc-3", "staff_id": "other", "status": "pass"},
            ],
            "temperature_logs": [{"id": "t1", "staff_id": "staff-1", "photo_url": "https://img/t.jpg"}],
            "barcode_labels": [{"id": "b1", "staff_id": "staff-1", "barcode_photo_url": "https://img/b.jpg"}],
            "audit_logs": [{"id": "a1", "actor_id": "staff-1", "action": "create"}],
        }
    )

    with patch("backend.services.profile_service.get_client", return_value=fake_db):
        response = client.get("/api/profile/activity-summary", headers=staff_headers)

    data = response.get_json()["data"]
    assert data["qc_submitted"] == 2
    assert data["temperature_logs"] == 1
    assert data["barcode_labels"] == 1
    assert data["upload_evidence"] == 3
    assert data["accuracy"] == 50.0
    assert data["has_activity"] is True


def test_profile_admin_role_from_session(client, admin_headers):
    with patch("backend.services.profile_service.get_client", return_value=FakeSupabase({})):
        response = client.get("/api/profile/me", headers=admin_headers)

    assert response.get_json()["data"]["role"] == "admin"
